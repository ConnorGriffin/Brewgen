/*
 * Brief model helpers: the locked none/hint/present/bold word steps and the
 * translation from a visitor's brief into the one versioned choice brief every
 * compute route accepts. Nothing here ever asks for the all-descriptor set.
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

/* ---- versioned public brief -------------------------------------------- */

const clamp = (value, low, high) => Math.min(high, Math.max(low, value))
const wholePercent = (value, fallback) => {
  const number = Number(value)
  return clamp(Math.round(Number.isFinite(number) ? number : fallback), 0, 100)
}

/* The browser sends ingredient choices and optional whole-percent bounds. The
 * server resolves the grain catalog and the style's category constraints. */
export function allowedFermentables (style) {
  const usage = style.grain_usage || []
  const allowedSlugs = usage.map((grain) => grain.slug)
  const maximumCount = clamp(
    Math.round(Number(style.unique_fermentable_count) || 4),
    1,
    Math.min(allowedSlugs.length, 7)
  )
  return {
    allowed_slugs: allowedSlugs,
    bounds: usage.map((grain) => ({
      slug: grain.slug,
      minimum_percent: wholePercent(grain.min_percent, 0),
      maximum_percent: wholePercent(grain.max_percent, 100)
    })),
    maximum_count: maximumCount
  }
}

export function sensoryBounds (flavors) {
  return flavors.map((flavor) => {
    const band = levelBand(flavor.level, flavor.styleMin, flavor.styleMax)
    const minimum = clamp(band.min, 0, 5)
    return {
      name: flavor.name,
      minimum,
      maximum: clamp(Math.max(band.max, minimum), 0, 5)
    }
  })
}

/* Every compute route accepts this same choice brief. A focused range request
 * adds only its sibling `descriptor` field. */
export function buildBrief (style, brief) {
  const half = SRM_TOLERANCE
  return {
    version: 1,
    style: {
      slug: style.slug,
      original_gravity: clamp(Number(abvToOg(brief.abv).toFixed(4)), 1, 1.2)
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

/* Stable keys for the editor's advisory compute. Whole-brief previews key the
 * exact version-one request. A focused range deliberately ignores its target
 * descriptor's own bound, matching the server's range semantics: changing only
 * that flavor therefore keeps its cached answer fresh, while strength, color,
 * style, fermentables, or any other flavor invalidate it. */
export function briefKey (style, brief) {
  return JSON.stringify(buildBrief(style, brief))
}

export function focusedRangeKey (style, brief, descriptor) {
  const payload = buildBrief(style, brief)
  return JSON.stringify({
    ...payload,
    sensory: payload.sensory.filter((bound) => bound.name !== descriptor),
    descriptor
  })
}
