"""Validate the public choice brief and derive trusted solver inputs.

Public callers choose a style, equipment values, allowed fermentables, sensory
bounds, and a colour band. They cannot submit the category or style models:
those constraints are resolved here from Brewgen's shipped catalogs.
"""

import math
from dataclasses import dataclass


MAX_ALLOWED_FERMENTABLES = 71
MAX_SENSORY_DESCRIPTORS = 48


class BriefError(Exception):
    """A rejected brief whose errors contain field paths, never field values."""

    def __init__(self, errors):
        super().__init__("invalid")
        self.errors = errors


@dataclass
class DerivedBrief:
    """The complete, server-derived input needed by every compute route."""

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
    descriptor: str = None


def _is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(value)


class _Errors:
    def __init__(self):
        self.items = []

    def add(self, path):
        self.items.append({"path": path})

    def number(self, obj, key, path, low, high):
        if key not in obj or not _is_number(obj[key]):
            self.add(path)
            return None
        value = obj[key]
        if not low <= value <= high:
            self.add(path)
            return None
        return value

    def integer(self, obj, key, path, low, high):
        if key not in obj or not _is_integer(obj[key]):
            self.add(path)
            return None
        value = obj[key]
        if not low <= value <= high:
            self.add(path)
            return None
        return value


def _reject_unknown(obj, allowed, prefix, errors):
    for key in obj:
        if key not in allowed:
            errors.add(prefix + str(key))


class BriefContract:
    """The strict ``version: 1`` public choice-brief contract."""

    def __init__(self, all_grains, all_styles):
        self.all_grains = all_grains
        self.all_styles = all_styles
        self._sensory_keywords = list(all_grains.get_sensory_keywords())
        self._sensory_names = set(self._sensory_keywords)

    def parse(self, payload, *, require_descriptor=False):
        """Return trusted solver inputs or raise :class:`BriefError`."""
        if not isinstance(payload, dict):
            raise BriefError([{"path": ""}])

        errors = _Errors()
        top_keys = {
            "version", "style", "equipment", "fermentables", "sensory",
            "color_srm",
        }
        if require_descriptor:
            top_keys.add("descriptor")
        _reject_unknown(payload, top_keys, "", errors)

        version = payload.get("version")
        if not _is_integer(version) or version != 1:
            errors.add("version")

        style, original_sg = self._style(payload, errors)
        volume, efficiency = self._equipment(payload, errors)
        grains, max_unique = self._fermentables(payload, errors)
        sensory_bounds = self._sensory(payload, errors)
        min_srm, max_srm = self._color(payload, errors)
        descriptor = self._descriptor(payload, require_descriptor, errors)

        if errors.items:
            raise BriefError(errors.items)

        return DerivedBrief(
            grains=grains,
            categories=style.get_category_usage(),
            sensory_bounds=sensory_bounds,
            sensory_keywords=self._sensory_keywords,
            max_unique=max_unique,
            original_sg=original_sg,
            target_volume_gallons=volume,
            mash_efficiency=efficiency,
            min_srm=min_srm,
            max_srm=max_srm,
            descriptor=descriptor,
        )

    def _style(self, payload, errors):
        value = payload.get("style")
        if not isinstance(value, dict):
            errors.add("style")
            return None, None
        _reject_unknown(
            value, {"slug", "original_gravity"}, "style.", errors)
        slug = value.get("slug")
        style = self.all_styles.get_style_by_slug(slug) \
            if isinstance(slug, str) else None
        if style is None:
            errors.add("style.slug")
        gravity = errors.number(
            value, "original_gravity", "style.original_gravity", 1.000, 1.200)
        return style, gravity

    def _equipment(self, payload, errors):
        value = payload.get("equipment")
        if not isinstance(value, dict):
            errors.add("equipment")
            return None, None
        _reject_unknown(
            value,
            {"batch_volume_gallons", "mash_efficiency_percent"},
            "equipment.",
            errors,
        )
        volume = errors.number(
            value,
            "batch_volume_gallons",
            "equipment.batch_volume_gallons",
            0.25,
            100,
        )
        efficiency = errors.number(
            value,
            "mash_efficiency_percent",
            "equipment.mash_efficiency_percent",
            1,
            100,
        )
        return volume, efficiency

    def _fermentables(self, payload, errors):
        value = payload.get("fermentables")
        if not isinstance(value, dict):
            errors.add("fermentables")
            return [], None
        _reject_unknown(
            value,
            {"allowed_slugs", "bounds", "maximum_count"},
            "fermentables.",
            errors,
        )

        allowed = value.get("allowed_slugs")
        slugs = []
        if not isinstance(allowed, list) or not allowed \
                or len(allowed) > MAX_ALLOWED_FERMENTABLES:
            errors.add("fermentables.allowed_slugs")
        else:
            seen = set()
            for index, slug in enumerate(allowed):
                path = "fermentables.allowed_slugs[%d]" % index
                grain = self.all_grains.get_grain_by_slug(slug) \
                    if isinstance(slug, str) else None
                if grain is None or slug in seen:
                    errors.add(path)
                else:
                    seen.add(slug)
                    slugs.append(slug)

        bounds = value.get("bounds", [])
        bound_by_slug = {}
        if not isinstance(bounds, list):
            errors.add("fermentables.bounds")
        else:
            allowed_set = set(slugs)
            seen_bounds = set()
            for index, bound in enumerate(bounds):
                base = "fermentables.bounds[%d]" % index
                if not isinstance(bound, dict):
                    errors.add(base)
                    continue
                _reject_unknown(
                    bound,
                    {"slug", "minimum_percent", "maximum_percent"},
                    base + ".",
                    errors,
                )
                slug = bound.get("slug")
                if not isinstance(slug, str) or slug not in allowed_set \
                        or slug in seen_bounds:
                    errors.add(base + ".slug")
                else:
                    seen_bounds.add(slug)
                minimum = errors.integer(
                    bound,
                    "minimum_percent",
                    base + ".minimum_percent",
                    0,
                    100,
                )
                maximum = errors.integer(
                    bound,
                    "maximum_percent",
                    base + ".maximum_percent",
                    0,
                    100,
                )
                if minimum is not None and maximum is not None \
                        and minimum > maximum:
                    errors.add(base + ".minimum_percent")
                if isinstance(slug, str):
                    bound_by_slug[slug] = (minimum, maximum)

        max_unique = errors.integer(
            value, "maximum_count", "fermentables.maximum_count", 1, 7)
        if max_unique is not None and isinstance(allowed, list) \
                and max_unique > len(allowed):
            errors.add("fermentables.maximum_count")

        grains = []
        for slug in slugs:
            matched = self.all_grains.get_grain_by_slug(slug)
            minimum, maximum = bound_by_slug.get(slug, (0, 100))
            grains.append({
                "slug": matched.slug,
                "name": matched.name,
                "brand": matched.brand,
                "category": matched.category,
                "color": matched.color,
                "ppg": matched.ppg,
                "min_percent": minimum if minimum is not None else 0,
                "max_percent": maximum if maximum is not None else 100,
                "sensory_data": matched.sensory_data,
            })
        return grains, max_unique

    def _sensory(self, payload, errors):
        value = payload.get("sensory")
        bounds = []
        if not isinstance(value, list) or len(value) > MAX_SENSORY_DESCRIPTORS:
            errors.add("sensory")
            return bounds

        seen = set()
        for index, item in enumerate(value):
            base = "sensory[%d]" % index
            if not isinstance(item, dict):
                errors.add(base)
                continue
            _reject_unknown(
                item, {"name", "minimum", "maximum"}, base + ".", errors)
            name = item.get("name")
            if not isinstance(name, str) or name not in self._sensory_names \
                    or name in seen:
                errors.add(base + ".name")
            else:
                seen.add(name)
            minimum = errors.number(
                item, "minimum", base + ".minimum", 0, 5)
            maximum = errors.number(
                item, "maximum", base + ".maximum", 0, 5)
            if minimum is not None and maximum is not None \
                    and minimum > maximum:
                errors.add(base + ".minimum")
            if isinstance(name, str) and name in self._sensory_names \
                    and minimum is not None and maximum is not None:
                bounds.append({"name": name, "min": minimum, "max": maximum})
        return bounds

    def _color(self, payload, errors):
        value = payload.get("color_srm")
        if not isinstance(value, dict):
            errors.add("color_srm")
            return None, None
        _reject_unknown(value, {"minimum", "maximum"}, "color_srm.", errors)
        minimum = errors.number(
            value, "minimum", "color_srm.minimum", 0, 255)
        maximum = errors.number(
            value, "maximum", "color_srm.maximum", 0, 255)
        if minimum is not None and maximum is not None and minimum > maximum:
            errors.add("color_srm.minimum")
        return minimum, maximum

    def _descriptor(self, payload, required, errors):
        if not required:
            return None
        value = payload.get("descriptor")
        if not isinstance(value, str) or value not in self._sensory_names:
            errors.add("descriptor")
            return None
        return value
