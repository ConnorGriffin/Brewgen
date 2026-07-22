"""Thin HTTP coverage: the three fermentable routes go through the new solver
interface and expose bounded failure states. Valid, infeasible, and
deadline-exceeded requests are all exercised."""

import pytest

from brewgen.backend import views
from brewgen.backend.solver.fermentables import SolverConfig


@pytest.fixture
def client():
    return views.app.test_client()


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
    # No blend of these pale grains can reach a very dark SRM.
    resp = client.post("/api/v1/grains/recipes", json=_body(min_srm=100, max_srm=200))
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "infeasible"
    assert payload["alternatives"] == []


def test_recipes_endpoint_reports_deadline_exceeded(client, monkeypatch):
    # Deadlines are server configuration; a zero request deadline yields the
    # bounded deadline-exceeded state rather than an unbounded search.
    monkeypatch.setattr(views, "SOLVER_CONFIG",
                        SolverConfig(request_deadline_seconds=0))
    resp = client.post("/api/v1/grains/recipes", json=_body())
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "deadline_exceeded"
    assert payload["alternatives"] == []
