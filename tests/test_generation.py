"""Bounded, diverse, deterministic generation: exact in-model SRM bounds, whole
percentages, pairwise distance, cardinality, and explicit completion states.

Every returned bill is independently recomputed here (total, bounds, cardinality,
MCU/SRM, pairwise L1) rather than trusting the solver's own bookkeeping."""

import pytest

from conftest import make_grain, make_category
from brewgen.backend.solver import color
from brewgen.backend.solver.fermentables import (
    FermentableSolver, SolverConfig, GenerationStatus)

STYLE_CATS = [
    make_category("base", 60, 100, unique_fermentable_count=2),
    make_category("crystal", 0, 25, unique_fermentable_count=2),
    make_category("roasted", 0, 15, unique_fermentable_count=1),
    make_category("munich", 0, 40, unique_fermentable_count=1),
]
SG, VOL, EFF = 1.055, 5.5, 75


def _lut(grains):
    return {g["slug"]: g for g in grains}


def _srm_of(percents, lut):
    slugs = list(percents)
    return color.morey_srm(color.mash_color_units(
        [lut[s]["color"] for s in slugs], [lut[s]["ppg"] for s in slugs],
        [percents[s] for s in slugs], SG, VOL, EFF))


def _l1(a, b):
    keys = set(a) | set(b)
    return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in keys)


def _style_grains(real_grains):
    wanted = {"base", "crystal", "roasted", "munich"}
    return [g for g in real_grains if g["category"] in wanted]


def test_generation_returns_valid_diverse_bounded_bills(real_grains):
    grains = _style_grains(real_grains)
    min_srm, max_srm = 6.0, 14.0
    result = FermentableSolver(grains, STYLE_CATS, max_unique_grains=4).generate(
        SG, VOL, EFF, min_srm, max_srm)

    assert result.status == GenerationStatus.COMPLETE
    assert len(result.alternatives) == 5

    lut = _lut(grains)
    cat_of = {g["slug"]: g["category"] for g in grains}
    caps = {c["name"]: c for c in STYLE_CATS}

    for bill in result.alternatives:
        pct = bill.percents
        # Whole percentages, each present grain 1..100, summing to exactly 100.
        assert all(isinstance(v, int) and 1 <= v <= 100 for v in pct.values())
        assert sum(pct.values()) == 100
        # Global cardinality.
        assert len(pct) <= 4
        # Per-category usage + cardinality.
        by_cat = {}
        for slug, v in pct.items():
            by_cat.setdefault(cat_of[slug], []).append(v)
        for name, members in by_cat.items():
            assert len(members) <= caps[name]["unique_fermentable_count"]
            assert sum(members) <= caps[name]["max_percent"]
            assert sum(members) >= caps[name]["min_percent"]
        # Exact SRM acceptance, independently recomputed and matching the model.
        srm = _srm_of(pct, lut)
        assert min_srm - 1e-9 <= srm <= max_srm + 1e-9
        assert srm == pytest.approx(bill.srm, rel=1e-9)

    # Every pair is at least 10 summed absolute percentage points apart.
    bills = [b.percents for b in result.alternatives]
    for i in range(len(bills)):
        for j in range(i + 1, len(bills)):
            assert _l1(bills[i], bills[j]) >= 10


def test_generation_is_deterministic_regardless_of_input_order(real_grains):
    grains = _style_grains(real_grains)
    args = (SG, VOL, EFF, 6.0, 14.0)
    r1 = FermentableSolver(grains, STYLE_CATS, max_unique_grains=4).generate(*args)
    r2 = FermentableSolver(list(reversed(grains)), STYLE_CATS,
                           max_unique_grains=4).generate(*args)
    assert [b.percents for b in r1.alternatives] == [b.percents for b in r2.alternatives]
    assert r1.status == r2.status


def test_generation_infeasible_when_srm_unreachable():
    # A single very pale base grain cannot produce a dark beer.
    grains = [make_grain("pale", "base", color=1.5, ppg=37.0)]
    cats = [make_category("base", 0, 100)]
    result = FermentableSolver(grains, cats, max_unique_grains=1).generate(
        original_sg=1.05, target_volume_gallons=5.5, mash_efficiency=75,
        min_srm=40.0, max_srm=60.0)
    assert result.status == GenerationStatus.INFEASIBLE
    assert result.alternatives == []


def test_generation_never_returns_a_bill_outside_srm_bounds():
    # Two grains straddling the range; only certain blends land inside it, and
    # the model -- not a post-filter -- must reject the rest.
    grains = [
        make_grain("pale", "base", color=2.0, ppg=37.0, max_percent=100),
        make_grain("dark", "roasted", color=400.0, ppg=30.0, max_percent=100),
    ]
    cats = [make_category("base", 0, 100), make_category("roasted", 0, 100)]
    min_srm, max_srm = 10.0, 20.0
    result = FermentableSolver(grains, cats, max_unique_grains=2).generate(
        1.05, 5.5, 75, min_srm, max_srm)
    lut = _lut(grains)
    assert result.alternatives  # some blend fits
    for bill in result.alternatives:
        srm = _srm_of(bill.percents, lut)
        assert min_srm - 1e-9 <= srm <= max_srm + 1e-9


def test_generation_respects_min_percent_only_when_selected():
    grains = [
        make_grain("base1", "base", color=2.0, ppg=37.0, max_percent=100),
        make_grain("base2", "base", color=3.0, ppg=36.0, max_percent=100),
        make_grain("special", "specialty", color=8.0, ppg=34.0,
                   min_percent=20, max_percent=40),
    ]
    cats = [make_category("base", 60, 100), make_category("specialty", 0, 40)]
    result = FermentableSolver(grains, cats, max_unique_grains=3).generate(
        1.05, 5.5, 75, 0.0, 100.0)
    assert result.alternatives
    for bill in result.alternatives:
        used = bill.percents.get("special", 0)
        # The floor applies only when the grain is actually selected.
        assert used == 0 or used >= 20


def test_generation_complete_when_diverse_space_exhausts_below_five():
    # Only one feasible bill exists, so generation returns it and completes.
    grains = [make_grain("only", "base", color=2.0, ppg=37.0)]
    cats = [make_category("base", 100, 100)]
    result = FermentableSolver(grains, cats, max_unique_grains=1).generate(
        1.05, 5.5, 75, 0.0, 100.0)
    assert result.status == GenerationStatus.COMPLETE
    assert len(result.alternatives) == 1
    assert result.alternatives[0].percents == {"only": 100}


def test_generation_deadline_exceeded_before_any_bill():
    grains = [make_grain("base1", "base", color=2.0),
              make_grain("base2", "base", color=3.0)]
    cats = [make_category("base", 0, 100)]
    config = SolverConfig(request_deadline_seconds=0)
    result = FermentableSolver(grains, cats, max_unique_grains=2,
                               config=config).generate(
        1.05, 5.5, 75, 0.0, 100.0, clock=lambda: 0.0)
    assert result.status == GenerationStatus.DEADLINE_EXCEEDED
    assert result.alternatives == []


def test_generation_partial_when_deadline_hits_after_first_bill():
    grains = [make_grain("base1", "base", color=2.0, ppg=37.0),
              make_grain("base2", "base", color=3.0, ppg=36.0)]
    cats = [make_category("base", 0, 100)]
    config = SolverConfig(request_deadline_seconds=50)
    # start, first-iteration check (proceed), second-iteration check (expired).
    times = iter([0.0, 0.0, 1000.0])
    result = FermentableSolver(grains, cats, max_unique_grains=2,
                               config=config).generate(
        1.05, 5.5, 75, 0.0, 100.0, clock=lambda: next(times))
    assert result.status == GenerationStatus.PARTIAL
    assert len(result.alternatives) == 1
