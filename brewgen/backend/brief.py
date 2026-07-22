"""The strict, versioned public grain-bill brief (issue #29).

The public compute surface accepts one shape: a ``version: 1`` brief in which the
visitor submits *choices* -- a style slug and original gravity, equipment, the
fermentables they will allow with optional whole-percent bounds, a fermentable
count cap, sensory descriptor bounds, and exact SRM bounds. The server derives
the category and style-model constraints from the style slug; it never accepts
whole category/sensory/grain model objects from the client.

``parse_brief`` validates a decoded JSON body against the locked contract and, on
success, returns a :class:`DerivedBrief` carrying the solver inputs. On failure
it raises :class:`BriefError` whose ``errors`` name each offending field *by
path only* -- values are never echoed back.
"""

import math
from dataclasses import dataclass, field

# Catalog-cardinality caps (issue #29). Lists may not exceed the current
# catalog; these are also validated against the live catalog membership below,
# so the numeric caps are a cheap first gate before the membership checks.
MAX_ALLOWED_FERMENTABLES = 71
MAX_SENSORY_DESCRIPTORS = 48


class BriefError(Exception):
    """A brief that cannot be honored. ``code`` is the stable machine code
    (``invalid_brief``/``empty_brief``); ``http_status`` the response status;
    ``errors`` a list of ``{"path": ...}`` locating each offending field without
    repeating its value."""

    def __init__(self, code, http_status, errors=None):
        super().__init__(code)
        self.code = code
        self.http_status = http_status
        self.errors = errors or []


@dataclass
class DerivedBrief:
    """Solver inputs derived server-side from a valid brief."""

    grains: list
    categories: list
    sensory_bounds: list
    sensory_keywords: list
    max_unique: int
    original_sg: float
    target_volume_gallons: float
    mash_efficiency: float
    min_srm: float
    max_srm: float


# -- small typed-value guards ------------------------------------------------
#
# Booleans are a subclass of int in Python, so every numeric guard rejects bool
# explicitly ("booleans used as numbers"). JSON's NaN/Infinity survive decoding,
# so every numeric guard also requires a finite value.

def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class _Collector:
    """Accumulates field-path errors so one response can name every problem."""

    def __init__(self):
        self.errors = []

    def add(self, path):
        self.errors.append({"path": path})

    def number(self, obj, key, path, low, high):
        """Validate ``obj[key]`` is a finite number in ``[low, high]``; return it
        or ``None`` (recording an error) when absent or out of contract."""
        if key not in obj:
            self.add(path)
            return None
        value = obj[key]
        if not _is_number(value) or not math.isfinite(value):
            self.add(path)
            return None
        if not (low <= value <= high):
            self.add(path)
            return None
        return value

    def integer(self, obj, key, path, low, high):
        if key not in obj:
            self.add(path)
            return None
        value = obj[key]
        if not _is_int(value) or not (low <= value <= high):
            self.add(path)
            return None
        return value


def _reject_unknown(obj, allowed, prefix, collector):
    """Record an error for every key in ``obj`` outside ``allowed``."""
    for key in obj:
        if key not in allowed:
            collector.add(prefix + str(key))


def parse_brief(payload, all_grains, all_styles, allow_extra=()):
    """Validate ``payload`` and derive the solver model, or raise ``BriefError``.

    ``allow_extra`` names top-level keys the caller handles itself (the
    sensory-range route consumes a sibling ``descriptor``); they are exempt from
    the unknown-field rejection here.
    """
    if payload is None or (isinstance(payload, (dict, list, str)) and not payload):
        raise BriefError("empty_brief", 422)
    if not isinstance(payload, dict):
        raise BriefError("invalid_brief", 422, [{"path": ""}])

    c = _Collector()
    top = {"version", "style", "equipment", "fermentables", "sensory", "color_srm"}
    _reject_unknown(payload, top | set(allow_extra), "", c)

    # version is exactly the integer 1.
    if payload.get("version") != 1 or not _is_int(payload.get("version")):
        c.add("version")

    original_sg = _style(payload, all_styles, c)
    volume, efficiency = _equipment(payload, c)
    grains, max_unique = _fermentables(payload, all_grains, c)
    sensory_bounds = _sensory(payload, all_grains, c)
    min_srm, max_srm = _color(payload, c)

    if c.errors:
        raise BriefError("invalid_brief", 422, c.errors)

    style_obj = all_styles.get_style_by_slug(payload["style"]["slug"])
    categories = style_obj.get_category_usage()
    return DerivedBrief(
        grains=grains,
        categories=categories,
        sensory_bounds=sensory_bounds,
        sensory_keywords=list(all_grains.get_sensory_keywords()),
        max_unique=max_unique,
        original_sg=original_sg,
        target_volume_gallons=volume,
        mash_efficiency=efficiency,
        min_srm=min_srm,
        max_srm=max_srm,
    )


def _style(payload, all_styles, c):
    style = payload.get("style")
    if not isinstance(style, dict):
        c.add("style")
        return None
    _reject_unknown(style, {"slug", "original_gravity"}, "style.", c)
    slug = style.get("slug")
    if not isinstance(slug, str) or all_styles.get_style_by_slug(slug) is None:
        c.add("style.slug")
    return c.number(style, "original_gravity", "style.original_gravity", 1.000, 1.200)


def _equipment(payload, c):
    equip = payload.get("equipment")
    if not isinstance(equip, dict):
        c.add("equipment")
        return None, None
    _reject_unknown(equip, {"batch_volume_gallons", "mash_efficiency_percent"},
                    "equipment.", c)
    volume = c.number(equip, "batch_volume_gallons",
                      "equipment.batch_volume_gallons", 0.25, 100)
    efficiency = c.number(equip, "mash_efficiency_percent",
                          "equipment.mash_efficiency_percent", 1, 100)
    return volume, efficiency


def _fermentables(payload, all_grains, c):
    ferm = payload.get("fermentables")
    if not isinstance(ferm, dict):
        c.add("fermentables")
        return [], None
    _reject_unknown(ferm, {"allowed_slugs", "bounds", "maximum_count"},
                    "fermentables.", c)

    allowed = ferm.get("allowed_slugs")
    slugs = []
    if not isinstance(allowed, list) or not allowed:
        c.add("fermentables.allowed_slugs")
    elif len(allowed) > MAX_ALLOWED_FERMENTABLES:
        c.add("fermentables.allowed_slugs")
    else:
        seen = set()
        for i, slug in enumerate(allowed):
            path = "fermentables.allowed_slugs[%d]" % i
            if not isinstance(slug, str) or all_grains.get_grain_by_slug(slug) is None:
                c.add(path)
            elif slug in seen:
                c.add(path)
            else:
                seen.add(slug)
                slugs.append(slug)

    # Optional per-slug whole-percent bounds. A bound may only name a slug that
    # is present in allowed_slugs.
    bounds = ferm.get("bounds", [])
    bound_by_slug = {}
    if not isinstance(bounds, list):
        c.add("fermentables.bounds")
    else:
        seen_bounds = set()
        for i, bound in enumerate(bounds):
            base = "fermentables.bounds[%d]" % i
            if not isinstance(bound, dict):
                c.add(base)
                continue
            _reject_unknown(bound, {"slug", "minimum_percent", "maximum_percent"},
                            base + ".", c)
            slug = bound.get("slug")
            if not isinstance(slug, str) or slug not in set(slugs):
                c.add(base + ".slug")
            elif slug in seen_bounds:
                c.add(base + ".slug")
            else:
                seen_bounds.add(slug)
            lo = c.integer(bound, "minimum_percent", base + ".minimum_percent", 0, 100)
            hi = c.integer(bound, "maximum_percent", base + ".maximum_percent", 0, 100)
            if lo is not None and hi is not None and lo > hi:
                c.add(base + ".minimum_percent")
            if isinstance(slug, str):
                bound_by_slug[slug] = (lo, hi)

    max_count = c.integer(ferm, "maximum_count", "fermentables.maximum_count", 1, 7)
    if max_count is not None and slugs and max_count > len(slugs):
        c.add("fermentables.maximum_count")

    grains = []
    for slug in slugs:
        matched = all_grains.get_grain_by_slug(slug)
        lo, hi = bound_by_slug.get(slug, (0, 100))
        grains.append({
            "slug": matched.slug,
            "name": matched.name,
            "brand": matched.brand,
            "category": matched.category,
            "color": matched.color,
            "ppg": matched.ppg,
            "min_percent": lo if lo is not None else 0,
            "max_percent": hi if hi is not None else 100,
            "sensory_data": matched.sensory_data,
        })
    return grains, max_count


def _sensory(payload, all_grains, c):
    sensory = payload.get("sensory")
    known = set(all_grains.get_sensory_keywords())
    bounds = []
    if not isinstance(sensory, list):
        c.add("sensory")
        return bounds
    if len(sensory) > MAX_SENSORY_DESCRIPTORS:
        c.add("sensory")
        return bounds
    seen = set()
    for i, entry in enumerate(sensory):
        base = "sensory[%d]" % i
        if not isinstance(entry, dict):
            c.add(base)
            continue
        _reject_unknown(entry, {"name", "minimum", "maximum"}, base + ".", c)
        name = entry.get("name")
        if not isinstance(name, str) or name not in known:
            c.add(base + ".name")
        elif name in seen:
            c.add(base + ".name")
        else:
            seen.add(name)
        lo = c.number(entry, "minimum", base + ".minimum", 0, 5)
        hi = c.number(entry, "maximum", base + ".maximum", 0, 5)
        if lo is not None and hi is not None and lo > hi:
            c.add(base + ".minimum")
        if isinstance(name, str) and name in known and lo is not None and hi is not None:
            bounds.append({"name": name, "min": lo, "max": hi})
    return bounds


def _color(payload, c):
    color = payload.get("color_srm")
    if not isinstance(color, dict):
        c.add("color_srm")
        return None, None
    _reject_unknown(color, {"minimum", "maximum"}, "color_srm.", c)
    lo = c.number(color, "minimum", "color_srm.minimum", 0, 255)
    hi = c.number(color, "maximum", "color_srm.maximum", 0, 255)
    if lo is not None and hi is not None and lo > hi:
        c.add("color_srm.minimum")
    return lo, hi
