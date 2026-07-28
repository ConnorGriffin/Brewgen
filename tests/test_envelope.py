"""Integration coverage for the anonymous-compute envelope, exercised through
the public HTTP surface of the three compute endpoints.

Proves, in one place: the media-type/size/JSON gates, the versioned brief
contract, the per-visitor rate limit (burst then refill, keyed per trusted
hop), the two-slot no-queue concurrency ceiling, the deadline->503 mapping, the
stable problem+json failure contract with no echoed input, and the
aggregate-only privacy log. The size cap carries a regression guard: an
oversized body must be rejected before the solver is ever built."""

import json
import logging
import threading
import time

import pytest

from brewgen.backend import views, envelope
from brewgen.backend.solver.fermentables import SolverConfig

COMPUTE_ENDPOINTS = [
    "/api/v1/grains/sensory-range",
    "/api/v1/grains/feasibility",
    "/api/v1/grains/recipes",
]


@pytest.fixture
def client():
    return views.app.test_client()


def _brief(endpoint=None):
    """A valid brief for any compute endpoint (adds a descriptor for the focused
    range endpoint, whose contract requires one)."""
    grains = views.all_grains.get_grain_list()
    by_cat = {}
    for g in grains:
        by_cat.setdefault(g["category"], []).append(g["slug"])
    fermentables = [
        {"slug": s, "min_percent": 0, "max_percent": 100} for s in by_cat["base"][:2]
    ] + [
        {"slug": s, "min_percent": 0, "max_percent": 25} for s in by_cat["crystal"][:2]
    ]
    brief = {
        "fermentable_list": fermentables,
        "category_model": [
            {"name": "base", "min_percent": 60, "max_percent": 100,
             "unique_fermentable_count": 2},
            {"name": "crystal", "min_percent": 0, "max_percent": 25,
             "unique_fermentable_count": 2},
        ],
        "max_unique_fermentables": 4,
        "equipment_profile": {"target_volume_gallons": 5.5, "mash_efficiency": 75},
        "beer_profile": {"min_color_srm": 3, "max_color_srm": 20,
                         "original_sg": 1.055},
    }
    if endpoint and endpoint.endswith("sensory-range"):
        brief["descriptor"] = views.all_grains.get_sensory_keywords()[0]
    return brief


def _post_raw(client, endpoint, raw, content_type="application/json"):
    return client.post(endpoint, data=raw, content_type=content_type)


# -- size / media-type / JSON gates ----------------------------------------

def test_oversized_body_is_413_before_the_solver_is_built(client, monkeypatch):
    # Regression guard: a 65_537-byte body must be rejected before any solver
    # work. The body is *valid, padded JSON* that would reach the solver if the
    # cap regressed behind solver work, so a spy that raises when built proves
    # the cap fires first.
    def spy(_data):
        raise AssertionError("solver must not be built for an oversized body")
    monkeypatch.setattr(views, "_build_fermentable_solver", spy)

    body = json.dumps(_brief("/api/v1/grains/recipes"))
    body += " " * (65_537 - len(body))
    assert len(body) == 65_537
    resp = _post_raw(client, "/api/v1/grains/recipes", body)

    assert resp.status_code == 413
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["outcome"] == "oversized"


@pytest.mark.parametrize("endpoint", COMPUTE_ENDPOINTS)
def test_wrong_media_type_is_415(client, endpoint):
    resp = _post_raw(client, endpoint, "descriptor=malty", content_type="text/plain")
    assert resp.status_code == 415
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["outcome"] == "wrong_media_type"


@pytest.mark.parametrize("endpoint", COMPUTE_ENDPOINTS)
def test_non_json_body_is_400(client, endpoint):
    resp = _post_raw(client, endpoint, "{not valid json")
    assert resp.status_code == 400
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["outcome"] == "malformed_json"


@pytest.mark.parametrize("endpoint", COMPUTE_ENDPOINTS)
def test_empty_body_is_400(client, endpoint):
    resp = _post_raw(client, endpoint, "")
    assert resp.status_code == 400
    assert resp.get_json()["outcome"] == "malformed_json"


# -- versioned brief contract ----------------------------------------------

def _mutations():
    keyword_count = len(views.all_grains.get_sensory_keywords())

    def unknown_field(b):
        b["surprise"] = True

    def unknown_slug(b):
        b["fermentable_list"][0]["slug"] = "definitely-not-a-real-grain"

    def duplicate_slug(b):
        b["fermentable_list"].append(dict(b["fermentable_list"][0]))

    def non_finite(b):
        b["max_unique_fermentables"] = float("inf")

    def inverted_range(b):
        b["fermentable_list"][0]["min_percent"] = 90
        b["fermentable_list"][0]["max_percent"] = 10

    def over_cardinality(b):
        b["sensory_model"] = [{"name": "x", "min": 0, "max": 1}
                              for _ in range(keyword_count + 1)]

    return [unknown_field, unknown_slug, duplicate_slug, non_finite,
            inverted_range, over_cardinality]


@pytest.mark.parametrize("endpoint", COMPUTE_ENDPOINTS)
@pytest.mark.parametrize("mutate", _mutations(), ids=lambda f: f.__name__)
def test_invalid_brief_is_422_problem_json(client, endpoint, mutate):
    brief = _brief(endpoint)
    mutate(brief)
    # json.dumps serializes non-finite numbers as Infinity/NaN, which the server
    # parses and the contract then rejects for non-finiteness.
    resp = _post_raw(client, endpoint, json.dumps(brief))
    assert resp.status_code == 422
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["outcome"] == "invalid"


def test_unknown_brief_version_is_rejected(client):
    brief = _brief("/api/v1/grains/recipes")
    brief["version"] = 2
    resp = _post_raw(client, "/api/v1/grains/recipes", json.dumps(brief))
    assert resp.status_code == 422
    assert resp.get_json()["outcome"] == "invalid"


# -- per-visitor rate limit -------------------------------------------------

def _frozen_limiter(monkeypatch, now=1000.0):
    limiter = envelope.RateLimiter(clock=lambda: now)
    monkeypatch.setattr(envelope, "RATE_LIMITER", limiter)
    return limiter


def test_rate_limit_allows_a_burst_of_two_then_429(client, monkeypatch):
    _frozen_limiter(monkeypatch)  # frozen clock: no refill mid-burst
    body = _brief("/api/v1/grains/feasibility")
    assert client.post("/api/v1/grains/feasibility", json=body).status_code != 429
    assert client.post("/api/v1/grains/feasibility", json=body).status_code != 429
    third = client.post("/api/v1/grains/feasibility", json=body)
    assert third.status_code == 429
    assert third.mimetype == "application/problem+json"
    assert third.get_json()["outcome"] == "rate_limited"


def test_rate_limit_refills_at_six_per_minute(client, monkeypatch):
    clock = {"now": 0.0}
    monkeypatch.setattr(envelope, "RATE_LIMITER",
                        envelope.RateLimiter(clock=lambda: clock["now"]))
    body = _brief("/api/v1/grains/feasibility")
    # Spend the burst of two, then throttle.
    client.post("/api/v1/grains/feasibility", json=body)
    client.post("/api/v1/grains/feasibility", json=body)
    assert client.post("/api/v1/grains/feasibility", json=body).status_code == 429
    # One token refills after ten seconds (six per minute).
    clock["now"] = 10.0
    assert client.post("/api/v1/grains/feasibility", json=body).status_code != 429
    assert client.post("/api/v1/grains/feasibility", json=body).status_code == 429


def test_rate_limited_carries_exact_retry_after(client, monkeypatch):
    # Right after the burst the frozen bucket sits at zero tokens, so one refills
    # in exactly (1 - 0) / 0.1 = 10 s. The refusal must state that, both as the
    # RFC 7231 header and as the body field the frontend renders.
    _frozen_limiter(monkeypatch)
    body = _brief("/api/v1/grains/feasibility")
    client.post("/api/v1/grains/feasibility", json=body)
    client.post("/api/v1/grains/feasibility", json=body)
    third = client.post("/api/v1/grains/feasibility", json=body)
    assert third.status_code == 429
    assert third.headers["Retry-After"] == "10"
    assert third.get_json()["retry_after"] == 10


def test_busy_shed_does_not_charge_the_visitor(client, monkeypatch):
    # Regression guard for the charge bug: a request shed as busy never reaches
    # solver work, so it must leave the visitor's allowance untouched. Against
    # the old gate (charge, then refuse) the second post below would already be
    # 429; with the busy refund the full burst of two survives the shed.
    _frozen_limiter(monkeypatch)
    body = _brief("/api/v1/grains/feasibility")

    assert envelope.SLOTS.acquire(blocking=False) is True
    assert envelope.SLOTS.acquire(blocking=False) is True
    try:
        busy = client.post("/api/v1/grains/feasibility", json=body)
        assert busy.status_code == 503
        assert busy.get_json()["outcome"] == "busy"
        assert busy.headers["Retry-After"] == "1"
        assert busy.get_json()["retry_after"] == 1
    finally:
        envelope.SLOTS.release()
        envelope.SLOTS.release()

    # The visitor still has both burst tokens: two allowed, then 429.
    assert client.post("/api/v1/grains/feasibility", json=body).status_code != 429
    assert client.post("/api/v1/grains/feasibility", json=body).status_code != 429
    assert client.post("/api/v1/grains/feasibility", json=body).status_code == 429


def test_allow_retry_timing_is_exact_under_an_injected_clock():
    # The limiter's retry seconds come from the same clock reading as the
    # decision, so they are exact without any wall-clock waiting.
    now = {"t": 0.0}
    limiter = envelope.RateLimiter(clock=lambda: now["t"])
    addr = "203.0.113.5"
    assert limiter.allow(addr) == (True, 0.0)
    assert limiter.allow(addr) == (True, 0.0)
    allowed, retry = limiter.allow(addr)
    assert allowed is False
    assert retry == 10.0                       # empty bucket -> a full ten seconds
    now["t"] = 5.0                             # half a token has refilled
    allowed, retry = limiter.allow(addr)
    assert allowed is False
    assert retry == pytest.approx(5.0)


def test_busy_refund_restores_the_bucket_at_a_frozen_clock():
    # refund credits exactly one token back (capped at capacity) at the same
    # clock instant, so the busy path can undo its own charge.
    now = {"t": 0.0}
    limiter = envelope.RateLimiter(clock=lambda: now["t"])
    addr = "203.0.113.6"
    assert limiter.allow(addr)[0] is True
    assert limiter.allow(addr)[0] is True
    assert limiter.allow(addr)[0] is False     # burst spent
    limiter.refund(addr)
    assert limiter.allow(addr)[0] is True       # the refunded token is spendable
    assert limiter.allow(addr)[0] is False


def test_rate_limit_is_keyed_per_visitor_via_one_trusted_hop(client, monkeypatch):
    _frozen_limiter(monkeypatch)
    body = _brief("/api/v1/grains/feasibility")

    def post(ip):
        return client.post("/api/v1/grains/feasibility", json=body,
                           headers={"X-Forwarded-For": ip})

    # One visitor spends its burst and is throttled...
    post("203.0.113.1")
    post("203.0.113.1")
    assert post("203.0.113.1").status_code == 429
    # ...while a different forwarded hop is unaffected: the key is the client,
    # not the relay (ProxyFix resolves exactly one hop).
    assert post("203.0.113.9").status_code != 429


# -- two-slot, no-queue concurrency ----------------------------------------

def test_two_solver_slots_are_available(client):
    # Holding one slot leaves the second free, so a request still runs.
    assert envelope.SLOTS.acquire(blocking=False) is True
    try:
        resp = client.post("/api/v1/grains/recipes", json=_brief())
        assert resp.status_code != 503
    finally:
        envelope.SLOTS.release()


def test_third_concurrent_request_is_busy_503(client):
    # Both slots held (two solves in flight): the next request is immediately
    # busy, no queue, no wait.
    assert envelope.SLOTS.acquire(blocking=False) is True
    assert envelope.SLOTS.acquire(blocking=False) is True
    try:
        resp = client.post("/api/v1/grains/recipes", json=_brief())
        assert resp.status_code == 503
        assert resp.mimetype == "application/problem+json"
        assert resp.get_json()["outcome"] == "busy"
    finally:
        envelope.SLOTS.release()
        envelope.SLOTS.release()


# -- deadline -> 503 --------------------------------------------------------

@pytest.mark.parametrize("endpoint", [
    "/api/v1/grains/feasibility", "/api/v1/grains/recipes"])
def test_deadline_maps_to_503(client, monkeypatch, endpoint):
    monkeypatch.setattr(views, "SOLVER_CONFIG",
                        SolverConfig(request_deadline_seconds=0))
    resp = client.post(endpoint, json=_brief(endpoint))
    assert resp.status_code == 503
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["outcome"] == "deadline"


# -- problem+json contract: no echo, stable shape --------------------------

def test_problem_json_never_echoes_input(client):
    marker = "zzz-marker-not-a-real-slug"
    brief = _brief("/api/v1/grains/recipes")
    brief["fermentable_list"][0]["slug"] = marker
    resp = _post_raw(client, "/api/v1/grains/recipes", json.dumps(brief))
    assert resp.status_code == 422
    text = resp.get_data(as_text=True)
    assert marker not in text
    assert set(resp.get_json()) == {"type", "title", "status", "outcome"}


# -- privacy log ------------------------------------------------------------

def test_log_carries_only_aggregate_fields(client, caplog):
    marker_ip = "203.0.113.77"
    marker_slug = _brief()["fermentable_list"][0]["slug"]
    with caplog.at_level(logging.INFO, logger="brewgen.compute"):
        client.post("/api/v1/grains/recipes", json=_brief(),
                    headers={"X-Forwarded-For": marker_ip})

    records = [r for r in caplog.records if r.name == "brewgen.compute"]
    assert len(records) == 1, "exactly one aggregate line per compute request"
    payload = json.loads(records[0].getMessage())
    assert set(payload) == {"timestamp", "request_id", "operation",
                            "outcome", "status", "duration"}
    assert payload["operation"] == "recipes"
    # The address, its hash, and brief content never reach the log.
    assert marker_ip not in records[0].getMessage()
    assert marker_slug not in records[0].getMessage()


# -- single-flight coalescing + short-lived result cache -------------------

def _counting_solver_spy(monkeypatch, gate=None):
    """Replace the solver builder with a spy that counts executions and,
    optionally, blocks the leader on ``gate`` so followers reliably attach while
    it is still in flight. Returns the shared call counter (a list)."""
    real_build = views._build_fermentable_solver
    calls = []
    lock = threading.Lock()

    def spy(data):
        with lock:
            calls.append(1)
        if gate is not None:
            gate.wait(timeout=5)
        return real_build(data)

    monkeypatch.setattr(views, "_build_fermentable_solver", spy)
    return calls


def _post_from(client_endpoint, brief, ip):
    resp = views.app.test_client().post(
        client_endpoint, json=brief, headers={"X-Forwarded-For": ip})
    return resp


def test_concurrent_identical_briefs_run_the_solver_once(monkeypatch):
    # N byte-identical valid briefs racing one endpoint must cause exactly one
    # solver execution; every caller gets the same 200 body, and no follower is
    # turned away busy even though N exceeds the two-slot ceiling. Distinct
    # forwarded hops keep the per-visitor rate limit out of the way -- the
    # canonical key is the brief, not the address.
    gate = threading.Event()
    calls = _counting_solver_spy(monkeypatch, gate=gate)
    endpoint = "/api/v1/grains/feasibility"
    brief = _brief(endpoint)

    results = {}

    def worker(i):
        results[i] = _post_from(endpoint, brief, "203.0.113.%d" % (i + 1))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    # Let the leader reach the solver and the followers reach their wait.
    deadline = time.monotonic() + 5
    while not calls and time.monotonic() < deadline:
        time.sleep(0.01)
    time.sleep(0.1)
    gate.set()
    for t in threads:
        t.join(timeout=5)

    assert len(calls) == 1, "identical concurrent briefs must share one execution"
    bodies = {r.get_data() for r in results.values()}
    statuses = {r.status_code for r in results.values()}
    assert statuses == {200}, "no follower is turned away while one leader runs"
    assert len(bodies) == 1, "every caller receives the byte-identical body"


def test_identical_brief_replays_from_cache_then_recomputes_after_ttl(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(envelope, "COALESCER",
                        envelope.ComputeCoalescer(clock=lambda: clock["now"]))
    calls = _counting_solver_spy(monkeypatch)
    endpoint = "/api/v1/grains/feasibility"
    brief = _brief(endpoint)

    first = _post_from(endpoint, brief, "203.0.113.1")
    assert first.status_code == 200
    assert len(calls) == 1
    # A repeat inside the TTL replays the cached answer -- no new solver work.
    cached = _post_from(endpoint, brief, "203.0.113.2")
    assert cached.status_code == 200
    assert cached.get_data() == first.get_data()
    assert len(calls) == 1
    # Past the TTL the cache entry is gone and the brief recomputes.
    clock["now"] += envelope.RESULT_CACHE_TTL_SECONDS + 1
    _post_from(endpoint, brief, "203.0.113.3")
    assert len(calls) == 2


def test_different_canonical_keys_never_share_a_result(monkeypatch):
    calls = _counting_solver_spy(monkeypatch)
    endpoint = "/api/v1/grains/feasibility"
    a = _brief(endpoint)
    b = _brief(endpoint)
    b["fermentable_list"][0]["max_percent"] = 90  # a different grain bound

    _post_from(endpoint, a, "203.0.113.1")
    _post_from(endpoint, b, "203.0.113.2")
    assert len(calls) == 2, "briefs with different keys must not false-share"


def test_sensory_range_key_ignores_the_queried_descriptors_own_bound(monkeypatch):
    calls = _counting_solver_spy(monkeypatch)
    endpoint = "/api/v1/grains/sensory-range"
    keywords = views.all_grains.get_sensory_keywords()
    target, other = keywords[0], keywords[1]

    def brief(target_bound, other_bound):
        b = _brief(endpoint)
        b["descriptor"] = target
        b["sensory_model"] = [
            {"name": target, "min": target_bound[0], "max": target_bound[1]},
            {"name": other, "min": other_bound[0], "max": other_bound[1]},
        ]
        return b

    # Differ only in the queried descriptor's own bound -> one execution.
    _post_from(endpoint, brief((0, 5), (0, 5)), "203.0.113.1")
    _post_from(endpoint, brief((1, 4), (0, 5)), "203.0.113.2")
    assert len(calls) == 1, "the queried descriptor's own bound is not part of the key"

    # Differ in a *different* descriptor's bound -> a second execution.
    _post_from(endpoint, brief((0, 5), (0, 4)), "203.0.113.3")
    assert len(calls) == 2, "another descriptor's bound does change the key"


def test_deadline_outcome_is_not_cached(monkeypatch):
    # A transient 503 must never be replayed: an immediately repeated identical
    # brief re-enters the solver rather than being handed the cached timeout.
    monkeypatch.setattr(views, "SOLVER_CONFIG",
                        SolverConfig(request_deadline_seconds=0))
    calls = _counting_solver_spy(monkeypatch)
    endpoint = "/api/v1/grains/feasibility"
    brief = _brief(endpoint)

    first = _post_from(endpoint, brief, "203.0.113.1")
    second = _post_from(endpoint, brief, "203.0.113.2")
    assert first.status_code == 503
    assert second.status_code == 503
    assert len(calls) == 2, "a deadline is not cached; the repeat recomputes"
