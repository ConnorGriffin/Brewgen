"""The interactive feasibility and focused-range operations, on the versioned
brief.

The public brief editor drives two lighter compute paths besides generation: a
whole-brief feasibility check and a focused single-descriptor range. Both now
take the strict ``version: 1`` brief and derive the category/style-model
constraints server-side; the focused range still holds every other configured
constraint fixed while dropping the target descriptor's own bound. The
transitional equivalence to the retired all-descriptor sweep and the real-style
performance gate are preserved against the brief-derived solver."""

import time

import pytest

from conftest import make_brief
from brewgen.backend import envelope, views
from brewgen.backend.brief import parse_brief

STYLE = views.all_styles.get_style_by_slug("american-pale-ale")
KEYWORDS = sorted(views.all_grains.get_sensory_keywords())


def _derive(brief):
    return parse_brief(brief, views.all_grains, views.all_styles,
                       allow_extra=("descriptor",))


def _solver(brief):
    return views._solver_for(_derive(brief))


# A style solver and its unconstrained descriptor spans, computed once, so the
# focused-range mechanics can be exercised on descriptors that actually vary.
_STYLE_SOLVER = _solver(make_brief(STYLE, min_srm=3.0, max_srm=30.0))
_SWEEP = {r["name"]: (r["min"], r["max"]) for r in _STYLE_SOLVER.sensory_ranges()}
_VARYING = [name for name, (lo, hi) in _SWEEP.items() if hi > lo]
_ZERO = [name for name, (lo, hi) in _SWEEP.items() if hi < 0.3]
TARGET = _VARYING[0]
OTHER = _VARYING[1]


@pytest.fixture(autouse=True)
def _relaxed_envelope(monkeypatch):
    monkeypatch.setattr(envelope, "RATE_LIMITER",
                        envelope.RateLimiter(capacity=1000, refill=1000))
    monkeypatch.setattr(envelope, "CONCURRENCY", envelope.ConcurrencyGuard(slots=8))


@pytest.fixture
def client():
    return views.app.test_client()


def _range_body(descriptor, **overrides):
    brief = make_brief(STYLE, min_srm=3.0, max_srm=30.0, **overrides)
    brief["descriptor"] = descriptor
    return brief


# -- focused range: exact results --------------------------------------------

def test_sensory_range_returns_exact_min_max(client):
    body = _range_body(TARGET)
    resp = client.post("/api/v1/grains/sensory-range", json=body)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "feasible"
    assert data["name"] == TARGET
    assert data["min"] <= data["max"]

    # The HTTP answer is exactly what the solver computes for the same brief,
    # colour band and all.
    derived = _derive(body)
    result = views._solver_for(derived).sensory_range(
        TARGET, color_context=views._color_context(derived))
    assert data["min"] == result.minimum
    assert data["max"] == result.maximum


def test_sensory_range_excludes_targets_own_bound(client):
    unbounded = client.post(
        "/api/v1/grains/sensory-range", json=_range_body(TARGET)).get_json()

    # Pin the same descriptor to a narrow sliver and re-open its range.
    midpoint = (unbounded["min"] + unbounded["max"]) / 2
    pinned = _range_body(
        TARGET, sensory=[{"name": TARGET, "minimum": midpoint, "maximum": midpoint}])
    reopened = client.post("/api/v1/grains/sensory-range", json=pinned).get_json()

    # The stale bound is dropped, so the reopened span is the full one again.
    assert reopened["min"] == unbounded["min"]
    assert reopened["max"] == unbounded["max"]


def test_sensory_range_respects_other_configured_bounds(client):
    open_span = client.post(
        "/api/v1/grains/sensory-range", json=_range_body(TARGET)).get_json()
    other_span = client.post(
        "/api/v1/grains/sensory-range", json=_range_body(OTHER)).get_json()

    # Pin the *other* descriptor to its own minimum; the target range may shift
    # but must remain within the unconstrained span.
    constrained = _range_body(
        TARGET, sensory=[{"name": OTHER, "minimum": other_span["min"],
                          "maximum": other_span["min"]}])
    narrowed = client.post("/api/v1/grains/sensory-range", json=constrained).get_json()
    assert narrowed["status"] == "feasible"
    assert narrowed["min"] >= open_span["min"] - 1e-6
    assert narrowed["max"] <= open_span["max"] + 1e-6


# -- focused range: invalid --------------------------------------------------

def test_sensory_range_unknown_descriptor_is_invalid(client):
    resp = client.post("/api/v1/grains/sensory-range",
                       json=_range_body("not-a-real-descriptor"))
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["code"] == "invalid_brief"
    assert "descriptor" in {e["path"] for e in body["errors"]}


def test_sensory_range_missing_descriptor_is_invalid(client):
    body = make_brief(STYLE)   # no descriptor sibling
    resp = client.post("/api/v1/grains/sensory-range", json=body)
    assert resp.status_code == 422
    assert resp.get_json()["code"] == "invalid_brief"


# -- full-brief feasibility --------------------------------------------------

def test_feasibility_reports_feasible(client):
    resp = client.post("/api/v1/grains/feasibility",
                       json=make_brief(STYLE, min_srm=3.0, max_srm=30.0))
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "feasible"


def test_feasibility_infeasible_on_impossible_color(client):
    # Pale grains, but a near-black target: the colour band rules it out, proving
    # colour is part of the feasibility check.
    resp = client.post("/api/v1/grains/feasibility",
                       json=make_brief(STYLE, min_srm=200.0, max_srm=255.0))
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "infeasible"


@pytest.mark.skipif(not _ZERO, reason="style has no all-but-absent descriptor")
def test_feasibility_infeasible_on_contradictory_sensory(client):
    # Demand a tasteable amount of a descriptor these grains cannot deliver.
    zero = _ZERO[0]
    resp = client.post("/api/v1/grains/feasibility", json=make_brief(
        STYLE, min_srm=3.0, max_srm=30.0,
        sensory=[{"name": zero, "minimum": 1.0, "maximum": 5.0}]))
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "infeasible"


# -- the plural sweep path is gone -------------------------------------------

def test_all_descriptor_sweep_endpoint_removed(client):
    resp = client.post("/api/v1/grains/sensory-profiles", json=make_brief(STYLE))
    # No POST handler remains for the retired sweep (the SPA catch-all serves
    # GET only), so the path can never run it.
    assert resp.status_code in (404, 405)


# -- transitional equivalence (issue #36) ------------------------------------

@pytest.mark.parametrize("style_slug",
                         [s.slug for s in views.all_styles.style_list[:2]])
def test_focused_range_matches_full_sweep(style_slug):
    """Each focused range (no colour band) equals the old full-sweep value for
    the same descriptor, across representative committed styles."""
    style_obj = views.all_styles.get_style_by_slug(style_slug)
    solver = _solver(make_brief(style_obj, min_srm=0.0, max_srm=255.0))

    sweep = {r["name"]: (r["min"], r["max"]) for r in solver.sensory_ranges()}
    assert sweep, "style model should be feasible for the sweep"
    for name, (expected_min, expected_max) in sweep.items():
        focused = solver.sensory_range(name)
        assert focused.status.value == "feasible"
        assert focused.minimum == expected_min
        assert focused.maximum == expected_max


# -- real-style performance gate ---------------------------------------------

def test_focused_range_and_feasibility_under_one_second():
    solver = _solver(make_brief(STYLE, min_srm=3.0, max_srm=30.0))

    start = time.monotonic()
    solver.sensory_range(KEYWORDS[0])
    assert time.monotonic() - start < 1.0

    start = time.monotonic()
    solver.feasibility()
    assert time.monotonic() - start < 1.0
