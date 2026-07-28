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
``views.py``; the in-memory rate limit and the one-slot ceiling are therefore
per-container and correct only under that shape. The deploy must forward exactly
one hop.
"""

import collections
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
from .brief import BriefError

# -- locked envelope constants ---------------------------------------------

MAX_BODY_BYTES = 65_536            # 64 KiB body cap
RATE_LIMIT_PER_MINUTE = 6         # sustained compute requests per visitor
RATE_LIMIT_BURST = 2              # tokens a fresh visitor may spend at once
RATE_IDLE_EXPIRY_SECONDS = 600    # drop a visitor's bucket after 10 idle minutes
CONCURRENCY_LIMIT = 1             # active solver operation per container, no queue
BUSY_RETRY_SECONDS = 1            # short retry for a busy shed (<=2 s end-to-end budget)
LOG_RETENTION_DAYS = 7            # documented retention; enforced by the log sink
RESULT_CACHE_TTL_SECONDS = 60     # replay window for a just-computed identical brief
RESULT_CACHE_MAX_ENTRIES = 256    # bound the cache so distinct briefs can't grow it

# The outcomes that represent a genuine solver answer and are safe to replay. A
# transient/limit state (deadline, busy, rate_limited, internal) is never cached
# so an immediate retry is always free to succeed.
_CACHEABLE_OUTCOMES = frozenset({"feasible", "infeasible", "complete", "partial"})

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

def problem(status, outcome, errors=None, retry_after=None):
    """Build an ``application/problem+json`` failure `(response, outcome)`.

    The body carries RFC 7807 members, a stable machine ``outcome`` tag, and
    optional path-only validation errors; it never echoes the request. When
    ``retry_after`` is given (seconds until the visitor may retry), it is
    surfaced both as an integer ``Retry-After`` header (ceiled, per RFC 7231)
    and as a ``retry_after`` body field the frontend renders as a countdown."""
    body = {
        "type": "about:blank",
        "title": _TITLES.get(outcome, "Request failed"),
        "status": status,
        "outcome": outcome,
    }
    headers = {}
    if errors:
        body["errors"] = errors
    if retry_after is not None:
        seconds = max(0, math.ceil(retry_after))
        body["retry_after"] = seconds
        headers["Retry-After"] = str(seconds)
    resp = Response(json.dumps(body), status=status,
                    mimetype="application/problem+json", headers=headers)
    return resp, outcome


def ok_json(body, outcome, status=200):
    """Build a successful ``application/json`` `(response, outcome)`."""
    resp = Response(json.dumps(body), status=status, mimetype="application/json")
    return resp, outcome


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
        """Charge one request to ``address``.

        Returns ``(allowed, retry_after)``: ``allowed`` is True when a token was
        spent, and ``retry_after`` is the seconds until one token next refills,
        computed from the *same* clock reading so it is exact under a frozen
        clock (0.0 when the request is allowed)."""
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
                return True, 0.0
            self._buckets[key] = (tokens, now)
            return False, (1 - tokens) / self._refill_per_second

    def refund(self, address):
        """Credit one token back to ``address`` (capped at capacity).

        Undoes the charge :meth:`allow` made when a request is shed *after* the
        rate check but before any solver work runs (a busy concurrency shed), so
        the gate keeps its documented rate->concurrency order yet a busy
        rejection costs the visitor no net token. At a frozen clock this exactly
        restores the pre-request bucket."""
        with self._lock:
            now = self._clock()
            key = self._hash(address)
            if key in self._buckets:
                tokens, last = self._buckets[key]
                tokens = min(self._capacity,
                             tokens + (now - last) * self._refill_per_second + 1)
            else:
                tokens = self._capacity
            self._buckets[key] = (tokens, now)

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


# -- canonical brief key ----------------------------------------------------

def _normalize_brief(data, require_descriptor):
    """Canonicalize a validated brief into a shape that is stable across
    equivalent-but-differently-written requests.

    Sorts each choice list by its identity key so ordering is irrelevant. For
    a focused ``sensory_range``, the queried descriptor's own sensory entry is
    dropped because that endpoint computes the descriptor's full editable span
    independently of its current bound.
    """
    fermentables = data["fermentables"]
    norm = {
        "style": data["style"],
        "equipment": data["equipment"],
        "fermentables": {
            "allowed_slugs": sorted(fermentables["allowed_slugs"]),
            "bounds": sorted(
                fermentables.get("bounds", []),
                key=lambda item: item["slug"],
            ),
            "maximum_count": fermentables["maximum_count"],
        },
        "color_srm": data["color_srm"],
    }

    sensory = data["sensory"]
    if require_descriptor:
        sensory = [
            item for item in sensory
            if item["name"] != data["descriptor"]
        ]
    norm["sensory"] = sorted(sensory, key=lambda item: item["name"])

    if require_descriptor:
        norm["descriptor"] = data["descriptor"]

    return norm


def canonical_key(operation, data, require_descriptor):
    """A deterministic string key for ``(operation, canonical brief)``."""
    payload = json.dumps(_normalize_brief(data, require_descriptor),
                         sort_keys=True, separators=(",", ":"))
    return operation + "\x00" + payload


# -- single-flight coalescing + short-lived result cache --------------------

class _Flight:
    """One in-flight leader others may attach to. ``result`` is the frozen
    response tuple to replay, or ``None`` once done to mean 're-run' (the leader
    produced a non-answer that must not be shared)."""

    def __init__(self, lock):
        self.cond = threading.Condition(lock)
        self.done = False
        self.result = None


class ComputeCoalescer:
    """Collapse identical concurrent compute calls onto one execution and replay
    a just-completed identical answer for a short TTL.

    Identical calls sharing a canonical key elect one leader that runs the
    solver; the rest attach as followers and receive the leader's frozen result
    without taking a slot or re-running. A genuine answer is cached (bounded LRU,
    TTL) so an immediate identical brief replays with no solver work. The clock
    is injectable so tests can advance the TTL without waiting.
    """

    def __init__(self, ttl=RESULT_CACHE_TTL_SECONDS,
                 max_entries=RESULT_CACHE_MAX_ENTRIES, clock=time.monotonic):
        self._ttl = ttl
        self._max_entries = max_entries
        self._clock = clock
        self._lock = threading.Lock()
        self._cache = collections.OrderedDict()  # key -> (expires_at, frozen)
        self._inflight = {}                       # key -> _Flight

    def execute(self, key, runner):
        """Return the frozen ``(body, status, mimetype, headers, outcome)`` for ``key``,
        replaying a cached or coalesced result when possible, else running
        ``runner`` (which acquires the slot and calls the view)."""
        while True:
            with self._lock:
                cached = self._get_cached(key)
                if cached is not None:
                    return cached
                flight = self._inflight.get(key)
                if flight is None:
                    flight = _Flight(self._lock)
                    self._inflight[key] = flight
                    leader = True
                else:
                    leader = False

            if leader:
                return self._lead(key, flight, runner)

            with self._lock:
                while not flight.done:
                    flight.cond.wait()
                if flight.result is not None:
                    return flight.result
            # Leader produced a non-answer: fall through and re-run.

    def _lead(self, key, flight, runner):
        cacheable = False
        frozen = None
        try:
            frozen, cacheable = runner()
        finally:
            with self._lock:
                if cacheable and frozen is not None:
                    self._put_cached(key, frozen)
                flight.result = frozen if cacheable else None
                flight.done = True
                if self._inflight.get(key) is flight:
                    del self._inflight[key]
                flight.cond.notify_all()
        return frozen

    def _get_cached(self, key):
        entry = self._cache.get(key)
        if entry is None:
            return None
        expires_at, frozen = entry
        if self._clock() >= expires_at:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return frozen

    def _put_cached(self, key, frozen):
        self._cache[key] = (self._clock() + self._ttl, frozen)
        self._cache.move_to_end(key)
        while len(self._cache) > self._max_entries:
            self._cache.popitem(last=False)


# -- process-wide, monkeypatchable state ------------------------------------

RATE_LIMITER = RateLimiter()
SLOTS = threading.BoundedSemaphore(CONCURRENCY_LIMIT)
COALESCER = ComputeCoalescer()


def reset_state():
    """Reset the limiter, concurrency ceiling, and coalescer to a clean slate.

    Only for tests, which need each case to start from an empty bucket store,
    one free slot, and an empty cache/in-flight map regardless of what earlier
    cases did."""
    global RATE_LIMITER, SLOTS, COALESCER
    RATE_LIMITER = RateLimiter()
    SLOTS = threading.BoundedSemaphore(CONCURRENCY_LIMIT)
    COALESCER = ComputeCoalescer()


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

    The wrapped function receives the validated, server-derived brief and
    returns a ``(response, outcome)`` pair (use :func:`ok_json` /
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
    try:
        brief = contract.parse(data, require_descriptor=require_descriptor)
    except BriefError as error:
        return problem(422, "invalid", errors=error.errors)

    # 5. per-visitor rate limit (one trusted hop) -- charged before any
    #    coalescing or cache lookup, so a flood still spends its budget.
    address = client_address()
    allowed, retry_after = RATE_LIMITER.allow(address)
    if not allowed:
        return problem(429, "rate_limited", retry_after=retry_after)

    # 6. coalesce identical in-flight work and replay a recent identical answer,
    #    taking a slot only for the leader's single execution.
    key = canonical_key(operation, data, require_descriptor)

    def runner():
        # 6a. one-slot, no-queue concurrency ceiling -- the leader alone takes a
        #     slot; followers ride its result without one. A busy shed never
        #     reaches solver work, so refund the token step 5 charged: the rate
        #     check keeps its documented position, but a busy rejection costs
        #     the visitor nothing and carries a short retry.
        if not SLOTS.acquire(blocking=False):
            RATE_LIMITER.refund(address)
            shed = problem(503, "busy", retry_after=BUSY_RETRY_SECONDS)
            return _freeze(*shed), False
        try:
            resp, outcome = view(brief, *args, **kwargs)
        except Exception:  # never leak an internal failure's shape
            resp, outcome = problem(500, "internal")
        finally:
            SLOTS.release()
        return _freeze(resp, outcome), outcome in _CACHEABLE_OUTCOMES

    return _thaw(COALESCER.execute(key, runner))


# Headers that must survive the freeze/replay round trip. Content type and
# length are rebuilt from the frozen body and mimetype, so only the retry hint
# has to be carried across.
_REPLAYED_HEADERS = ("Retry-After",)


def _freeze(response, outcome):
    """Reduce a `(response, outcome)` pair to a replayable, single-use-free
    tuple. A Flask ``Response`` body reads once, so we hold the bytes (plus the
    retry hint, which lives in a header) and rebuild a fresh ``Response`` per
    caller in :func:`_thaw`."""
    headers = tuple((name, response.headers[name])
                    for name in _REPLAYED_HEADERS if name in response.headers)
    return (response.get_data(), response.status_code, response.mimetype,
            headers, outcome)


def _thaw(frozen):
    """Rebuild a fresh `(response, outcome)` from a frozen tuple so every caller
    gets an independent, byte-identical response object."""
    body, status, mimetype, headers, outcome = frozen
    return (Response(body, status=status, mimetype=mimetype,
                     headers=list(headers)), outcome)
