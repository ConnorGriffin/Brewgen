"""Pure, Flask-independent beer color math for the fermentables solver.

Every function here is a plain calculation over grain data and percentages so it
can be unit tested in isolation and reused both to score a finished grain bill
and to build the linear color constraints the MILP solves against.

The math mirrors the historical ``GrainBill`` calculation exactly so the two
agree bill-for-bill:

    sg points needed = (original_sg - 1) * 1000 * target_volume_gallons
    average ppg       = sum(ppg_i * percent_i / 100)
    grain pounds_i    = sg_points_needed / (average_ppg * mash_efficiency) * percent_i
    mash color units  = sum(color_i * pounds_i) / target_volume_gallons
    srm (Morey)       = 1.4922 * mcu ** 0.6859

``percent_i`` is a whole percentage point (0-100) and ``mash_efficiency`` is the
whole-number efficiency (e.g. ``75``) used by the existing equipment profile.
"""

# Morey equation constants: srm = MOREY_COEFFICIENT * mcu ** MOREY_EXPONENT
MOREY_COEFFICIENT = 1.4922
MOREY_EXPONENT = 0.6859


def sg_to_ppg(original_sg):
    """Convert a specific gravity (1.xxx) to gravity points per gallon."""
    return (original_sg - 1) * 1000


def sg_points_needed(original_sg, target_volume_gallons):
    """Total gravity points the grain bill must supply for the batch."""
    return sg_to_ppg(original_sg) * target_volume_gallons


def average_ppg(ppgs, percents):
    """Usage-weighted average ppg of a grain bill.

    Args:
        ppgs (list): Per-grain ppg values.
        percents (list): Per-grain usage as whole percentage points (0-100).
    """
    return sum(ppg * (percent / 100) for ppg, percent in zip(ppgs, percents))


def grain_pounds(ppgs, percents, original_sg, target_volume_gallons, mash_efficiency):
    """Pounds of each grain needed to hit the target gravity.

    Reproduces the original ``GrainBill.__get_grain_pounds`` calculation.
    """
    points_needed = sg_points_needed(original_sg, target_volume_gallons)
    avg_ppg = average_ppg(ppgs, percents)
    return [
        points_needed / (avg_ppg * mash_efficiency) * percent
        for percent in percents
    ]


def mash_color_units(colors, ppgs, percents, original_sg, target_volume_gallons,
                     mash_efficiency):
    """Mash color units (MCU) for a fixed grain bill.

    Equivalent to summing ``color_i * pounds_i / target_volume_gallons`` but
    reduced to the batch-independent linear-fractional form ``K * C / P`` where
    ``C`` and ``P`` are the color- and ppg-weighted percentage sums. This is the
    exact expression the generation constraints are derived from.
    """
    numerator = sum(color * percent for color, percent in zip(colors, percents))
    denominator = sum(ppg * percent for ppg, percent in zip(ppgs, percents))
    return _color_constant(original_sg, mash_efficiency) * numerator / denominator


def morey_srm(mcu):
    """Forward Morey equation: SRM color from mash color units."""
    if mcu <= 0:
        return 0.0
    return MOREY_COEFFICIENT * mcu ** MOREY_EXPONENT


def morey_mcu(srm):
    """Inverse Morey equation: mash color units that yield the given SRM."""
    if srm <= 0:
        return 0.0
    return (srm / MOREY_COEFFICIENT) ** (1 / MOREY_EXPONENT)


def color_bound_coefficients(colors, ppgs, original_sg, target_volume_gallons,
                             mash_efficiency, min_srm, max_srm):
    """Linear coefficients enforcing an SRM range on the integer percentages.

    Morey is inverted at the requested SRM bounds to get MCU bounds, then the
    positive linear-fractional MCU expression ``K * C / P`` is cross-multiplied
    (``P`` is strictly positive) into two linear inequalities over the per-grain
    percentages ``x_i``::

        sum(lower_i * x_i) >= 0   <=>   mcu >= mcu_min   (min color)
        sum(upper_i * x_i) >= 0   <=>   mcu <= mcu_max   (max color)

    Args:
        colors, ppgs (list): Per-grain color (Lovibond) and ppg values.
        original_sg (float): Target starting gravity (1.xxx).
        target_volume_gallons (float): Present for signature symmetry; MCU is
            volume-independent so it does not affect the coefficients.
        mash_efficiency (float): Whole-number mash efficiency (e.g. 75).
        min_srm, max_srm (float): Requested SRM range.

    Returns:
        (lower_coeffs, upper_coeffs): two coefficient lists, one per grain.
    """
    k = _color_constant(original_sg, mash_efficiency)
    mcu_min = morey_mcu(min_srm)
    mcu_max = morey_mcu(max_srm)
    lower_coeffs = [k * color - mcu_min * ppg for color, ppg in zip(colors, ppgs)]
    upper_coeffs = [mcu_max * ppg - k * color for color, ppg in zip(colors, ppgs)]
    return lower_coeffs, upper_coeffs


def _color_constant(original_sg, mash_efficiency):
    """The ``K`` in ``mcu = K * C / P``; positive for any real batch."""
    return sg_to_ppg(original_sg) * 100 / mash_efficiency
