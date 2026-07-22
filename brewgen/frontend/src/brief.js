/*
 * Brief model helpers: the locked none/hint/present/bold word steps and the
 * translation from a visitor's brief into the payloads the two focused #36
 * solver endpoints consume. Nothing here ever asks for the all-descriptor set.
 */

/* Word-step levels. Index 0 ("none") doubles as the rosewood avoid state. */
export const LEVELS = ['none', 'hint', 'present', 'bold']

/* Fixed brewhouse assumptions — the Advanced section stays collapsed per the
 * #26 decisions, so these are constants rather than visitor inputs. */
export const ATTENUATION = 0.75
export const BATCH_GALLONS = 5.5
export const MASH_EFFICIENCY = 75
/* A single-thumb colour control expresses one target SRM; give the solver a
 * narrow band around it rather than an impossible exact-equality constraint. */
export const SRM_TOLERANCE = 1

/* Turn an underscore descriptor slug into a human label ("dark_chocolate" ->
 * "dark chocolate") for display; the slug itself is what the solver wants. */
export const humanize = (name) => name.replace(/_/g, ' ')

/*
 * A flavour row's desired sensory band, expressed as a sub-range of the
 * descriptor's style span [min, max]. "none" sits below the style floor (the
 * avoid state); hint/present/bold split the style span into thirds.
 */
export function levelBand (level, styleMin, styleMax) {
  const lo = Number(styleMin) || 0
  const hi = Number(styleMax) || 0
  const span = Math.max(0, hi - lo)
  switch (level) {
    case 0: return { min: 0, max: lo }
    case 1: return { min: lo, max: lo + span / 3 }
    case 2: return { min: lo + span / 3, max: lo + (2 * span) / 3 }
    default: return { min: lo + (2 * span) / 3, max: hi }
  }
}

/* The default level a style-mentioned flavour arrives at, from its style mean —
 * mirrors the locked mockup's seeding (mean>=2 bold, >=0.8 present, else hint). */
export function seedLevel (mean) {
  const m = Number(mean) || 0
  if (m >= 2) return 3
  if (m >= 0.8) return 2
  return 1
}

/* Convert a target ABV into an original gravity using the fixed attenuation, so
 * the strength slider actually moves the brief the solver judges. */
export function abvToOg (abv) {
  return 1 + Number(abv) / (ATTENUATION * 131.25)
}

export function ogToAbv (og) {
  return (Number(og) - 1) * ATTENUATION * 131.25
}

/* Which word steps are reachable given a descriptor's conditional range from
 * #36: a step is reachable when its band overlaps [rangeMin, rangeMax]. */
export function reachableLevels (styleMin, styleMax, range) {
  if (!range || range.min == null || range.max == null) {
    return LEVELS.map(() => true)
  }
  return LEVELS.map((_, level) => {
    const band = levelBand(level, styleMin, styleMax)
    return band.min <= range.max && band.max >= range.min
  })
}

/* ---- solver payloads ---------------------------------------------------- */

export function fermentableList (style) {
  return (style.grain_usage || []).map((g) => ({
    slug: g.slug,
    min_percent: g.min_percent,
    max_percent: g.max_percent
  }))
}

export function categoryModel (style) {
  // The style endpoint already returns the category shape the solver reads.
  return style.category_usage || []
}

export function sensoryModel (flavors) {
  return flavors.map((f) => {
    const band = levelBand(f.level, f.styleMin, f.styleMax)
    return { name: f.name, min: band.min, max: band.max }
  })
}

export function beerProfile (brief) {
  const half = SRM_TOLERANCE
  return {
    original_sg: Number(abvToOg(brief.abv).toFixed(4)),
    min_color_srm: Math.max(0, brief.srm - half),
    max_color_srm: brief.srm + half
  }
}

export function equipmentProfile () {
  return {
    target_volume_gallons: BATCH_GALLONS,
    mash_efficiency: MASH_EFFICIENCY
  }
}

/* The shared body both focused endpoints accept. `descriptor` is added by the
 * single-flavour range caller; feasibility omits it. */
export function briefPayload (style, brief) {
  return {
    fermentable_list: fermentableList(style),
    category_model: categoryModel(style),
    sensory_model: sensoryModel(brief.flavors),
    max_unique_fermentables: style.unique_fermentable_count || 4,
    equipment_profile: equipmentProfile(),
    beer_profile: beerProfile(brief)
  }
}
