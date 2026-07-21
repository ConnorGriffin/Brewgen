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


def test_sensory_profiles_endpoint_returns_ranges(client):
    resp = client.post("/api/v1/grains/sensory-profiles", json=_body())
    assert resp.status_code == 200
    profiles = resp.get_json()
    assert isinstance(profiles, list) and profiles
    for entry in profiles:
        assert set(entry) == {"name", "min", "max"}
        assert entry["min"] <= entry["max"]


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
