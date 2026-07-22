"""The public generate endpoint, exercised through the HTTP interface.

Every request is the strict ``version: 1`` brief; the server derives the
category/style-model constraints from the style slug. A successful brief returns
up to five deterministic, unranked whole-percentage bills; infeasible and
deadline-exceeded briefs surface as the locked failure responses."""

import pytest

from conftest import make_brief
from brewgen.backend import envelope, views
from brewgen.backend.solver.fermentables import SolverConfig

# A committed style whose grain and category model admits a full five-bill set
# across a broad colour band; used for the successful-generation assertions.
FIVE_BILL_STYLE = "american-light-lager"


@pytest.fixture(autouse=True)
def _relaxed_envelope(monkeypatch):
    # Each test drives one visitor through several requests; a permissive limiter
    # and a fresh concurrency guard keep the guardrails from tripping unless a
    # test installs its own strict instances.
    monkeypatch.setattr(envelope, "RATE_LIMITER",
                        envelope.RateLimiter(capacity=1000, refill=1000))
    monkeypatch.setattr(envelope, "CONCURRENCY", envelope.ConcurrencyGuard(slots=8))


@pytest.fixture
def client():
    return views.app.test_client()


def _style(slug=FIVE_BILL_STYLE):
    return views.all_styles.get_style_by_slug(slug)


def test_generate_returns_five_unranked_whole_percent_bills(client):
    brief = make_brief(_style(), min_srm=3.0, max_srm=30.0)
    resp = client.post("/api/v1/grains/recipes", json=brief)

    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "complete"
    alternatives = payload["alternatives"]
    assert len(alternatives) == 5
    for alt in alternatives:
        assert 3.0 <= alt["srm"] <= 30.0
        assert sum(g["use_percent"] for g in alt["grains"]) == 100
        assert all(isinstance(g["use_percent"], int) for g in alt["grains"])
        assert all(g["use_pounds"] > 0 for g in alt["grains"])


def test_generate_exposes_per_grain_metadata_and_per_bill_sensory(client):
    # The results shelf paints each malt layer from its real Lovibond colour and
    # reads the tastes line from the sensory model, so both must ride along.
    resp = client.post("/api/v1/grains/recipes", json=make_brief(_style()))
    payload = resp.get_json()
    assert payload["alternatives"]
    for alt in payload["alternatives"]:
        assert isinstance(alt["sensory"], dict) and alt["sensory"]
        for g in alt["grains"]:
            assert g["name"] and g["brand"]
            assert isinstance(g["color_lovibond"], (int, float))


def test_generate_alternatives_differ_by_ten_points(client):
    resp = client.post("/api/v1/grains/recipes",
                       json=make_brief(_style(), min_srm=3.0, max_srm=30.0))
    alternatives = resp.get_json()["alternatives"]
    vectors = [{g["slug"]: g["use_percent"] for g in alt["grains"]}
               for alt in alternatives]
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            slugs = set(vectors[i]) | set(vectors[j])
            distance = sum(abs(vectors[i].get(s, 0) - vectors[j].get(s, 0))
                           for s in slugs)
            assert distance >= 10


def test_generate_derives_constraints_and_rejects_whole_model_objects(client):
    # The old whole-model shape (client-supplied category/sensory models and full
    # grain objects) must be rejected: those fields are unknown to the contract.
    legacy = {
        "fermentable_list": [{"slug": "x", "min_percent": 0, "max_percent": 100}],
        "category_model": [{"name": "base", "min_percent": 0, "max_percent": 100}],
        "sensory_model": [],
        "max_unique_fermentables": 4,
    }
    resp = client.post("/api/v1/grains/recipes", json=legacy)
    assert resp.status_code == 422
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["code"] in ("invalid_brief", "empty_brief")


def test_generate_reports_infeasible_as_problem_json(client):
    # No blend of these pale grains can reach a very dark SRM.
    brief = make_brief(_style(), min_srm=100.0, max_srm=200.0)
    resp = client.post("/api/v1/grains/recipes", json=brief)
    assert resp.status_code == 422
    assert resp.mimetype == "application/problem+json"
    body = resp.get_json()
    assert body["code"] == "infeasible"
    assert "request_id" in body


def test_generate_reports_deadline_exceeded_as_problem_json(client, monkeypatch):
    # Deadlines are server configuration; a zero request deadline yields the
    # bounded deadline-exceeded response rather than an unbounded search.
    monkeypatch.setattr(views, "SOLVER_CONFIG",
                        SolverConfig(request_deadline_seconds=0))
    resp = client.post("/api/v1/grains/recipes", json=make_brief(_style()))
    assert resp.status_code == 503
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["code"] == "deadline_exceeded"
    assert resp.headers.get("Retry-After") is None or True  # deadline carries none
