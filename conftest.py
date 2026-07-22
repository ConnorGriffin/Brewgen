"""Shared pytest fixtures and helpers for the Brewgen test suite.

Living at the repo root, this file puts the project on ``sys.path`` so
``import brewgen...`` resolves without an install, and provides small builders
for synthetic and real grain/category models used across the solver tests.
"""

import json
import os

import pytest

# Ensure the repo root (this file's directory) is importable.
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GRAINS_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "brewgen", "backend", "data", "grains.json")


def make_grain(slug, category="base", color=2.0, ppg=37.0,
               min_percent=0, max_percent=100, sensory=None):
    """Build a synthetic solver grain dict."""
    return {
        "slug": slug,
        "category": category,
        "color": color,
        "ppg": ppg,
        "min_percent": min_percent,
        "max_percent": max_percent,
        "sensory_data": sensory or {},
    }


def make_category(name, min_percent=0, max_percent=100,
                  unique_fermentable_count=None):
    """Build a synthetic solver category dict."""
    return {
        "name": name,
        "min_percent": min_percent,
        "max_percent": max_percent,
        "unique_fermentable_count": unique_fermentable_count,
    }


def make_brief(style_obj, allowed=None, sensory=None, bounds=None,
               min_srm=3.0, max_srm=20.0, original_gravity=1.05,
               maximum_count=None, **overrides):
    """Build a valid ``version: 1`` public brief from a real style object.

    Mirrors what the front end submits: the style's own grains as the allowed
    fermentables with their usage bounds, no sensory bounds unless supplied, and
    a broad colour band. ``overrides`` replace whole top-level sections so a test
    can inject a single malformed field."""
    grain_usage = style_obj.get_grain_usage()
    if allowed is None:
        allowed = [g["slug"] for g in grain_usage]
    allowed_set = set(allowed)
    if bounds is None:
        bounds = [{"slug": g["slug"],
                   "minimum_percent": int(g["min_percent"]),
                   "maximum_percent": int(g["max_percent"])}
                  for g in grain_usage if g["slug"] in allowed_set]
    if maximum_count is None:
        maximum_count = min(style_obj.unique_fermentable_count or 4, len(allowed), 7) or 1
    brief = {
        "version": 1,
        "style": {"slug": style_obj.slug, "original_gravity": original_gravity},
        "equipment": {"batch_volume_gallons": 5.5, "mash_efficiency_percent": 75},
        "fermentables": {
            "allowed_slugs": list(allowed),
            "bounds": bounds,
            "maximum_count": maximum_count,
        },
        "sensory": sensory if sensory is not None else [],
        "color_srm": {"minimum": min_srm, "maximum": max_srm},
    }
    for key, value in overrides.items():
        brief[key] = value
    return brief


@pytest.fixture(scope="session")
def real_grains():
    """All grains from the shipped database as solver grain dicts."""
    with open(GRAINS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    grains = []
    for g in data:
        grains.append({
            "slug": _slug(g["name"], g["brand"]),
            "category": g["category"],
            "color": g["color"],
            "ppg": (g["potential"] - 1) * 1000,
            "min_percent": 0,
            "max_percent": g["max_percent"],
            "sensory_data": g.get("sensory") or {},
        })
    return grains


def _slug(name, brand):
    from slugify import slugify
    return slugify("{}_{}".format(brand, name), replacements=[["'", ""], ["®", ""]])
