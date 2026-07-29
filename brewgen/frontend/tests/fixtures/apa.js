/*
 * Deterministic style + solver responses so the brief editor can be exercised
 * (component test, browser test, screenshots) without a live backend. Shapes
 * mirror the real endpoints in brewgen/backend/views.py.
 *
 * The style payload itself is the *real* American Pale Ale response, committed
 * by scripts/build_style_defaults.py — a reduced stand-in is what once hid an
 * opening brief no grain bill could satisfy.
 */

export { style } from './apa-style.js'

export const styles = [
  { name: 'American Pale Ale', slug: 'american-pale-ale', category: 'Pale American Ale' },
  { name: 'Irish Stout', slug: 'irish-stout', category: 'Dark British Beer' }
]

/* A generous feasible range for any focused single-descriptor request. */
export const sensoryRange = (descriptor) => ({
  status: 'feasible', name: descriptor, min: 0.1, max: 2.6
})

export const feasibility = { status: 'feasible' }

/* ---- generation (POST /api/v1/grains/recipes) --------------------------- */

/* Three malts the shelf paints from. Colours are real Lovibond. */
const MALT = {
  'generic-2-row': { name: 'Pale 2-Row', brand: 'Generic', color_lovibond: 2 },
  'crystal-40l': { name: 'Crystal 40', brand: 'Briess', color_lovibond: 40 },
  'munich-malt': { name: 'Munich', brand: 'Weyermann', color_lovibond: 9 }
}

function bill (parts, srm, sensory) {
  return {
    grains: parts.map(([slug, use_percent]) => ({
      slug,
      use_percent,
      use_pounds: Math.round(use_percent * 0.11 * 10) / 10,
      ...MALT[slug]
    })),
    srm,
    sensory
  }
}

/* Five whole-percentage bills, each summing to 100 and every pair at least ten
 * summed points apart — the diversity floor the shelf promises. Sensory values
 * mirror the shape the endpoint now rides along with each bill. */
const BILLS = [
  bill([['generic-2-row', 90], ['crystal-40l', 10]], 6.4,
    { malty: 2.0, bready: 1.2, caramel: 1.4 }),
  bill([['generic-2-row', 80], ['munich-malt', 20]], 5.1,
    { malty: 2.4, bready: 1.6, caramel: 0.2 }),
  bill([['generic-2-row', 75], ['crystal-40l', 10], ['munich-malt', 15]], 7.2,
    { malty: 2.2, bready: 1.4, caramel: 1.0 }),
  bill([['generic-2-row', 85], ['crystal-40l', 15]], 8.1,
    { malty: 1.9, bready: 1.0, caramel: 1.8 }),
  bill([['generic-2-row', 70], ['crystal-40l', 5], ['munich-malt', 25]], 6.0,
    { malty: 2.5, bready: 1.8, caramel: 0.6 })
]

export const recipesComplete = { status: 'complete', alternatives: BILLS }
export const recipesPartial = { status: 'partial', alternatives: BILLS.slice(0, 3) }
export const recipesInfeasible = { status: 'infeasible', alternatives: [] }
export const recipesDeadline = { status: 'deadline_exceeded', alternatives: [] }

/* The brief the shelf reads back, in the shape App hands ResultsShelf. */
export const resultsContext = {
  styleName: 'American Pale Ale',
  abv: 5.4,
  srm: 8,
  flavors: [
    { name: 'malty', level: 3, styleMin: 1.0, styleMax: 3.0 },
    { name: 'bready', level: 2, styleMin: 0.5, styleMax: 2.5 },
    { name: 'caramel', level: 2, styleMin: 0.0, styleMax: 2.0 }
  ]
}
