"""The #29 anonymous-compute envelope, proven through the public interface.

Covers the request boundary (strict validation, the 64 KiB cap, media type,
malformed and empty bodies), the compute boundary (shared deadline across
validity/sensory-range/generation, two-slot no-queue concurrency and slot
recovery), the per-visitor token bucket (burst, refill, expiry, all on a fake
clock), the ``application/problem+json`` failure contract, and the scrubbed
logging boundary."""

import io
import json
import logging

import pytest

from conftest import make_brief
from brewgen.backend import envelope, views
from brewgen.backend.envelope import (
    AddressHasher, RateLimiter, ConcurrencyGuard, _TokenBucket)
from brewgen.backend.solver.fermentables import SolverConfig

RECIPES = "/api/v1/grains/recipes"
FEASIBILITY = "/api/v1/grains/feasibility"
SENSORY_RANGE = "/api/v1/grains/sensory-range"

STYLE = views.all_styles.get_style_by_slug("american-pale-ale")
STYLE_SLUGS = [g["slug"] for g in STYLE.get_grain_usage()]
SLUGS = views.all_grains.get_grain_slugs()
KEYWORDS = sorted(views.all_grains.get_sensory_keywords())
OUTSIDER = next(s for s in SLUGS if s not in set(STYLE_SLUGS))


@pytest.fixture(autouse=True)
def _relaxed_envelope(monkeypatch):
    """Default to guardrails that never trip, so a test opts in to a strict
    limiter or concurrency guard only when it is what is under test."""
    monkeypatch.setattr(envelope, "RATE_LIMITER",
                        envelope.RateLimiter(capacity=1000, refill=1000))
    monkeypatch.setattr(envelope, "CONCURRENCY", envelope.ConcurrencyGuard(slots=8))


@pytest.fixture
def client():
    return views.app.test_client()


def base():
    """A fresh, valid brief for a real style."""
    return make_brief(STYLE, min_srm=3.0, max_srm=30.0)


# -- shallow mutators (never touch the shared base) --------------------------

def _set(b, key, val):
    c = dict(b)
    c[key] = val
    return c


def _style_(b, **kw):
    s = dict(b["style"]); s.update(kw); return _set(b, "style", s)


def _equip(b, **kw):
    e = dict(b["equipment"]); e.update(kw); return _set(b, "equipment", e)


def _ferm(b, **kw):
    f = dict(b["fermentables"]); f.update(kw); return _set(b, "fermentables", f)


# -- strict validation: one offending field, named by path -------------------

INVALID_CASES = [
    ("unknown top-level field", lambda b: _set(b, "surprise", 1), "surprise"),
    ("unknown nested field", lambda b: _style_(b, surprise=1), "style.surprise"),
    ("version not one", lambda b: _set(b, "version", 2), "version"),
    ("version boolean", lambda b: _set(b, "version", True), "version"),
    ("unknown style slug", lambda b: _style_(b, slug="no-such-style"), "style.slug"),
    ("gravity below range", lambda b: _style_(b, original_gravity=0.9),
     "style.original_gravity"),
    ("gravity above range", lambda b: _style_(b, original_gravity=1.5),
     "style.original_gravity"),
    ("batch below range", lambda b: _equip(b, batch_volume_gallons=0.1),
     "equipment.batch_volume_gallons"),
    ("efficiency above range", lambda b: _equip(b, mash_efficiency_percent=101),
     "equipment.mash_efficiency_percent"),
    ("efficiency boolean", lambda b: _equip(b, mash_efficiency_percent=True),
     "equipment.mash_efficiency_percent"),
    ("empty allowed list", lambda b: _ferm(b, allowed_slugs=[]),
     "fermentables.allowed_slugs"),
    ("unknown allowed slug", lambda b: _ferm(b, allowed_slugs=["sentinel-not-real"]),
     "fermentables.allowed_slugs[0]"),
    ("duplicate allowed slug",
     lambda b: _ferm(b, allowed_slugs=[SLUGS[0], SLUGS[0]], maximum_count=1),
     "fermentables.allowed_slugs[1]"),
    ("allowed over catalog cap",
     lambda b: _ferm(b, allowed_slugs=[SLUGS[0]] * 72, maximum_count=1),
     "fermentables.allowed_slugs"),
    ("bound for absent fermentable",
     lambda b: _ferm(b, bounds=[{"slug": OUTSIDER, "minimum_percent": 0,
                                 "maximum_percent": 10}]),
     "fermentables.bounds[0].slug"),
    ("inverted bound",
     lambda b: _ferm(b, bounds=[{"slug": STYLE_SLUGS[0], "minimum_percent": 80,
                                 "maximum_percent": 20}]),
     "fermentables.bounds[0].minimum_percent"),
    ("bound over range",
     lambda b: _ferm(b, bounds=[{"slug": STYLE_SLUGS[0], "minimum_percent": 0,
                                 "maximum_percent": 150}]),
     "fermentables.bounds[0].maximum_percent"),
    ("maximum_count zero", lambda b: _ferm(b, maximum_count=0),
     "fermentables.maximum_count"),
    ("maximum_count over seven", lambda b: _ferm(b, maximum_count=8),
     "fermentables.maximum_count"),
    ("maximum_count as float", lambda b: _ferm(b, maximum_count=2.0),
     "fermentables.maximum_count"),
    ("maximum_count exceeds allowed",
     lambda b: _ferm(b, allowed_slugs=[STYLE_SLUGS[0], STYLE_SLUGS[1]],
                     bounds=[], maximum_count=3),
     "fermentables.maximum_count"),
    ("unknown sensory name",
     lambda b: _set(b, "sensory", [{"name": "sentinel-flavor", "minimum": 0,
                                    "maximum": 1}]),
     "sensory[0].name"),
    ("duplicate sensory name",
     lambda b: _set(b, "sensory", [{"name": KEYWORDS[0], "minimum": 0, "maximum": 1},
                                   {"name": KEYWORDS[0], "minimum": 0, "maximum": 1}]),
     "sensory[1].name"),
    ("sensory bound over range",
     lambda b: _set(b, "sensory", [{"name": KEYWORDS[0], "minimum": 0,
                                    "maximum": 6}]),
     "sensory[0].maximum"),
    ("inverted sensory bound",
     lambda b: _set(b, "sensory", [{"name": KEYWORDS[0], "minimum": 4,
                                    "maximum": 1}]),
     "sensory[0].minimum"),
    ("sensory over catalog cap",
     lambda b: _set(b, "sensory", [{"name": KEYWORDS[0], "minimum": 0,
                                    "maximum": 1}] * 49),
     "sensory"),
    ("srm below range",
     lambda b: _set(b, "color_srm", {"minimum": -1, "maximum": 20}),
     "color_srm.minimum"),
    ("srm above range",
     lambda b: _set(b, "color_srm", {"minimum": 0, "maximum": 300}),
     "color_srm.maximum"),
    ("inverted srm",
     lambda b: _set(b, "color_srm", {"minimum": 20, "maximum": 5}),
     "color_srm.minimum"),
    ("missing section", lambda b: {k: v for k, v in b.items() if k != "equipment"},
     "equipment"),
]


@pytest.mark.parametrize("label,mutate,path",
                         INVALID_CASES, ids=[c[0] for c in INVALID_CASES])
def test_invalid_brief_rejected_with_field_path(client, label, mutate, path):
    resp = client.post(RECIPES, json=mutate(base()))
    assert resp.status_code == 422
    assert resp.mimetype == "application/problem+json"
    body = resp.get_json()
    assert body["code"] == "invalid_brief"
    assert path in {e["path"] for e in body["errors"]}


def test_non_finite_numbers_are_rejected(client):
    # JSON's NaN/Infinity survive decoding; the finite guards must reject them.
    raw = ('{"version":1,"style":{"slug":"american-pale-ale",'
           '"original_gravity":NaN},'
           '"equipment":{"batch_volume_gallons":Infinity,'
           '"mash_efficiency_percent":75},'
           '"fermentables":{"allowed_slugs":["%s"],"bounds":[],'
           '"maximum_count":1},"sensory":[],'
           '"color_srm":{"minimum":0,"maximum":20}}') % STYLE_SLUGS[0]
    resp = client.post(RECIPES, data=raw, content_type="application/json")
    assert resp.status_code == 422
    paths = {e["path"] for e in resp.get_json()["errors"]}
    assert "style.original_gravity" in paths
    assert "equipment.batch_volume_gallons" in paths


def test_errors_name_paths_not_values(client):
    # A rejected field is located by path; its value is never echoed back.
    resp = client.post(RECIPES, json=_ferm(base(),
                       allowed_slugs=["sentinel-secret-value"], maximum_count=1))
    assert resp.status_code == 422
    assert "sentinel-secret-value" not in resp.get_data(as_text=True)


def test_empty_brief_is_rejected(client):
    resp = client.post(RECIPES, json={})
    assert resp.status_code == 422
    assert resp.get_json()["code"] == "empty_brief"


# -- request boundary: size and media type -----------------------------------

def test_over_cap_body_rejected_before_parse(client):
    # A body past 64 KiB is refused as request_too_large, never parsed.
    raw = '{"pad":"' + "a" * 70000 + '"}'
    resp = client.post(RECIPES, data=raw, content_type="application/json")
    assert resp.status_code == 413
    assert resp.get_json()["code"] == "request_too_large"


def test_legitimate_sized_body_passes_the_cap(client):
    # A large-but-under-cap body clears the size gate (and then fails validation,
    # proving the cap did not reject it for size).
    raw = '{"pad":"' + "a" * 60000 + '"}'
    resp = client.post(RECIPES, data=raw, content_type="application/json")
    assert resp.status_code != 413
    assert resp.get_json()["code"] != "request_too_large"


def test_wrong_media_type_rejected(client):
    resp = client.post(RECIPES, data="{}", content_type="text/plain")
    assert resp.status_code == 415
    assert resp.get_json()["code"] == "unsupported_media_type"


def test_malformed_json_rejected(client):
    resp = client.post(RECIPES, data="{not json", content_type="application/json")
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "malformed_json"


def test_every_failure_carries_a_request_id(client):
    resp = client.post(RECIPES, json={})
    body = resp.get_json()
    assert body["request_id"]
    assert resp.headers["X-Request-Id"] == body["request_id"]


# -- token bucket: burst, refill, expiry (fake clock) ------------------------

def test_token_bucket_bursts_then_refills():
    bucket = _TokenBucket(capacity=2, refill=6 / 60.0, now=0.0)
    assert bucket.take(0.0)[0] is True
    assert bucket.take(0.0)[0] is True
    allowed, retry = bucket.take(0.0)
    assert allowed is False
    assert retry == pytest.approx(10.0)   # one token per ten seconds
    assert bucket.take(10.0)[0] is True    # refilled after ten seconds


def test_rate_limiter_refills_and_expires_idle_buckets():
    now = {"t": 0.0}
    limiter = RateLimiter(capacity=2, refill=6 / 60.0, idle_expiry=600,
                          clock=lambda: now["t"])
    assert limiter.check("visitor")[0] is True
    assert limiter.check("visitor")[0] is True
    allowed, retry = limiter.check("visitor")
    assert allowed is False and retry == pytest.approx(10.0)
    now["t"] = 10.0
    assert limiter.check("visitor")[0] is True    # refilled
    now["t"] = 10.0 + 601                          # idle past expiry
    limiter.check("someone-else")                  # triggers the sweep
    assert "visitor" not in limiter._buckets


def test_seventh_request_is_rate_limited(client, monkeypatch):
    # Six per minute, burst two: with the bucket depth exhausted the next request
    # is refused as rate_limited with an accurate Retry-After. Empty bodies keep
    # the solver out of it — the limiter is checked before the brief is parsed.
    now = {"t": 0.0}
    monkeypatch.setattr(envelope, "RATE_LIMITER",
                        RateLimiter(capacity=2, refill=6 / 60.0,
                                    clock=lambda: now["t"]))
    assert client.post(RECIPES, json={}).status_code == 422   # burst 1
    assert client.post(RECIPES, json={}).status_code == 422   # burst 2
    limited = client.post(RECIPES, json={})
    assert limited.status_code == 429
    assert limited.get_json()["code"] == "rate_limited"
    assert limited.headers["Retry-After"] == "10"
    now["t"] = 10.0                                            # a token refills
    assert client.post(RECIPES, json={}).status_code == 422


# -- concurrency: two slots, no queue, recovery ------------------------------

def test_overflow_is_busy_with_no_queue(client, monkeypatch):
    guard = ConcurrencyGuard(slots=2)
    monkeypatch.setattr(envelope, "CONCURRENCY", guard)
    assert guard.acquire() and guard.acquire()   # both slots occupied
    resp = client.post(RECIPES, json=base())
    assert resp.status_code == 503
    assert resp.get_json()["code"] == "busy"
    assert resp.headers["Retry-After"] == "1"
    guard.release()
    guard.release()
    assert client.post(RECIPES, json=base()).status_code == 200


def test_slot_recovered_after_internal_error(client, monkeypatch):
    # One slot; the guarded solve raises. A leaked slot would make the next
    # request busy — a second 500 proves the slot was released, not queued.
    guard = ConcurrencyGuard(slots=1)
    monkeypatch.setattr(envelope, "CONCURRENCY", guard)

    class Boom:
        def generate(self, **kwargs):
            raise RuntimeError("solver blew up")

    monkeypatch.setattr(views, "_solver_for", lambda derived: Boom())
    assert client.post(RECIPES, json=base()).status_code == 500
    assert client.post(RECIPES, json=base()).status_code == 500


def test_slot_recovered_after_deadline(client, monkeypatch):
    guard = ConcurrencyGuard(slots=1)
    monkeypatch.setattr(envelope, "CONCURRENCY", guard)
    monkeypatch.setattr(views, "SOLVER_CONFIG",
                        SolverConfig(request_deadline_seconds=0))
    first = client.post(RECIPES, json=base())
    assert first.status_code == 503 and first.get_json()["code"] == "deadline_exceeded"
    second = client.post(RECIPES, json=base())
    # Not "busy" — the slot from the timed-out first request was recovered.
    assert second.get_json()["code"] == "deadline_exceeded"


# -- shared deadline across every compute path (fake clock) ------------------

class _SpentClock:
    """Zero on first read (so a budget's deadline is set), far past it after —
    every subsequent budget check sees the shared deadline already blown."""

    def __init__(self):
        self.reads = 0

    def __call__(self):
        self.reads += 1
        return 0.0 if self.reads == 1 else 10_000.0


def test_shared_deadline_governs_validity_range_and_generation(client, monkeypatch):
    def spend_next():
        monkeypatch.setattr(views, "_clock", _SpentClock())

    spend_next()
    feas = client.post(FEASIBILITY, json=base())
    assert feas.status_code == 200 and feas.get_json()["status"] == "deadline_exceeded"

    spend_next()
    body = _set(base(), "descriptor", KEYWORDS[0])
    rng = client.post(SENSORY_RANGE, json=body)
    assert rng.status_code == 200 and rng.get_json()["status"] == "deadline_exceeded"

    spend_next()
    gen = client.post(RECIPES, json=base())
    assert gen.status_code == 503 and gen.get_json()["code"] == "deadline_exceeded"


# -- scrubbed logging boundary -----------------------------------------------

@pytest.fixture
def captured_public_log():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("brewgen.public")
    logger.addHandler(handler)
    previous = logger.level
    logger.setLevel(logging.DEBUG)
    try:
        yield stream
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)


SENTINELS = ["sentinel-body", "sentinel-cookie", "sentinel-agent", "203.0.113.7"]


def test_public_log_omits_body_address_and_headers(client, captured_public_log):
    brief = _ferm(base(), allowed_slugs=["sentinel-body"], maximum_count=1)
    client.post(RECIPES, json=brief, headers={
        "User-Agent": "sentinel-agent",
        "Cookie": "session=sentinel-cookie",
        "X-Forwarded-For": "203.0.113.7",
        "Referer": "http://sentinel-body/x",
    })
    logged = captured_public_log.getvalue()
    assert "op=generate" in logged        # the event was recorded...
    for sentinel in SENTINELS:
        assert sentinel not in logged      # ...but nothing sensitive rode along
    assert "127.0.0.1" not in logged       # nor the raw peer address


def test_internal_error_log_keeps_stack_not_request(client, monkeypatch,
                                                    captured_public_log):
    class Boom:
        def generate(self, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(views, "_solver_for", lambda derived: Boom())
    resp = client.post(RECIPES, json=_ferm(base(), allowed_slugs=STYLE_SLUGS,
                                           bounds=[]))
    assert resp.status_code == 500
    logged = captured_public_log.getvalue()
    assert "RuntimeError" in logged        # exception type retained for triage
    assert "outcome=internal_error" in logged
    assert STYLE_SLUGS[0] not in logged    # the request itself never attached


def test_address_hasher_is_stable_within_a_day_and_rotates():
    day = {"n": 0}
    hasher = AddressHasher(clock=lambda: day["n"] * 86400)
    first = hasher.hash("203.0.113.7")
    assert hasher.hash("203.0.113.7") == first      # deterministic within a day
    assert hasher.hash("198.51.100.2") != first     # distinct address, distinct key
    day["n"] = 1
    assert hasher.hash("203.0.113.7") != first       # key rotated across the day
