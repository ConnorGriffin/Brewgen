"""Public-interface tests for the bounded interactive-flavor operations.

Covers issue #36: a focused per-descriptor range and a full-brief feasibility
check replace the retired all-descriptor sensory sweep. Behaviour is exercised
through the Flask HTTP interface; the transitional equivalence and performance
checks call the solver the same way the views do.

Run with the project venv, e.g.::

    .venv/bin/python -m pytest tests/test_interactive_flavor_range.py
"""

import time

import pytest

from conftest import make_choice_brief
from brewgen.backend import views, envelope
from brewgen.backend.models import grain, style
from brewgen.backend.solver.fermentables import SolverConfig

GRAINS = grain.GrainList()
STYLES = style.StyleModel()
SLUGS = GRAINS.get_grain_slugs()
KEYWORDS = sorted(GRAINS.get_sensory_keywords())


@pytest.fixture
def client(monkeypatch):
    # These are solver-semantics tests, not envelope tests: several make more
    # than the burst of two rapid calls, so install a non-throttling limiter and
    # non-binding deadlines. Dedicated tests below own deadline handling and
    # real performance; test_envelope owns the real rate-limit contract.
    monkeypatch.setattr(envelope, "RATE_LIMITER",
                        envelope.RateLimiter(per_minute=6000, burst=1000))
    monkeypatch.setattr(
        views,
        "SOLVER_CONFIG",
        SolverConfig(
            solver_time_limit_seconds=float("inf"),
            request_deadline_seconds=float("inf"),
        ),
    )
    views.app.testing = True
    return views.app.test_client()


def _feasible_body(**overrides):
    """A known-feasible public choice brief for one shipped style."""
    body = make_choice_brief(
        STYLES.get_style_by_slug("american-pale-ale"))
    body.update(overrides)
    return body


def _style_body(style_object):
    """A representative brief drawn from a committed style, with the style's
    own grain and category usage but no sensory bounds (so the full sweep and
    the focused path see an identical model)."""
    return make_choice_brief(style_object)


# -- focused range: exact results --------------------------------------------

def test_sensory_range_returns_exact_min_max(client):
    body = _feasible_body(descriptor=KEYWORDS[0])
    resp = client.post("/api/v1/grains/sensory-range", json=body)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "feasible"
    assert data["name"] == KEYWORDS[0]
    assert data["min"] <= data["max"]

    # The HTTP answer is exactly what the solver computes directly.
    derived = views.CONTRACT.parse(body, require_descriptor=True)
    solver = views._build_fermentable_solver(derived)
    result = solver.sensory_range(
        KEYWORDS[0], color_context=views._color_context(derived))
    assert data["min"] == result.minimum
    assert data["max"] == result.maximum


def test_sensory_range_excludes_targets_own_bound(client):
    descriptor = KEYWORDS[0]
    # First learn the full editable span with no bounds at all.
    unbounded = client.post(
        "/api/v1/grains/sensory-range",
        json=_feasible_body(descriptor=descriptor),
    ).get_json()

    # Now pin that same descriptor to a narrow sliver and re-open its range.
    midpoint = (unbounded["min"] + unbounded["max"]) / 2
    pinned = _feasible_body(
        descriptor=descriptor,
        sensory=[{
            "name": descriptor,
            "minimum": midpoint,
            "maximum": midpoint,
        }],
    )
    reopened = client.post("/api/v1/grains/sensory-range", json=pinned).get_json()

    # The stale bound is dropped, so the reopened span is the full one again.
    assert reopened["min"] == unbounded["min"]
    assert reopened["max"] == unbounded["max"]


def test_sensory_range_respects_other_configured_bounds(client):
    """A bound on a *different* descriptor still constrains the target range."""
    if len(KEYWORDS) < 2:
        pytest.skip("need two descriptors")
    target, other = KEYWORDS[0], KEYWORDS[1]
    open_span = client.post(
        "/api/v1/grains/sensory-range",
        json=_feasible_body(descriptor=target),
    ).get_json()

    other_span = client.post(
        "/api/v1/grains/sensory-range",
        json=_feasible_body(descriptor=other),
    ).get_json()
    # Pin the other descriptor to its own minimum; the target range may shift
    # but must remain within the unconstrained span.
    constrained = _feasible_body(
        descriptor=target,
        sensory=[{"name": other, "minimum": other_span["min"],
                  "maximum": other_span["min"]}],
    )
    narrowed = client.post(
        "/api/v1/grains/sensory-range", json=constrained).get_json()
    assert narrowed["status"] == "feasible"
    assert narrowed["min"] >= open_span["min"] - 1e-6
    assert narrowed["max"] <= open_span["max"] + 1e-6


# -- focused range: invalid & malformed --------------------------------------

def test_sensory_range_unknown_descriptor_is_invalid(client):
    resp = client.post(
        "/api/v1/grains/sensory-range",
        json=_feasible_body(descriptor="not-a-real-descriptor"),
    )
    assert resp.status_code == 422
    assert resp.get_json()["outcome"] == "invalid"


def test_sensory_range_missing_descriptor_is_invalid(client):
    resp = client.post("/api/v1/grains/sensory-range", json=_feasible_body())
    assert resp.status_code == 422
    assert resp.get_json()["outcome"] == "invalid"


def test_sensory_range_unknown_slug_is_invalid(client):
    body = _feasible_body(descriptor=KEYWORDS[0])
    body["fermentables"]["allowed_slugs"][0] = "no-such-grain"
    resp = client.post("/api/v1/grains/sensory-range", json=body)
    assert resp.status_code == 422
    assert resp.get_json()["outcome"] == "invalid"


# -- full-brief feasibility --------------------------------------------------

def test_feasibility_reports_feasible(client):
    resp = client.post("/api/v1/grains/feasibility", json=_feasible_body())
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "feasible"


def test_feasibility_infeasible_on_impossible_color(client):
    # Only pale-ish grains, but demand a near-black beer: color rules it out,
    # proving the color band is part of the feasibility check.
    body = _feasible_body(
        color_srm={"minimum": 200, "maximum": 255},
    )
    resp = client.post("/api/v1/grains/feasibility", json=body)
    assert resp.status_code == 422
    assert resp.get_json()["outcome"] == "infeasible"


def test_feasibility_infeasible_on_contradictory_sensory(client):
    descriptor = KEYWORDS[0]
    span = client.post(
        "/api/v1/grains/sensory-range",
        json=_feasible_body(descriptor=descriptor),
    ).get_json()
    # Demand more of the descriptor than any bill can deliver.
    body = _feasible_body(
        sensory=[{"name": descriptor,
                  "minimum": span["max"] + 0.1,
                  "maximum": min(span["max"] + 1.0, 5)}],
    )
    resp = client.post("/api/v1/grains/feasibility", json=body)
    assert resp.status_code == 422
    assert resp.get_json()["outcome"] == "infeasible"


def test_feasibility_malformed_input_is_invalid(client):
    resp = client.post("/api/v1/grains/feasibility", json="not-a-brief")
    assert resp.status_code == 422
    assert resp.get_json()["outcome"] == "invalid"


# -- shared deadline ---------------------------------------------------------

def test_operations_report_deadline_when_budget_spent(client, monkeypatch):
    # Server config, never caller input: a zero budget means the shared
    # deadline is already spent before any solve runs.
    spent = SolverConfig(request_deadline_seconds=0.0,
                         solver_time_limit_seconds=0.0)
    monkeypatch.setattr(views, "SOLVER_CONFIG", spent)

    r1 = client.post("/api/v1/grains/feasibility", json=_feasible_body())
    assert r1.status_code == 503
    assert r1.get_json()["outcome"] == "deadline"

    r2 = client.post(
        "/api/v1/grains/sensory-range",
        json=_feasible_body(descriptor=KEYWORDS[0]),
    )
    assert r2.status_code == 503
    assert r2.get_json()["outcome"] == "deadline"


# -- the plural sweep path is gone -------------------------------------------

def test_all_descriptor_sweep_endpoint_removed(client):
    resp = client.post(
        "/api/v1/grains/sensory-profiles", json=_feasible_body())
    # No POST handler remains for the retired sweep (caught by the SPA
    # catch-all, which serves GET only), so the path can never run it.
    assert resp.status_code in (404, 405)


# -- transitional equivalence ------------------------------------------------

@pytest.mark.parametrize("style_slug", [s.slug for s in STYLES.style_list[:2]])
def test_focused_range_matches_full_sweep(style_slug):
    """Each focused range equals the old full-sweep value for the same
    descriptor, across representative committed styles."""
    style_object = STYLES.get_style_by_slug(style_slug)
    derived = views.CONTRACT.parse(_style_body(style_object))
    solver = views._build_fermentable_solver(derived)
    # This is a semantic-equivalence test, not the performance gate below.
    # Remove production timing from the assertion so a loaded CI runner cannot
    # turn an otherwise-correct solve into DEADLINE_EXCEEDED.
    solver.config = SolverConfig(
        solver_time_limit_seconds=float("inf"),
        request_deadline_seconds=float("inf"),
    )

    sweep = {r["name"]: (r["min"], r["max"]) for r in solver.sensory_ranges()}
    assert sweep, "style model should be feasible for the sweep"

    for name, (expected_min, expected_max) in sweep.items():
        focused = solver.sensory_range(name)
        assert focused.status.value == "feasible"
        assert focused.minimum == expected_min
        assert focused.maximum == expected_max


# -- real-style performance gate ---------------------------------------------

def test_focused_range_and_feasibility_under_one_second():
    style_object = STYLES.style_list[0]
    derived = views.CONTRACT.parse(_style_body(style_object))
    solver = views._build_fermentable_solver(derived)

    start = time.monotonic()
    solver.sensory_range(KEYWORDS[0])
    assert time.monotonic() - start < 1.0

    start = time.monotonic()
    solver.feasibility()
    assert time.monotonic() - start < 1.0
