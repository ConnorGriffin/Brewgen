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
