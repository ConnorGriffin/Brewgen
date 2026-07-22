"""The anonymous-compute envelope around the public grain-bill routes (#29).

This layer owns everything that keeps anonymous optimization bounded without
collecting user data:

* a 64 KiB raw-body cap enforced *before* JSON parsing;
* an ``application/json`` media-type gate;
* an in-memory token bucket (six requests/visitor/minute, burst two) keyed by a
  daily-rotated keyed hash of the trusted client address -- the address, hash,
  and rotation key are never logged or persisted;
* a two-slot concurrency ceiling with no queue -- overflow is rejected as busy;
* ``application/problem+json`` failures with stable codes, a random request id,
  and no echoed input; and
* a scrubbed structured log carrying only timestamp, request id, operation,
  outcome, HTTP status, and duration.

The limiter, concurrency guard, and address hasher are module singletons so a
test can install deterministic, fake-clock variants.
"""

import functools
import hashlib
import json
import logging
import math
import os
import secrets
import threading
import time

from flask import Response, request
from werkzeug.exceptions import RequestEntityTooLarge

# -- locked limits (issue #29) ----------------------------------------------

MAX_BODY_BYTES = 64 * 1024          # cap the raw body before JSON parsing
RATE_CAPACITY = 2                   # burst two
RATE_REFILL_PER_SECOND = 6 / 60.0   # six per minute
BUCKET_IDLE_EXPIRY_SECONDS = 10 * 60
MAX_ACTIVE_SOLVES = 2               # two active solver requests, no queue
LOG_RETENTION_DAYS = 7              # request events retained at most seven days

public_log = logging.getLogger("brewgen.public")


class BusyError(Exception):
    """Raised when both solver slots are occupied; there is no waiting queue."""


# -- rate limiting -----------------------------------------------------------

class _TokenBucket:
    """A refilling token bucket. Capacity is the burst allowance; tokens refill
    continuously at ``refill`` per second up to capacity."""

    __slots__ = ("capacity", "refill", "tokens", "updated")

    def __init__(self, capacity, refill, now):
        self.capacity = capacity
        self.refill = refill
        self.tokens = float(capacity)
        self.updated = now

    def take(self, now):
        """Consume one token. Returns ``(allowed, retry_after_seconds)``."""
        elapsed = now - self.updated
        if elapsed > 0:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill)
            self.updated = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True, 0.0
        return False, (1 - self.tokens) / self.refill


class RateLimiter:
    """Per-visitor token buckets with idle expiry. State is memory-only."""

    def __init__(self, capacity=RATE_CAPACITY, refill=RATE_REFILL_PER_SECOND,
                 idle_expiry=BUCKET_IDLE_EXPIRY_SECONDS, clock=time.monotonic):
        self._capacity = capacity
        self._refill = refill
        self._idle_expiry = idle_expiry
        self._clock = clock
        self._buckets = {}
        self._lock = threading.Lock()

    def check(self, key):
        now = self._clock()
        with self._lock:
            self._expire(now)
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _TokenBucket(self._capacity, self._refill, now)
                self._buckets[key] = bucket
            return bucket.take(now)

    def _expire(self, now):
        stale = [k for k, b in self._buckets.items()
                 if now - b.updated > self._idle_expiry]
        for key in stale:
            del self._buckets[key]


class AddressHasher:
    """Daily-rotated keyed hash of a client address.

    The rotation key is random per process and rotates each UTC day, so buckets
    cannot be correlated across days and the raw address is never recoverable
    from the key. Neither the address, the key, nor the digest is logged."""

    def __init__(self, clock=time.time):
        self._clock = clock
        self._day = None
        self._key = None
        self._lock = threading.Lock()

    def hash(self, address):
        with self._lock:
            day = int(self._clock() // 86400)
            if day != self._day:
                self._day = day
                self._key = secrets.token_bytes(32)
            return hashlib.blake2b(
                address.encode("utf-8"), key=self._key, digest_size=16).hexdigest()


class ConcurrencyGuard:
    """A non-queuing ceiling on concurrent solves."""

    def __init__(self, slots=MAX_ACTIVE_SOLVES):
        self._sem = threading.BoundedSemaphore(slots)

    def acquire(self):
        return self._sem.acquire(blocking=False)

    def release(self):
        self._sem.release()


# Module singletons; replaceable in tests for deterministic behaviour.
RATE_LIMITER = RateLimiter()
ADDRESS_HASHER = AddressHasher()
CONCURRENCY = ConcurrencyGuard()

# When set (to the trusted relay/proxy), forwarded client addresses are honored;
# otherwise only the direct peer address is trusted.
TRUSTED_PROXY = os.environ.get("BREWGEN_TRUSTED_PROXY")


def _client_key():
    """A stable, non-reversible per-visitor key. Trusts a forwarded address only
    when a relay/proxy is configured; never returns or logs the raw address."""
    address = None
    if TRUSTED_PROXY:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            address = forwarded.split(",")[0].strip()
    if not address:
        address = request.remote_addr or "unknown"
    return ADDRESS_HASHER.hash(address)


# -- concurrency helper ------------------------------------------------------

class solver_slot:
    """Context manager that holds one solver slot, or raises ``BusyError`` when
    none is free. The slot is always released, so a slot is recovered even when
    the guarded solve raises or times out."""

    def __enter__(self):
        if not CONCURRENCY.acquire():
            raise BusyError()
        return self

    def __exit__(self, *exc):
        CONCURRENCY.release()
        return False


# -- problem+json ------------------------------------------------------------

def problem(code, status, request_id, errors=None, retry_after=None):
    """Build an ``application/problem+json`` response. Carries a stable machine
    code and the request id; never echoes request input."""
    body = {"code": code, "status": status, "request_id": request_id}
    if errors:
        body["errors"] = errors
    resp = Response(json.dumps(body), status=status,
                    mimetype="application/problem+json")
    if retry_after is not None:
        resp.headers["Retry-After"] = str(retry_after)
    return resp


# -- the decorator -----------------------------------------------------------

def compute_endpoint(operation):
    """Wrap a compute handler with the full #29 envelope.

    The wrapped ``fn(payload, request_id)`` receives the decoded JSON body and a
    random request id and returns ``(flask_response, outcome_code)``. It may
    raise ``brief.BriefError`` for a rejected brief or ``BusyError`` when no
    solver slot is free; every other exception becomes a generic 500.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            request_id = secrets.token_hex(8)
            started = time.monotonic()

            def finish(response, outcome):
                duration_ms = (time.monotonic() - started) * 1000
                # The only fields ever logged for this route: no bodies,
                # constraint values, addresses, headers, cookies, UAs, or query
                # strings ever reach the log.
                public_log.info(
                    "op=%s request_id=%s outcome=%s status=%s duration_ms=%.1f",
                    operation, request_id, outcome, response.status_code, duration_ms)
                response.headers["X-Request-Id"] = request_id
                return response

            if request.mimetype != "application/json":
                return finish(problem("unsupported_media_type", 415, request_id),
                              "unsupported_media_type")

            # 64 KiB cap, enforced before any JSON parsing.
            try:
                raw = request.get_data(cache=False)
            except RequestEntityTooLarge:
                return finish(problem("request_too_large", 413, request_id),
                              "request_too_large")
            if len(raw) > MAX_BODY_BYTES:
                return finish(problem("request_too_large", 413, request_id),
                              "request_too_large")

            allowed, retry_after = RATE_LIMITER.check(_client_key())
            if not allowed:
                return finish(
                    problem("rate_limited", 429, request_id,
                            retry_after=max(1, math.ceil(retry_after))),
                    "rate_limited")

            try:
                payload = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return finish(problem("malformed_json", 400, request_id),
                              "malformed_json")

            from .brief import BriefError
            try:
                response, outcome = fn(payload, request_id)
            except BriefError as exc:
                return finish(
                    problem(exc.code, exc.http_status, request_id, errors=exc.errors),
                    exc.code)
            except BusyError:
                return finish(problem("busy", 503, request_id, retry_after=1), "busy")
            except Exception:
                # Retain type and stack for triage, but never the request itself.
                public_log.exception(
                    "op=%s request_id=%s outcome=internal_error", operation, request_id)
                return finish(problem("internal_error", 500, request_id),
                              "internal_error")
            return finish(response, outcome)

        return wrapper
    return decorator
