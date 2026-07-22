/*
 * Deterministic style + solver responses so the brief editor can be exercised
 * (component test, browser test, screenshots) without a live backend. Shapes
 * mirror the real endpoints in brewgen/backend/views.py.
 */

export const styles = [
  { name: 'American Pale Ale', slug: 'american-pale-ale', category: 'Pale American Ale' },
  { name: 'Irish Stout', slug: 'irish-stout', category: 'Dark British Beer' }
]

export const style = {
  name: 'American Pale Ale',
  slug: 'american-pale-ale',
  unique_fermentable_count: 4,
  stats: {
    og: { low: 1.045, high: 1.06 },
    fg: { low: 1.01, high: 1.015 },
    ibu: { low: 30, high: 50 },
    srm: { low: 5, high: 14 },
    abv: { low: 4.5, high: 6.2 }
  },
  grain_usage: [
    { name: 'Pale 2-Row', slug: 'generic-2-row', min_percent: 55, max_percent: 95 },
    { name: 'Crystal 40', slug: 'crystal-40l', min_percent: 0, max_percent: 15 },
    { name: 'Munich', slug: 'munich-malt', min_percent: 0, max_percent: 20 }
  ],
  category_usage: [
    { name: 'base', unique_fermentable_count: 2, min_percent: 60, max_percent: 100 },
    { name: 'crystal', unique_fermentable_count: 1, min_percent: 0, max_percent: 15 }
  ],
  sensory_data: [
    { name: 'malty', min: 1.0, max: 3.0, mean: 2.2 },
    { name: 'bready', min: 0.5, max: 2.5, mean: 1.0 },
    { name: 'honey', min: 0.0, max: 1.5, mean: 0.5 },
    { name: 'caramel', min: 0.0, max: 2.0, mean: 0.9 },
    { name: 'toast', min: 0.0, max: 2.0, mean: 0.3 },
    { name: 'biscuit', min: 0.0, max: 2.0, mean: 0.4 },
    { name: 'nutty', min: 0.0, max: 1.5, mean: 0.2 },
    { name: 'coffee', min: 0.0, max: 1.0, mean: 0.05 },
    { name: 'dark_chocolate', min: 0.0, max: 1.0, mean: 0.02 }
  ],
  bjcp_sensory: {
    malty: ['Moderate malty sweetness.'],
    bready: ['Low to moderate bready character.'],
    caramel: ['Optional low caramel.']
  }
}

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
