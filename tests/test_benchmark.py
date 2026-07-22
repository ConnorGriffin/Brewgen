"""Public-compute regression gate.

A representative committed-style model (built from the shipped grain database,
not the missing raw recipe corpus) must return its five alternatives well
within an agreed solver budget on CI-class hardware. This guards against a
future change quietly reintroducing an unbounded or exponential search."""

import time

import pytest

from conftest import make_category
from brewgen.backend.solver import color
from brewgen.backend.solver.fermentables import FermentableSolver, GenerationStatus

# Generous enough to be stable on shared CI runners, tight enough to catch a
# regression back toward enumerate-all behavior.
BUDGET_SECONDS = 10.0

STYLE_CATS = [
    make_category("base", 55, 100, unique_fermentable_count=2),
    make_category("crystal", 0, 25, unique_fermentable_count=2),
    make_category("roasted", 0, 12, unique_fermentable_count=1),
    make_category("munich", 0, 40, unique_fermentable_count=1),
    make_category("wheat", 0, 40, unique_fermentable_count=1),
]


def test_five_result_request_stays_within_budget(real_grains):
    grains = [g for g in real_grains
              if g["category"] in {c["name"] for c in STYLE_CATS}]
    solver = FermentableSolver(grains, STYLE_CATS, max_unique_grains=4)

    start = time.perf_counter()
    result = solver.generate(original_sg=1.052, target_volume_gallons=5.5,
                             mash_efficiency=75, min_srm=4.0, max_srm=18.0)
    elapsed = time.perf_counter() - start

    assert elapsed < BUDGET_SECONDS, "generation took %.2fs" % elapsed
    assert result.status == GenerationStatus.COMPLETE
    assert len(result.alternatives) == 5

    # Independently confirm every returned bill lands inside the SRM band.
    lut = {g["slug"]: g for g in grains}
    for bill in result.alternatives:
        slugs = list(bill.percents)
        srm = color.morey_srm(color.mash_color_units(
            [lut[s]["color"] for s in slugs], [lut[s]["ppg"] for s in slugs],
            [bill.percents[s] for s in slugs], 1.052, 5.5, 75))
        assert 4.0 - 1e-9 <= srm <= 18.0 + 1e-9
