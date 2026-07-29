"""The committed, generation-proved default brief every style opens on.

The brief editor no longer invents its opening brief from a style's midpoints
and corpus means -- nothing checked that those individually typical numbers
intersected, and for a third of the catalog they did not. Instead every style
carries a frozen default that generation has already proved returns at least one
grain bill. The table is computed offline by ``scripts/build_style_defaults.py``
and committed as ``data/style_defaults.json``; it rides along with the style
payload the editor already fetches, so opening a style still spends no compute.

A default is stored in the editor's own display terms -- target strength, target
colour, and flavour rows at word steps -- because those are exactly what the
visitor sees before touching anything.

The module also mirrors the browser's brief maths (``frontend/src/brief.js``) so
the build step and the CI regression can construct the byte-identical
``version: 1`` payload the editor will send. Proving anything else would prove a
brief no visitor ever asks for. The mirror is held to the browser's own
constants by ``tests/test_style_defaults.py``.
"""

import json
import os
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP

# -- mirrored from frontend/src/brief.js and components/BriefEditor.vue -------

ATTENUATION = 0.75
BATCH_GALLONS = 5.5
MASH_EFFICIENCY = 75
SRM_TOLERANCE = 1
LEVELS = ["none", "hint", "present", "bold"]
MAX_ROWS = 5

# The invented sliders a style with no BJCP stats falls back to.
FALLBACK_ABV = {"low": 4, "high": 6}
FALLBACK_SRM = {"low": 2, "high": 20}

_DEFAULTS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "style_defaults.json")

with open(_DEFAULTS_PATH, "r", encoding="utf-8") as _f:
    _TABLE = json.load(_f)

BRIEF_VERSION = _TABLE["brief_version"]
_BY_SLUG = _TABLE["styles"]


def default_for(slug):
    """Return the proved default brief for ``slug``, or None if it has none."""
    return _BY_SLUG.get(slug)


def all_defaults():
    """Return the whole committed table, keyed by style slug."""
    return dict(_BY_SLUG)


# -- the browser's maths, mirrored -------------------------------------------

def js_round(value):
    """JavaScript ``Math.round``: halves go up, never to even."""
    return int((Decimal(value) + Decimal("0.5")).to_integral_value(
        rounding=ROUND_FLOOR))


def round1(value):
    """The editor's one-decimal rounding for a strength slider value."""
    return js_round(value * 10) / 10


def seed_level(mean):
    """The word step a style-mentioned flavour arrives at, from its corpus mean."""
    if mean >= 2:
        return 3
    if mean >= 0.8:
        return 2
    return 1


def level_band(level, style_min, style_max):
    """A word step's desired sensory band inside a descriptor's style span."""
    low = float(style_min or 0)
    high = float(style_max or 0)
    span = max(0.0, high - low)
    if level == 0:
        return 0.0, low
    if level == 1:
        return low, low + span / 3
    if level == 2:
        return low + span / 3, low + (2 * span) / 3
    return low + (2 * span) / 3, high


def abv_to_og(abv):
    """Turn a target ABV into the original gravity the brief carries."""
    return 1 + abv / (ATTENUATION * 131.25)


def _clamp(value, low, high):
    return min(high, max(low, value))


def _whole_percent(value, fallback):
    number = fallback if value is None else value
    return int(_clamp(js_round(number), 0, 100))


def build_brief(style, default):
    """Build the exact ``version: 1`` payload the editor sends for ``default``.

    ``style`` is the per-style payload the editor loads (``/api/v1/styles/<slug>``)
    and ``default`` one entry of the committed table.
    """
    usage = style.get("grain_usage") or []
    allowed = [item["slug"] for item in usage]
    by_name = {item["name"]: item for item in style.get("sensory_data") or []}

    sensory = []
    for row in default["flavors"]:
        descriptor = by_name[row["name"]]
        low, high = level_band(
            row["level"], descriptor["min"], descriptor["max"])
        minimum = _clamp(low, 0, 5)
        sensory.append({
            "name": row["name"],
            "minimum": minimum,
            "maximum": _clamp(max(high, minimum), 0, 5),
        })

    gravity = Decimal(abv_to_og(default["abv"])).quantize(
        Decimal("1.0000"), rounding=ROUND_HALF_UP)
    return {
        "version": BRIEF_VERSION,
        "style": {
            "slug": style["slug"],
            "original_gravity": _clamp(float(gravity), 1, 1.2),
        },
        "equipment": {
            "batch_volume_gallons": BATCH_GALLONS,
            "mash_efficiency_percent": MASH_EFFICIENCY,
        },
        "fermentables": {
            "allowed_slugs": allowed,
            "bounds": [
                {
                    "slug": item["slug"],
                    "minimum_percent": _whole_percent(item["min_percent"], 0),
                    "maximum_percent": _whole_percent(item["max_percent"], 100),
                }
                for item in usage
            ],
            "maximum_count": int(_clamp(
                js_round(style.get("unique_fermentable_count") or 4),
                1,
                min(len(allowed), 7),
            )),
        },
        "sensory": sensory,
        "color_srm": {
            "minimum": _clamp(default["srm"] - SRM_TOLERANCE, 0, 255),
            "maximum": _clamp(default["srm"] + SRM_TOLERANCE, 0, 255),
        },
    }
