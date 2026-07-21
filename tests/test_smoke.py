"""Baseline: the package imports cleanly and test discovery pulls in no
print-driven experiments (which run solver work at import time)."""

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(REPO_ROOT, "brewgen", "backend", "models")


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
