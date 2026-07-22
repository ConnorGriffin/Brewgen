"""The anonymous-compute envelope that wraps Brewgen's public POST endpoints.

Every public compute request passes through one shared gate, in a fixed order,
*before* any solver work runs:

1. media type must be ``application/json``            -> 415
2. body must be at most 64 KiB                         -> 413
3. body must parse as JSON                             -> 400
4. body must satisfy the versioned brief contract      -> 422
5. the visitor must be within their request budget     -> 429
6. a solver slot must be free (two, no queue)          -> 503 busy

Only then does the wrapped operation run under the solver's own shared budget,
and its ``deadline_exceeded``/``infeasible`` outcomes are surfaced as 503/422.

All failures use ``application/problem+json`` with the locked status codes and
carry no echoed input. Every request emits one aggregate log line carrying only
``{timestamp, request_id, operation, outcome, status, duration}`` -- never the
brief, the client address, or the address hash.

Deployment assumption (see decision-map #10 and the public-launch map #12/#16):
the API runs as a **single worker process** behind **exactly one trusted proxy
hop**. The client address is resolved with ``ProxyFix(x_for=1)`` in
``views.py``; the in-memory rate limit and the two-slot ceiling are therefore
per-container and correct only under that shape. The deploy must forward exactly
one hop.
"""

import hashlib
import json
import logging
import math
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone
from functools import wraps

from flask import Response, request

# -- locked envelope constants ---------------------------------------------

MAX_BODY_BYTES = 65_536            # 64 KiB body cap
RATE_LIMIT_PER_MINUTE = 6         # sustained compute requests per visitor
RATE_LIMIT_BURST = 2              # tokens a fresh visitor may spend at once
RATE_IDLE_EXPIRY_SECONDS = 600    # drop a visitor's bucket after 10 idle minutes
CONCURRENCY_LIMIT = 2             # active solver operations per container, no queue
LOG_RETENTION_DAYS = 7            # documented retention; enforced by the log sink

# Stable, input-free titles. These are never shown to the visitor (the frontend
# renders its own copy from the machine ``outcome`` tag); they only have to stay
# free of solver/server internals.
_TITLES = {
    "wrong_media_type": "Unsupported request format",
    "oversized": "Request too large",
    "malformed_json": "Malformed request",
    "invalid": "Brief could not be read",
    "infeasible": "No grain bill fits this brief",
    "rate_limited": "Too many requests",
    "busy": "Service busy",
    "deadline": "Timed out",
    "internal": "Internal error",
}

# One dedicated logger; the deploy points it at a 7-day sink. Nothing else is
# ever written here, so the aggregate record cannot pick up request internals.
logger = logging.getLogger("brewgen.compute")


# -- problem+json / success responses --------------------------------------

def problem(status, outcome):
    """Build an ``application/problem+json`` failure `(response, outcome)`.

    The body carries only RFC 7807 members plus a stable machine ``outcome``
    tag the frontend maps to a notice; it never echoes the request."""
    body = {
        "type": "about:blank",
        "title": _TITLES.get(outcome, "Request failed"),
        "status": status,
        "outcome": outcome,
    }
    resp = Response(json.dumps(body), status=status,
                    mimetype="application/problem+json")
    return resp, outcome


def ok_json(body, outcome, status=200):
    """Build a successful ``application/json`` `(response, outcome)`."""
    resp = Response(json.dumps(body), status=status, mimetype="application/json")
    return resp, outcome


# -- brief contract ---------------------------------------------------------

# The one supported contract version. A body may omit it (the frontend does),
# but if present it must match -- a future breaking shape ships a new version.
BRIEF_VERSION = 1

_FERMENTABLE_KEYS = {"slug", "min_percent", "max_percent"}
_CATEGORY_KEYS = {"name", "min_percent", "max_percent", "unique_fermentable_count"}
_SENSORY_KEYS = {"name", "min", "max"}
_EQUIPMENT_KEYS = {"target_volume_gallons", "mash_efficiency"}
_BEER_KEYS = {"original_sg", "min_color_srm", "max_color_srm"}
_TOP_KEYS = {
    "version", "fermentable_list", "category_model", "sensory_model",
    "max_unique_fermentables", "equipment_profile", "beer_profile",
}


def _finite_number(value):
    """True for a real, finite JSON number (rejecting NaN/Infinity and bools)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(value)


class BriefContract:
    """The versioned grain-bill brief validator.

    Holds the catalog (known slugs, categories, sensory keywords) so it can
    reject unknown or duplicate values and cap every list at catalog
    cardinality. :meth:`validate` returns ``None`` when the brief is acceptable
    or a machine outcome tag (always ``"invalid"``) when it is not -- coarse on
    purpose, so a rejection never echoes which value was wrong.
    """

    def __init__(self, slugs, categories, sensory_keywords):
        self.slugs = set(slugs)
        self.categories = set(categories)
        self.sensory_keywords = set(sensory_keywords)

    @classmethod
    def from_grain_list(cls, grain_list):
        return cls(
            grain_list.get_grain_slugs(),
            grain_list.get_all_categories(),
            grain_list.get_sensory_keywords(),
        )

    def validate(self, data, *, require_descriptor=False):
        """Return ``None`` if ``data`` is a valid brief, else ``"invalid"``."""
        if not isinstance(data, dict):
            return "invalid"

        allowed = set(_TOP_KEYS)
        if require_descriptor:
            allowed.add("descriptor")
        if set(data) - allowed:
            return "invalid"

        if "version" in data and data["version"] != BRIEF_VERSION:
            return "invalid"

        if require_descriptor:
            descriptor = data.get("descriptor")
            if not isinstance(descriptor, str) or descriptor not in self.sensory_keywords:
                return "invalid"

        if self._bad_fermentables(data.get("fermentable_list")):
            return "invalid"
        if self._bad_categories(data.get("category_model")):
            return "invalid"
        if self._bad_sensory(data.get("sensory_model")):
            return "invalid"
        if self._bad_max_unique(data.get("max_unique_fermentables")):
            return "invalid"
        if self._bad_equipment(data.get("equipment_profile")):
            return "invalid"
        if self._bad_beer(data.get("beer_profile")):
            return "invalid"
        return None

    def _bad_range(self, item, keys, lo=None, hi=None, low_key="min_percent",
                   high_key="max_percent"):
        """True if a min/max pair on ``item`` is missing, non-finite, out of the
        optional [lo, hi] band, or inverted."""
        for key in (low_key, high_key):
            value = item.get(key)
            if not _finite_number(value):
                return True
            if lo is not None and value < lo:
                return True
            if hi is not None and value > hi:
                return True
        return item[low_key] > item[high_key]

    def _bad_fermentables(self, fermentables):
        # At least one grain, capped at catalog cardinality, unique known slugs.
        if not isinstance(fermentables, list) or not fermentables:
            return True
        if len(fermentables) > len(self.slugs):
            return True
        seen = set()
        for item in fermentables:
            if not isinstance(item, dict) or set(item) - _FERMENTABLE_KEYS:
                return True
            slug = item.get("slug")
            if slug not in self.slugs or slug in seen:
                return True
            seen.add(slug)
            if self._bad_range(item, _FERMENTABLE_KEYS, lo=0, hi=100):
                return True
        return False

    def _bad_categories(self, categories):
        if categories is None:
            return False  # optional
        if not isinstance(categories, list) or len(categories) > len(self.categories):
            return True
        seen = set()
        for item in categories:
            if not isinstance(item, dict) or set(item) - _CATEGORY_KEYS:
                return True
            name = item.get("name")
            if name not in self.categories or name in seen:
                return True
            seen.add(name)
            if self._bad_range(item, _CATEGORY_KEYS, lo=0, hi=100):
                return True
            cap = item.get("unique_fermentable_count")
            if cap is not None and not _finite_number(cap):
                return True
        return False

    def _bad_sensory(self, sensory):
        if sensory is None:
            return False  # optional
        if not isinstance(sensory, list) or len(sensory) > len(self.sensory_keywords):
            return True
        seen = set()
        for item in sensory:
            if not isinstance(item, dict) or set(item) - _SENSORY_KEYS:
                return True
            name = item.get("name")
            if name not in self.sensory_keywords or name in seen:
                return True
            seen.add(name)
            if self._bad_range(item, _SENSORY_KEYS, low_key="min", high_key="max"):
                return True
        return False

    def _bad_max_unique(self, value):
        if value is None:
            return False  # optional, the solver defaults it
        return not _finite_number(value) or value < 1

    def _bad_equipment(self, equipment):
        if equipment is None:
            return False  # optional, the endpoints default it
        if not isinstance(equipment, dict) or set(equipment) - _EQUIPMENT_KEYS:
            return True
        for key in _EQUIPMENT_KEYS:
            if key in equipment and (not _finite_number(equipment[key])
                                     or equipment[key] <= 0):
                return True
        return False

    def _bad_beer(self, beer_profile):
        if beer_profile is None:
            return False  # optional, the endpoints default it
        if not isinstance(beer_profile, dict) or set(beer_profile) - _BEER_KEYS:
            return True
        for key in _BEER_KEYS:
            if key in beer_profile and not _finite_number(beer_profile[key]):
                return True
        lo = beer_profile.get("min_color_srm")
        hi = beer_profile.get("max_color_srm")
        if lo is not None and hi is not None and lo > hi:
            return True
        return False


# -- rate limiter -----------------------------------------------------------

class RateLimiter:
    """A per-visitor token bucket keyed by a daily-rotated hash of the address.

    Sustained rate ``RATE_LIMIT_PER_MINUTE`` with capacity ``RATE_LIMIT_BURST``:
    a fresh visitor may spend two requests at once, then one refills every ten
    seconds. Buckets idle for ``RATE_IDLE_EXPIRY_SECONDS`` are dropped, and the
    salt rotates daily so a hash can never be correlated across days. The salt
    and address are held only in memory and are never logged or persisted.

    Both clocks are injectable: ``clock`` (monotonic) drives refill/expiry and
    ``day_clock`` (wall) drives salt rotation, so behavior is testable without
    real waiting.
    """

    def __init__(self, per_minute=RATE_LIMIT_PER_MINUTE, burst=RATE_LIMIT_BURST,
                 idle_expiry=RATE_IDLE_EXPIRY_SECONDS,
                 clock=time.monotonic, day_clock=time.time):
        self._refill_per_second = per_minute / 60.0
        self._capacity = burst
        self._idle_expiry = idle_expiry
        self._clock = clock
        self._day_clock = day_clock
        self._lock = threading.Lock()
        self._buckets = {}          # key_hash -> [tokens, last_seen]
        self._salt = secrets.token_hex(16)
        self._salt_day = int(day_clock() // 86_400)

    def allow(self, address):
        """Charge one request to ``address``; return True if within budget."""
        with self._lock:
            now = self._clock()
            self._rotate_salt_if_needed()
            self._evict_idle(now)
            key = self._hash(address)
            if key in self._buckets:
                tokens, last = self._buckets[key]
                tokens = min(self._capacity,
                             tokens + (now - last) * self._refill_per_second)
            else:
                tokens = self._capacity
            if tokens >= 1:
                self._buckets[key] = (tokens - 1, now)
                return True
            self._buckets[key] = (tokens, now)
            return False

    def _hash(self, address):
        digest = hashlib.sha256()
        digest.update(self._salt.encode("utf-8"))
        digest.update(b"|")
        digest.update(str(address).encode("utf-8"))
        return digest.hexdigest()

    def _rotate_salt_if_needed(self):
        day = int(self._day_clock() // 86_400)
        if day != self._salt_day:
            self._salt = secrets.token_hex(16)
            self._salt_day = day
            self._buckets.clear()  # yesterday's hashes are meaningless now

    def _evict_idle(self, now):
        cutoff = now - self._idle_expiry
        stale = [key for key, (_t, last) in self._buckets.items() if last < cutoff]
        for key in stale:
            del self._buckets[key]


# -- process-wide, monkeypatchable state ------------------------------------

RATE_LIMITER = RateLimiter()
SLOTS = threading.BoundedSemaphore(CONCURRENCY_LIMIT)


def reset_state():
    """Reset the limiter and the concurrency ceiling to a clean slate.

    Only for tests, which need each case to start from an empty bucket store and
    two free slots regardless of what earlier cases did."""
    global RATE_LIMITER, SLOTS
    RATE_LIMITER = RateLimiter()
    SLOTS = threading.BoundedSemaphore(CONCURRENCY_LIMIT)


def client_address():
    """The request's client address as one trusted proxy hop resolves it.

    ``ProxyFix(x_for=1)`` in ``views.py`` rewrites ``remote_addr`` to the single
    forwarded hop, so raw peer/relay collapsing and blind X-Forwarded-For
    trust are both avoided."""
    return request.remote_addr or "0.0.0.0"


# -- structured aggregate logging -------------------------------------------

def _emit_log(request_id, operation, outcome, status, duration):
    """Emit the one aggregate record for a request. Only these six fields ever
    appear -- never the brief, the address, the hash, headers, or a query
    string."""
    logger.info(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "operation": operation,
        "outcome": outcome,
        "status": status,
        "duration": duration,
    }))


# -- the shared decorator ---------------------------------------------------

def compute_endpoint(operation, contract, require_descriptor=False):
    """Wrap a public compute view in the full envelope.

    The wrapped function receives the already-parsed, already-validated brief
    dict and returns a ``(response, outcome)`` pair (use :func:`ok_json` /
    :func:`problem`). Everything before it -- media type, size, JSON, contract,
    rate limit, concurrency -- and the single aggregate log line are handled
    here, once, so ordering and the failure shape are defined in one place.
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            start = time.monotonic()
            request_id = uuid.uuid4().hex
            response, outcome = _run(view, operation, contract,
                                     require_descriptor, args, kwargs)
            duration = round(time.monotonic() - start, 6)
            _emit_log(request_id, operation, outcome, response.status_code, duration)
            return response
        return wrapped
    return decorator


def _run(view, operation, contract, require_descriptor, args, kwargs):
    """Execute the ordered envelope and return `(response, outcome)`."""
    # 1. media type
    if request.mimetype != "application/json":
        return problem(415, "wrong_media_type")

    # 2. size cap -- reject before reading a large body into memory
    content_length = request.content_length
    if content_length is not None and content_length > MAX_BODY_BYTES:
        return problem(413, "oversized")
    raw = request.stream.read(MAX_BODY_BYTES + 1)
    if len(raw) > MAX_BODY_BYTES:
        return problem(413, "oversized")

    # 3. JSON parse
    if not raw.strip():
        return problem(400, "malformed_json")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return problem(400, "malformed_json")

    # 4. versioned brief contract
    if contract.validate(data, require_descriptor=require_descriptor):
        return problem(422, "invalid")

    # 5. per-visitor rate limit (one trusted hop)
    if not RATE_LIMITER.allow(client_address()):
        return problem(429, "rate_limited")

    # 6. two-slot, no-queue concurrency ceiling
    if not SLOTS.acquire(blocking=False):
        return problem(503, "busy")
    try:
        return view(data, *args, **kwargs)
    except Exception:  # never leak an internal failure's shape
        return problem(500, "internal")
    finally:
        SLOTS.release()
