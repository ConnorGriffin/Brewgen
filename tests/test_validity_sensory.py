"""Model validity and sensory-range operations: cardinality-preserving MILPs
with no fixed-point scaling and no invented color constraints."""

import pytest

from conftest import make_grain, make_category
from brewgen.backend.solver.fermentables import FermentableSolver


# -- validity ---------------------------------------------------------------

def test_valid_model_is_valid():
    grains = [make_grain("base1", "base"), make_grain("crys1", "crystal", max_percent=25)]
    cats = [make_category("base", 60, 100), make_category("crystal", 0, 25)]
    assert FermentableSolver(grains, cats, max_unique_grains=2).is_valid() is True


def test_category_minimum_unsatisfiable_is_invalid():
    # Only base grains available, but the base category is capped below 100, so
    # the percentages can never sum to 100.
    grains = [make_grain("base1", "base")]
    cats = [make_category("base", 0, 40)]
    assert FermentableSolver(grains, cats, max_unique_grains=1).is_valid() is False


def test_per_category_cardinality_cap_is_enforced():
    """Regression: the old CP-SAT ``... and grain_used[k]`` made the per-category
    count dead, so a cap of 1 was silently ignored. The crystal category needs
    15-25% but each crystal maxes at 10%, so it is only satisfiable by using two
    crystals -- which a cap of 1 must forbid (infeasible) and a cap of 2 allow."""
    grains = [
        make_grain("base1", "base", max_percent=100),
        make_grain("crys1", "crystal", max_percent=10),
        make_grain("crys2", "crystal", max_percent=10),
    ]
    base = make_category("base", 60, 100)

    capped = [base, make_category("crystal", 15, 25, unique_fermentable_count=1)]
    assert FermentableSolver(grains, capped, max_unique_grains=4).is_valid() is False

    relaxed = [base, make_category("crystal", 15, 25, unique_fermentable_count=2)]
    assert FermentableSolver(grains, relaxed, max_unique_grains=4).is_valid() is True


def test_global_cardinality_cap_can_make_model_infeasible():
    # Three grains, each maxing at 40%, so at least three are needed to reach
    # 100%; a global cap of two is therefore infeasible.
    grains = [make_grain("g%d" % i, "base", max_percent=40) for i in range(3)]
    cats = [make_category("base", 0, 100)]
    assert FermentableSolver(grains, cats, max_unique_grains=2).is_valid() is False
    assert FermentableSolver(grains, cats, max_unique_grains=3).is_valid() is True


# -- sensory ranges ---------------------------------------------------------

def test_sensory_ranges_pinned_single_grain():
    grains = [make_grain("a", "base", sensory={"sweet": 3.0, "malty": 2.0})]
    cats = [make_category("base", 100, 100)]  # base forced to exactly 100%
    solver = FermentableSolver(grains, cats, max_unique_grains=1,
                               sensory_keywords=["sweet", "malty", "roasted"])
    ranges = {d["name"]: d for d in solver.sensory_ranges()}
    assert ranges["sweet"] == {"name": "sweet", "min": 3.0, "max": 3.0}
    assert ranges["malty"] == {"name": "malty", "min": 2.0, "max": 2.0}
    # A descriptor no grain carries is a flat zero range, not an error.
    assert ranges["roasted"] == {"name": "roasted", "min": 0.0, "max": 0.0}


def test_sensory_ranges_span_extremes():
    grains = [
        make_grain("sweet_malt", "base", sensory={"sweet": 4.0}),
        make_grain("plain_malt", "base", sensory={"sweet": 0.0}),
    ]
    cats = [make_category("base", 100, 100)]
    solver = FermentableSolver(grains, cats, max_unique_grains=2,
                               sensory_keywords=["sweet"])
    ranges = {d["name"]: d for d in solver.sensory_ranges()}
    # All plain -> 0; all sweet -> 4; the weighted average spans that whole band.
    assert ranges["sweet"]["min"] == 0.0
    assert ranges["sweet"]["max"] == 4.0


def test_sensory_ranges_respects_cardinality():
    # A cap that forbids the sweet grain drags the achievable maximum down.
    grains = [
        make_grain("sweet_malt", "base", sensory={"sweet": 4.0}, max_percent=100),
        make_grain("plain_malt", "base", sensory={"sweet": 0.0}, max_percent=100),
    ]
    cats = [make_category("base", 100, 100, unique_fermentable_count=1)]
    solver = FermentableSolver(grains, cats, max_unique_grains=1,
                               sensory_keywords=["sweet"])
    ranges = {d["name"]: d for d in solver.sensory_ranges()}
    # With only one grain permitted the bill is either all-sweet or all-plain;
    # the average is never a blend, so max stays a clean 4.0 (not e.g. 2.0).
    assert ranges["sweet"]["max"] == 4.0
    assert ranges["sweet"]["min"] == 0.0


def test_sensory_ranges_infeasible_model_returns_empty():
    grains = [make_grain("a", "base")]
    cats = [make_category("base", 0, 40)]  # cannot reach 100%
    solver = FermentableSolver(grains, cats, max_unique_grains=1,
                               sensory_keywords=["sweet"])
    assert solver.sensory_ranges() == []
