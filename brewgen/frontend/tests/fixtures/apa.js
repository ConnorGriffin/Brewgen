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
