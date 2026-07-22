"""Color model: known values, monotonicity, forward/inverse round trips, and
equivalence between the historical GrainBill post-calculation and the new pure
functions / linear color-bound inequalities over many fixed grain bills."""

import random

import pytest

from brewgen.backend.solver import color
from brewgen.backend.models.grain import Grain, GrainBill
from brewgen.backend.models.equipment import EquipmentProfile


def test_sg_to_ppg_known_values():
    assert color.sg_to_ppg(1.050) == pytest.approx(50)
    assert color.sg_to_ppg(1.000) == pytest.approx(0)


def test_morey_forward_known_value():
    assert color.morey_srm(10) == pytest.approx(1.4922 * 10 ** 0.6859)
    assert color.morey_srm(0) == 0.0
    assert color.morey_srm(-5) == 0.0


def test_morey_monotonic_increasing():
    previous = -1.0
    for mcu in range(0, 300):
        srm = color.morey_srm(mcu)
        assert srm >= previous
        previous = srm


def test_morey_forward_inverse_round_trip():
    for mcu in [0.5, 1, 3, 10, 25, 60, 120]:
        assert color.morey_mcu(color.morey_srm(mcu)) == pytest.approx(mcu, rel=1e-9)
    for srm in [0.5, 1, 3, 10, 25, 60]:
        assert color.morey_srm(color.morey_mcu(srm)) == pytest.approx(srm, rel=1e-9)


# -- equivalence oracle: the real GrainBill calculation --------------------

def _random_grains(n, rng, color_range=(1.0, 500.0)):
    grains = []
    for i in range(n):
        grains.append(Grain(
            name="g%d" % i, brand="b",
            potential=round(rng.uniform(1.020, 1.045), 4),
            color=round(rng.uniform(*color_range), 1),
            category="base", sensory_data={}))
    return grains


def _random_bill(n, rng):
    """A random integer percentage split summing to exactly 100."""
    cuts = sorted(rng.randint(0, 100) for _ in range(n - 1))
    points = [0] + cuts + [100]
    return [points[i + 1] - points[i] for i in range(n)]


def test_mcu_srm_match_grainbill_over_many_bills():
    rng = random.Random(1234)
    equip = EquipmentProfile(mash_efficiency=72, target_volume_gallons=5.5)
    for _ in range(200):
        n = rng.randint(2, 6)
        grains = _random_grains(n, rng)
        bill = _random_bill(n, rng)
        original_sg = round(rng.uniform(1.030, 1.090), 3)

        old_srm = GrainBill(grains, bill).get_beer_srm(original_sg, equip)
        new_mcu = color.mash_color_units(
            [g.color for g in grains], [g.ppg for g in grains], bill,
            original_sg, equip.target_volume_gallons, equip.mash_efficiency)

        assert color.morey_srm(new_mcu) == pytest.approx(old_srm, rel=1e-9)


def test_grain_pounds_match_grainbill():
    rng = random.Random(99)
    equip = EquipmentProfile(mash_efficiency=68, target_volume_gallons=6.0)
    for _ in range(50):
        n = rng.randint(2, 5)
        grains = _random_grains(n, rng)
        bill = _random_bill(n, rng)
        original_sg = round(rng.uniform(1.030, 1.080), 3)

        recipe = GrainBill(grains, bill).get_recipe(original_sg, equip)
        new_pounds = color.grain_pounds(
            [g.ppg for g in grains], bill, original_sg,
            equip.target_volume_gallons, equip.mash_efficiency)
        pounds_by_slug = {grains[i].slug: new_pounds[i] for i in range(n)}

        for entry in recipe["grains"]:
            assert entry["use_pounds"] == pytest.approx(
                pounds_by_slug[entry["slug"]], rel=1e-9)


def test_color_bound_inequalities_match_post_calculation():
    """The two linear inequalities accept exactly the bills the old rounded
    post-filter's underlying SRM would accept against the same exact bounds."""
    rng = random.Random(7)
    equip = EquipmentProfile(mash_efficiency=75, target_volume_gallons=5.5)
    min_srm, max_srm = 6.0, 14.0
    checked_accept = checked_reject = 0
    for _ in range(400):
        n = rng.randint(2, 6)
        # Lighter grains so bills land across the 6-14 SRM band, exercising both
        # accepted and rejected outcomes rather than trivially all-dark.
        grains = _random_grains(n, rng, color_range=(1.0, 25.0))
        bill = _random_bill(n, rng)
        original_sg = round(rng.uniform(1.040, 1.070), 3)
        colors = [g.color for g in grains]
        ppgs = [g.ppg for g in grains]

        old_srm = GrainBill(grains, bill).get_beer_srm(original_sg, equip)
        # Skip bills sitting essentially on a bound to avoid float ties.
        if abs(old_srm - min_srm) < 1e-6 or abs(old_srm - max_srm) < 1e-6:
            continue

        lower, upper = color.color_bound_coefficients(
            colors, ppgs, original_sg, equip.target_volume_gallons,
            equip.mash_efficiency, min_srm, max_srm)
        accept_linear = (
            sum(lower[i] * bill[i] for i in range(n)) >= 0
            and sum(upper[i] * bill[i] for i in range(n)) >= 0)
        accept_direct = min_srm <= old_srm <= max_srm

        assert accept_linear == accept_direct
        if accept_direct:
            checked_accept += 1
        else:
            checked_reject += 1

    # The sweep must exercise both sides, not just trivially reject everything.
    assert checked_accept > 0 and checked_reject > 0
