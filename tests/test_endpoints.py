"""Thin HTTP coverage: the three fermentable routes go through the new solver
interface and expose bounded failure states. Valid, infeasible, and
deadline-exceeded requests are all exercised."""

import pytest

from brewgen.backend import views
from brewgen.backend.solver.fermentables import SolverConfig


@pytest.fixture
def client():
    return views.app.test_client()


def test_healthz_returns_ok_without_solver(client, monkeypatch):
    # Before this route existed, /healthz fell through to the catch-all which
    # attempted render_template("index.html") — a TemplateNotFound 500 in the
    # test environment. The dedicated route must return 200 JSON and must not
    # touch the solver (patching generate proves it is never called).
    called = []
    from brewgen.backend.solver import fermentables as _fe
    original_generate = _fe.FermentableSolver.generate
    monkeypatch.setattr(_fe.FermentableSolver, "generate",
                        lambda *a, **kw: called.append(1) or original_generate(*a, **kw))

    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}
    assert called == [], "/healthz must not invoke the solver"


def _body(min_srm=3, max_srm=20):
    grains = views.all_grains.get_grain_list()
    by_cat = {}
    for g in grains:
        by_cat.setdefault(g["category"], []).append(g["slug"])
    fermentables = [
        {"slug": s, "min_percent": 0, "max_percent": 100} for s in by_cat["base"][:2]
    ] + [
        {"slug": s, "min_percent": 0, "max_percent": 25} for s in by_cat["crystal"][:2]
    ]
    return {
        "fermentable_list": fermentables,
        "category_model": [
            {"name": "base", "min_percent": 60, "max_percent": 100,
             "unique_fermentable_count": 2},
            {"name": "crystal", "min_percent": 0, "max_percent": 25,
             "unique_fermentable_count": 2},
        ],
        "max_unique_fermentables": 4,
        "equipment_profile": {"target_volume_gallons": 5.5, "mash_efficiency": 75},
        "beer_profile": {"min_color_srm": min_srm, "max_color_srm": max_srm,
                         "original_sg": 1.055},
    }


def test_validity_endpoint_returns_boolean(client):
    resp = client.post("/api/v1/helpers/grain-model-valid", json=_body())
    assert resp.status_code == 200
    assert resp.get_json() is True


def test_recipes_endpoint_returns_unranked_alternatives(client):
    resp = client.post("/api/v1/grains/recipes", json=_body())
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "complete"
    alternatives = payload["alternatives"]
    assert 1 <= len(alternatives) <= 5
    for alt in alternatives:
        assert 3 <= alt["srm"] <= 20
        assert sum(g["use_percent"] for g in alt["grains"]) == 100
        assert all(g["use_pounds"] > 0 for g in alt["grains"])


def test_recipes_endpoint_exposes_per_grain_metadata_and_per_bill_sensory(client):
    # The results shelf paints each malt layer from its real Lovibond colour and
    # reads the tastes line from the sensory model, so both must ride along with
    # every bill rather than be fabricated in the browser.
    resp = client.post("/api/v1/grains/recipes", json=_body())
    payload = resp.get_json()
    assert payload["alternatives"]
    for alt in payload["alternatives"]:
        assert isinstance(alt["sensory"], dict) and alt["sensory"]
        assert all(isinstance(v, (int, float)) for v in alt["sensory"].values())
        for g in alt["grains"]:
            assert g["name"] and g["brand"]
            assert isinstance(g["color_lovibond"], (int, float))


def test_recipes_endpoint_alternatives_differ_by_ten_points(client):
    # Every displayed pair of bills must differ by at least ten summed
    # percentage points — the diversity floor the shelf promises. Guarded here at
    # the public interface so a serializer change can never quietly collapse it.
    resp = client.post("/api/v1/grains/recipes", json=_body())
    alternatives = resp.get_json()["alternatives"]
    vectors = [{g["slug"]: g["use_percent"] for g in alt["grains"]}
               for alt in alternatives]
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            slugs = set(vectors[i]) | set(vectors[j])
            distance = sum(abs(vectors[i].get(s, 0) - vectors[j].get(s, 0))
                           for s in slugs)
            assert distance >= 10


def test_recipes_endpoint_reports_infeasible(client):
    # No blend of these pale grains can reach a very dark SRM. Under the public
    # compute envelope an infeasible brief is the locked 422 problem+json
    # outcome, carrying no bills and no solver internals.
    resp = client.post("/api/v1/grains/recipes", json=_body(min_srm=100, max_srm=200))
    assert resp.status_code == 422
    assert resp.mimetype == "application/problem+json"
    payload = resp.get_json()
    assert payload["outcome"] == "infeasible"
    assert "alternatives" not in payload


def test_recipes_endpoint_reports_deadline_exceeded(client, monkeypatch):
    # Deadlines are server configuration; a zero request deadline yields the
    # bounded deadline outcome, surfaced by the envelope as 503 problem+json
    # rather than an unbounded search.
    monkeypatch.setattr(views, "SOLVER_CONFIG",
                        SolverConfig(request_deadline_seconds=0))
    resp = client.post("/api/v1/grains/recipes", json=_body())
    assert resp.status_code == 503
    assert resp.mimetype == "application/problem+json"
    assert resp.get_json()["outcome"] == "deadline"
