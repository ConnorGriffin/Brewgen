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
