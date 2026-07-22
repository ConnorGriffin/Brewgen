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

/* ---- the versioned public brief ----------------------------------------- */

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))

/* The allowed fermentables and their whole-percent bounds, taken straight from
 * the style's own grain usage. The server derives the category and style-model
 * constraints itself from the style slug — the client never sends them. */
export function allowedFermentables (style) {
  const usage = style.grain_usage || []
  const allowed_slugs = usage.map((g) => g.slug)
  const bounds = usage.map((g) => ({
    slug: g.slug,
    minimum_percent: clamp(Math.round(Number(g.min_percent) || 0), 0, 100),
    maximum_percent: clamp(Math.round(Number(g.max_percent) || 100), 0, 100)
  }))
  const maximum_count = clamp(
    Math.round(style.unique_fermentable_count || 4), 1, Math.min(allowed_slugs.length, 7))
  return { allowed_slugs, bounds, maximum_count }
}

/* Each flavour row's desired band as a sensory bound (0–5). */
export function sensoryBounds (flavors) {
  return flavors.map((f) => {
    const band = levelBand(f.level, f.styleMin, f.styleMax)
    const minimum = clamp(band.min, 0, 5)
    const maximum = clamp(Math.max(band.max, minimum), 0, 5)
    return { name: f.name, minimum, maximum }
  })
}

/*
 * The one strict `version: 1` brief every compute endpoint accepts. The focused
 * range caller adds a sibling `descriptor`; feasibility and generation send it
 * as-is. Whole model objects are never included — only the visitor's choices.
 */
export function buildBrief (style, brief) {
  const half = SRM_TOLERANCE
  return {
    version: 1,
    style: {
      slug: style.slug,
      original_gravity: clamp(Number(abvToOg(brief.abv).toFixed(4)), 1.0, 1.2)
    },
    equipment: {
      batch_volume_gallons: BATCH_GALLONS,
      mash_efficiency_percent: MASH_EFFICIENCY
    },
    fermentables: allowedFermentables(style),
    sensory: sensoryBounds(brief.flavors),
    color_srm: {
      minimum: clamp(brief.srm - half, 0, 255),
      maximum: clamp(brief.srm + half, 0, 255)
    }
  }
}
