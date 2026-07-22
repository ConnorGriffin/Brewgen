"""Baseline: the package imports cleanly and test discovery pulls in no
print-driven experiments (which run solver work at import time)."""

import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(REPO_ROOT, "brewgen", "backend", "models")
RECIPE_ANALYZER = os.path.join(REPO_ROOT, "recipe_analyzer")


def test_solver_package_imports():
    from brewgen.backend.solver import color, fermentables
    assert hasattr(color, "morey_srm")
    assert hasattr(fermentables, "FermentableSolver")


def test_models_import_without_ortools():
    # grain.py no longer depends on OR-Tools; importing it must not need it.
    import sys
    assert "ortools" not in sys.modules
    from brewgen.backend.models import grain
    assert hasattr(grain, "GrainBill")
    assert "ortools" not in sys.modules


def test_no_collectible_experiments_remain():
    # pytest collects test_*.py and *_test.py; the renamed experiments must not
    # match either pattern anywhere under the source tree.
    offenders = []
    for root, _dirs, files in os.walk(os.path.join(REPO_ROOT, "brewgen")):
        for name in files:
            if name.endswith("_test.py") or name.startswith("test_"):
                offenders.append(os.path.join(root, name))
    assert offenders == []
    # The experiment kept for reference is renamed so it can never be collected.
    assert os.path.exists(os.path.join(MODELS_DIR, "hop_experiment.py"))


def test_live_scrapers_are_absent():
    # The live crawlers were retired in issue #32 and must not be invokable.
    assert not os.path.exists(
        os.path.join(RECIPE_ANALYZER, "beersmith_scrape", "scrape.py")
    )
    assert not os.path.exists(
        os.path.join(RECIPE_ANALYZER, "brewersfriend_scrape", "scrape.py")
    )


def test_style_models_load():
    # The legacy style models must still be readable after scraper removal.
    style_data_dir = os.path.join(RECIPE_ANALYZER, "style_data")
    json_files = [f for f in os.listdir(style_data_dir) if f.endswith(".json")]
    assert len(json_files) > 0, "No style model files found"
    for fname in json_files:
        path = os.path.join(style_data_dir, fname)
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data, (dict, list)), f"{fname} did not parse as valid JSON"
        assert data, f"{fname} is empty"


def test_provenance_disclosure_exists():
    # The repository must carry provenance documentation for the legacy models.
    provenance = os.path.join(RECIPE_ANALYZER, "PROVENANCE.md")
    assert os.path.exists(provenance), "recipe_analyzer/PROVENANCE.md is missing"
    with open(provenance, encoding="utf-8") as fh:
        text = fh.read()
    assert "BeerSmith" in text
    assert "Brewers Friend" in text
    assert "not" in text.lower()
