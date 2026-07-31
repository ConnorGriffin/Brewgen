/*
 * Generate the issue #81 before/after screenshots: the brief a style opens on,
 * and what pressing Generate on that untouched brief returns.
 *
 *   before — the editor invents its opening brief from the style's midpoints
 *            and per-flavour corpus means, and the untouched brief is refused.
 *   after  — the editor opens on the style's committed, proved default, and the
 *            untouched brief comes back with grain bills.
 *
 * Both bundles are built offline and driven with the canonical harness
 * (scripts/screenshots.mjs). Both stages are served the same real American Pale
 * Ale style payload — the only difference is the app code, so each pair is a
 * like-for-like comparison. Both generation stubs are the server's real answers
 * for the brief each stage sends — the refusal for the invented one, the bills
 * for the proved default (see tests/test_style_defaults.py).
 *
 * Usage:
 *   cd brewgen/frontend && npm run build:offline          # the "after" bundle
 *   # build the pre-change bundle into .shots-before/…, then:
 *   node scripts/gen-issue-81-shots.mjs <out-dir> <before-index.html>
 */
import { writeFileSync } from 'node:fs'
import { join, resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { tmpdir } from 'node:os'
import { execFileSync } from 'node:child_process'
import * as apa from '../brewgen/frontend/tests/fixtures/apa.js'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const outDir = resolve(process.argv[2] || 'docs/screenshots/issue-81/local')
const afterIndex = 'file://' + join(repoRoot, '.shots-after/index.html')
const beforeIndex = 'file://' + resolve(process.argv[3] || '.shots-before/index.html')

const reads = {
  '/api/v1/styles/american-pale-ale': apa.style,
  '/api/v1/styles': apa.styles
}

/* The refusal exactly as the server sends it for the brief the editor used to
 * invent: problem+json, 422, the stable machine outcome tag. */
const INFEASIBLE = {
  $response: {
    status: 422,
    body: {
      type: 'about:blank', title: 'No grain bill fits this brief',
      status: 422, outcome: 'infeasible'
    }
  }
}

/* What the recipes route really returns for the proved American Pale Ale
 * default, captured once from the shipped grain and style models. */
const PROVED_BILLS = {
  status: 'complete',
  alternatives: [
  {
    grains: [{"slug": "briess-brewers-malt", "use_percent": 72, "use_pounds": 7.885313239574526, "name": "Brewer's Malt", "brand": "Briess", "color_lovibond": 1.8}, {"slug": "briess-caramel-malt-10l", "use_percent": 13, "use_pounds": 1.423737112700956, "name": "Caramel Malt 10L", "brand": "Briess", "color_lovibond": 10}, {"slug": "briess-victory-malt", "use_percent": 15, "use_pounds": 1.6427735915780262, "name": "Victory Malt", "brand": "Briess", "color_lovibond": 28}],
    srm: 8.909198025127967,
    sensory: {"sweet": 2.72, "malty": 1.44, "bready": 0.0, "honey": 0.0, "biscuit": 1.02, "nutty": 1.02, "toast": 1.0, "grainy": 1.44, "bitter": 0.0, "coffee": 0.0, "cocoa": 0.0, "dark_chocolate": 0.0, "roasted_almond": 0.0, "dried_fruit": 0.0, "wood_smoke": 0.0, "clove": 0.0, "almond": 0.13, "hazelnut": 0.0, "raisin": 0.0, "vanilla": 0.0, "marmalade": 0.0, "toffee": 0.13, "caramel": 0.26, "dark_caramel": 0.0, "sour": 0.0, "graham_cracker": 0.87, "wheat_flour": 0.0, "bread_dough": 0.0, "sourdough": 0.0, "roasted_marshmallow": 0.0, "burnt_sugar": 0.0, "prune": 0.0, "raisin_bread": 0.0, "woody": 0.0, "dark_toast": 0.0, "bread_crust": 0.3, "earthy": 0.0, "rye_bready": 0.0, "roasted": 0.0, "burnt": 0.0, "milk_chocolate": 0.0, "tobacco": 0.0, "molasses": 0.0, "creamy": 0.0, "pretzel": 0.0, "tart": 0.0, "ash": 0.0, "barbeque": 0.0}
  },
  {
    grains: [{"slug": "briess-brewers-malt", "use_percent": 76, "use_pounds": 8.342448946206046, "name": "Brewer's Malt", "brand": "Briess", "color_lovibond": 1.8}, {"slug": "briess-victory-malt", "use_percent": 9, "use_pounds": 0.9879215857349265, "name": "Victory Malt", "brand": "Briess", "color_lovibond": 28}, {"slug": "weyermann-carahell", "use_percent": 15, "use_pounds": 1.6465359762248775, "name": "CaraHell", "brand": "Weyermann", "color_lovibond": 10}],
    srm: 7.609632038025278,
    sensory: {"sweet": 2.73, "malty": 1.82, "bready": 0.21, "honey": 0.21, "biscuit": 1.06, "nutty": 0.94, "toast": 0.85, "grainy": 1.52, "bitter": 0.06, "coffee": 0.03, "cocoa": 0.03, "dark_chocolate": 0.0, "roasted_almond": 0.09, "dried_fruit": 0.09, "wood_smoke": 0.03, "clove": 0.06, "almond": 0.15, "hazelnut": 0.09, "raisin": 0.12, "vanilla": 0.12, "marmalade": 0.06, "toffee": 0.18, "caramel": 0.15, "dark_caramel": 0.09, "sour": 0.18, "graham_cracker": 0.85, "wheat_flour": 0.0, "bread_dough": 0.0, "sourdough": 0.0, "roasted_marshmallow": 0.0, "burnt_sugar": 0.0, "prune": 0.0, "raisin_bread": 0.0, "woody": 0.0, "dark_toast": 0.0, "bread_crust": 0.18, "earthy": 0.0, "rye_bready": 0.0, "roasted": 0.0, "burnt": 0.0, "milk_chocolate": 0.0, "tobacco": 0.0, "molasses": 0.0, "creamy": 0.0, "pretzel": 0.0, "tart": 0.0, "ash": 0.0, "barbeque": 0.0}
  },
  {
    grains: [{"slug": "briess-brewers-malt", "use_percent": 80, "use_pounds": 8.737927292457924, "name": "Brewer's Malt", "brand": "Briess", "color_lovibond": 1.8}, {"slug": "briess-victory-malt", "use_percent": 13, "use_pounds": 1.4199131850244124, "name": "Victory Malt", "brand": "Briess", "color_lovibond": 28}, {"slug": "generic-flaked-rice", "use_percent": 7, "use_pounds": 0.7645686380900683, "name": "Flaked Rice", "brand": "Generic", "color_lovibond": 0.8}],
    srm: 7.338589286387272,
    sensory: {"sweet": 2.695, "malty": 1.6, "bready": 0.0, "honey": 0.0, "biscuit": 1.06, "nutty": 1.06, "toast": 0.93, "grainy": 1.6, "bitter": 0.0, "coffee": 0.0, "cocoa": 0.0, "dark_chocolate": 0.0, "roasted_almond": 0.0, "dried_fruit": 0.0, "wood_smoke": 0.0, "clove": 0.0, "almond": 0.0, "hazelnut": 0.0, "raisin": 0.0, "vanilla": 0.0, "marmalade": 0.0, "toffee": 0.0, "caramel": 0.0, "dark_caramel": 0.0, "sour": 0.0, "graham_cracker": 0.93, "wheat_flour": 0.0, "bread_dough": 0.0, "sourdough": 0.0, "roasted_marshmallow": 0.0, "burnt_sugar": 0.0, "prune": 0.0, "raisin_bread": 0.0, "woody": 0.0, "dark_toast": 0.0, "bread_crust": 0.26, "earthy": 0.0, "rye_bready": 0.0, "roasted": 0.0, "burnt": 0.0, "milk_chocolate": 0.0, "tobacco": 0.0, "molasses": 0.0, "creamy": 0.0, "pretzel": 0.0, "tart": 0.0, "ash": 0.0, "barbeque": 0.0}
  },
  {
    grains: [{"slug": "briess-brewers-malt", "use_percent": 77, "use_pounds": 8.416877087236275, "name": "Brewer's Malt", "brand": "Briess", "color_lovibond": 1.8}, {"slug": "briess-caramel-malt-20l", "use_percent": 13, "use_pounds": 1.421031196546384, "name": "Caramel Malt 20L", "brand": "Briess", "color_lovibond": 20}, {"slug": "briess-victory-malt", "use_percent": 10, "use_pounds": 1.0931009204202953, "name": "Victory Malt", "brand": "Briess", "color_lovibond": 28}],
    srm: 8.88859835980877,
    sensory: {"sweet": 2.9, "malty": 1.54, "bready": 0.0, "honey": 0.0, "biscuit": 0.97, "nutty": 0.97, "toast": 1.0, "grainy": 1.54, "bitter": 0.0, "coffee": 0.0, "cocoa": 0.0, "dark_chocolate": 0.0, "roasted_almond": 0.0, "dried_fruit": 0.0, "wood_smoke": 0.0, "clove": 0.0, "almond": 0.13, "hazelnut": 0.0, "raisin": 0.13, "vanilla": 0.0, "marmalade": 0.0, "toffee": 0.13, "caramel": 0.26, "dark_caramel": 0.0, "sour": 0.0, "graham_cracker": 0.87, "wheat_flour": 0.0, "bread_dough": 0.0, "sourdough": 0.13, "roasted_marshmallow": 0.0, "burnt_sugar": 0.0, "prune": 0.0, "raisin_bread": 0.0, "woody": 0.0, "dark_toast": 0.0, "bread_crust": 0.2, "earthy": 0.0, "rye_bready": 0.0, "roasted": 0.0, "burnt": 0.0, "milk_chocolate": 0.0, "tobacco": 0.0, "molasses": 0.0, "creamy": 0.0, "pretzel": 0.0, "tart": 0.0, "ash": 0.0, "barbeque": 0.0}
  },
  {
    grains: [{"slug": "briess-brewers-malt", "use_percent": 76, "use_pounds": 8.212797938587043, "name": "Brewer's Malt", "brand": "Briess", "color_lovibond": 1.8}, {"slug": "briess-caramel-malt-60l", "use_percent": 8, "use_pounds": 0.8645050461670571, "name": "Caramel Malt 60L", "brand": "Briess", "color_lovibond": 60}, {"slug": "briess-wheat-malt-red", "use_percent": 16, "use_pounds": 1.7290100923341143, "name": "Wheat Malt, Red", "brand": "Briess", "color_lovibond": 2.3}],
    srm: 8.59476934436397,
    sensory: {"sweet": 2.76, "malty": 1.84, "bready": 0.32, "honey": 0.16, "biscuit": 0.92, "nutty": 0.76, "toast": 0.84, "grainy": 1.68, "bitter": 0.0, "coffee": 0.0, "cocoa": 0.0, "dark_chocolate": 0.0, "roasted_almond": 0.0, "dried_fruit": 0.0, "wood_smoke": 0.0, "clove": 0.0, "almond": 0.08, "hazelnut": 0.0, "raisin": 0.16, "vanilla": 0.0, "marmalade": 0.0, "toffee": 0.16, "caramel": 0.24, "dark_caramel": 0.0, "sour": 0.0, "graham_cracker": 0.76, "wheat_flour": 0.32, "bread_dough": 0.32, "sourdough": 0.08, "roasted_marshmallow": 0.16, "burnt_sugar": 0.16, "prune": 0.08, "raisin_bread": 0.0, "woody": 0.0, "dark_toast": 0.0, "bread_crust": 0.0, "earthy": 0.0, "rye_bready": 0.0, "roasted": 0.0, "burnt": 0.0, "milk_chocolate": 0.0, "tobacco": 0.0, "molasses": 0.0, "creamy": 0.0, "pretzel": 0.0, "tart": 0.0, "ash": 0.0, "barbeque": 0.0}
  }
  ]
}

const GENERATE = '.form-foot .generate'

const screens = [
  {
    name: 'brief-on-load',
    stub: { ...reads },
    clicks: []
  },
  {
    name: 'untouched-generate',
    stub: { ...reads, '/api/v1/grains/recipes': INFEASIBLE },
    afterStub: { ...reads, '/api/v1/grains/recipes': PROVED_BILLS },
    clicks: [GENERATE]
  }
]

const shots = []
for (const [stage, url] of [['before', beforeIndex], ['after', afterIndex]]) {
  for (const screen of screens) {
    for (const theme of ['light', 'dark']) {
      shots.push({
        url,
        theme,
        fetchStub: stage === 'after' && screen.afterStub
          ? screen.afterStub
          : screen.stub,
        clicks: screen.clicks,
        settle: 400,
        viewport: { width: 1280, height: 900 },
        out: join(outDir, `${screen.name}-${stage}-${theme}.png`)
      })
    }
  }
}

const configPath = join(tmpdir(), `issue-81-shots-${process.pid}.json`)
writeFileSync(configPath, JSON.stringify({ shots }, null, 2))

execFileSync('node', [join(repoRoot, 'scripts/screenshots.mjs'), configPath], { stdio: 'inherit' })
