"""Every shipped style must open on a brief that can actually be brewed.

The brief editor no longer builds its opening brief out of a style's midpoint
strength, midpoint colour and per-flavour corpus means: nothing proved those
individually typical numbers intersected, and for a third of the catalog they
did not -- an untouched American Pale Ale went straight to "no grain bill fits".

These cases hold the committed default table to the promise that replaced it.
They read the real shipped style data, build the exact brief the browser sends,
and push it through the same strict ``version: 1`` contract and the same
generation route a visitor's Generate reaches. Adding a style, or changing a
style's grain, category or sensory model, fails here until
``scripts/build_style_defaults.py`` is re-run and its output committed.
"""

import json
import re
from pathlib import Path

import pytest

from brewgen.backend import envelope, style_defaults, views

REPO = Path(__file__).resolve().parents[1]
FRONTEND = REPO / "brewgen" / "frontend"
FIXTURES = FRONTEND / "tests" / "fixtures"

EXPECTED_STYLE_COUNT = 67


@pytest.fixture
def client():
    return views.app.test_client()


@pytest.fixture(scope="session")
def style_payloads():
    """Every style exactly as the editor loads it, keyed by slug."""
    client = views.app.test_client()
    payloads = {}
    for summary in client.get("/api/v1/styles").get_json():
        payloads[summary["slug"]] = client.get(
            "/api/v1/styles/%s" % summary["slug"]).get_json()
    return payloads


def _strongest_mentioned(style):
    """The style's BJCP-mentioned descriptors, boldest corpus mean first."""
    by_name = {item["name"]: item for item in style["sensory_data"]}
    named = [by_name[name] for name in sorted(style["bjcp_sensory"])
             if name in by_name]
    named.sort(key=lambda item: (-item["mean"], item["name"]))
    return named


# -- the catalog -------------------------------------------------------------

def test_clone_beer_is_gone_and_every_remaining_style_carries_a_default(client):
    listed = client.get("/api/v1/styles").get_json()
    assert len(listed) == EXPECTED_STYLE_COUNT
    assert "Clone Beer" not in [style["name"] for style in listed]
    assert "clone-beer" not in [style["slug"] for style in listed]
    # Its slug stops resolving, so a stale deep link degrades to the editor's
    # quiet "couldn't load the styles" notice rather than a server error.
    assert client.get("/api/v1/styles/clone-beer").status_code == 404

    for style in listed:
        payload = client.get("/api/v1/styles/%s" % style["slug"]).get_json()
        assert payload["default"] is not None, style["slug"]


# -- what a default is made of ----------------------------------------------

def test_defaults_lead_with_a_style_s_strongest_flavors(style_payloads):
    for slug, style in style_payloads.items():
        wanted = [item["name"]
                  for item in _strongest_mentioned(style)][:style_defaults.MAX_ROWS]
        served = [row["name"] for row in style["default"]["flavors"]]
        # Rows are dropped weakest-first, so a default is always a prefix of the
        # style's own strongest descriptors -- never an alphabetical accident.
        assert served == wanted[:len(served)], slug

    # Ordinary Bitter used to open on `earthy`, whose corpus range is flat zero,
    # purely because the name sorts early.
    bitter = [row["name"]
              for row in style_payloads["ordinary-bitter"]["default"]["flavors"]]
    assert "earthy" not in bitter
    assert "toffee" in bitter


def test_defaults_never_seed_an_avoid_step_or_leave_the_style_s_own_ranges(
        style_payloads):
    for slug, style in style_payloads.items():
        default = style["default"]
        stats = style["stats"] or {}
        abv = stats.get("abv") or style_defaults.FALLBACK_ABV
        srm = stats.get("srm") or style_defaults.FALLBACK_SRM

        assert style_defaults.round1(abv["low"]) <= default["abv"] \
            <= style_defaults.round1(abv["high"]), slug
        assert style_defaults.js_round(srm["low"]) <= default["srm"] \
            <= style_defaults.js_round(srm["high"]), slug
        for row in default["flavors"]:
            # 0 is the avoid state; a default asks for flavour, never against it.
            assert 1 <= row["level"] <= 3, (slug, row)


# -- the promise itself ------------------------------------------------------

def test_every_style_default_generates_at_least_one_grain_bill(
        client, style_payloads):
    assert len(style_payloads) == EXPECTED_STYLE_COUNT
    for slug, style in style_payloads.items():
        brief = style_defaults.build_brief(style, style["default"])
        # Each style arrives as its own visitor: the shared anonymous-compute
        # allowance is what a real first Generate spends, not this sweep.
        envelope.reset_state()
        response = client.post("/api/v1/grains/recipes", json=brief)
        assert response.status_code == 200, (slug, response.get_json())
        assert response.get_json()["alternatives"], slug


def test_the_opening_brief_the_editor_used_to_invent_still_does_not_generate(
        client, style_payloads):
    """The reported bug, pinned where a visitor met it.

    Taking a style's first five mentioned descriptors in name order and setting
    each from its own corpus mean gives American Pale Ale a brief whose five
    flavour bands cannot hold together. It is still infeasible; the point is that
    it is no longer what anyone is shown.
    """
    style = style_payloads["american-pale-ale"]
    by_name = {item["name"]: item for item in style["sensory_data"]}
    in_name_order = [name for name in sorted(style["bjcp_sensory"])
                     if name in by_name][:style_defaults.MAX_ROWS]
    invented = {
        "abv": style["default"]["abv"],
        "srm": style["default"]["srm"],
        "flavors": [
            {"name": name, "level": style_defaults.seed_level(by_name[name]["mean"])}
            for name in in_name_order
        ],
    }
    assert invented["flavors"] != style["default"]["flavors"]

    envelope.reset_state()
    response = client.post("/api/v1/grains/recipes",
                           json=style_defaults.build_brief(style, invented))
    assert response.status_code == 422
    assert response.get_json()["outcome"] == "infeasible"


# -- the browser and the build step must send the same request ---------------

def test_the_proved_brief_is_the_brief_the_browser_builds(style_payloads):
    """The committed fixture is the anchor both sides are held to.

    ``brewgen/frontend/tests/brief-editor.spec.js`` asserts the browser's own
    brief maths reproduce this fixture from the same style payload; this asserts
    the mirror the build step proved it with does too. If either drifts, one of
    the two fails and the default stops meaning anything.
    """
    proved = json.loads((FIXTURES / "apa-proved-brief.json").read_text())
    style = style_payloads["american-pale-ale"]
    assert style_defaults.build_brief(style, style["default"]) == proved


def test_the_mirrored_brief_constants_match_the_browser_s():
    brief_js = (FRONTEND / "src" / "brief.js").read_text()
    editor = (FRONTEND / "src" / "components" / "BriefEditor.vue").read_text()

    def number(source, name):
        match = re.search(r"\b%s = ([0-9.]+)" % name, source)
        assert match, name
        return float(match.group(1))

    assert number(brief_js, "ATTENUATION") == style_defaults.ATTENUATION
    assert number(brief_js, "BATCH_GALLONS") == style_defaults.BATCH_GALLONS
    assert number(brief_js, "MASH_EFFICIENCY") == style_defaults.MASH_EFFICIENCY
    assert number(brief_js, "SRM_TOLERANCE") == style_defaults.SRM_TOLERANCE
    assert number(editor, "MAX_ROWS") == style_defaults.MAX_ROWS

    levels = re.search(r"LEVELS = \[([^\]]+)\]", brief_js).group(1)
    assert re.findall(r"'([a-z]+)'", levels) == style_defaults.LEVELS

    # The invented sliders a stats-less style falls back to live in the editor.
    fallback = re.search(r"stats\?\.abv \|\| \{ low: (\d+), high: (\d+) \}", editor)
    assert [int(fallback.group(1)), int(fallback.group(2))] == [
        style_defaults.FALLBACK_ABV["low"], style_defaults.FALLBACK_ABV["high"]]
    fallback = re.search(r"stats\?\.srm \|\| \{ low: (\d+), high: (\d+) \}", editor)
    assert [int(fallback.group(1)), int(fallback.group(2))] == [
        style_defaults.FALLBACK_SRM["low"], style_defaults.FALLBACK_SRM["high"]]
