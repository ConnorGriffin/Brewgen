/*
 * SRM colour maths, lifted from the locked mockup
 * (mockups/public-grain-bill-workflow-editorial-shelf.js). The colour slider's
 * track must be a genuine SRM gradient clipped to the selected style's range,
 * not a decorative bar.
 */

/* Standard SRM hex chart. */
const SRM_HEX = [
  [1, '#ffe699'], [2, '#ffd878'], [3, '#ffca5a'], [4, '#ffbf42'], [5, '#fbb123'],
  [6, '#f8a600'], [7, '#f39c00'], [8, '#ea8f00'], [9, '#e58500'], [10, '#de7c00'],
  [11, '#d77200'], [12, '#cf6900'], [13, '#cb6200'], [14, '#c35900'], [15, '#bb5100'],
  [16, '#b54c00'], [17, '#b04500'], [18, '#a63e00'], [19, '#a13700'], [20, '#9b3200'],
  [22, '#8f2900'], [24, '#822000'], [26, '#771900'], [28, '#6d1200'], [30, '#630d00'],
  [35, '#520a00'], [40, '#4a0700']
]

export function srmHex (srm) {
  let hex = SRM_HEX[0][1]
  for (const [s, h] of SRM_HEX) {
    if (srm >= s) hex = h
    else break
  }
  return hex
}

const SRM_WORDS = [
  [3, 'straw'], [5, 'gold'], [7, 'deep gold'], [10, 'amber-gold'],
  [13, 'amber'], [17, 'copper'], [22, 'brown'], [99, 'dark brown']
]

export const srmWord = (srm) => SRM_WORDS.find(([max]) => srm <= max)[1]

/*
 * Grain kernels read far lighter than the beer their Lovibond predicts, so a
 * malt-stack layer paints at a reduced effective SRM — Honey 20L looks
 * golden-sweet, not porter-brown (locked mockup, persona finding Walt r2).
 */
export const grainHex = (lovibond) => srmHex(Math.max(1, lovibond * 0.6))

/*
 * Pick the pour band's text colour by measured WCAG contrast rather than a
 * threshold guess: mid-amber SRM colours (6-12) fail with cream text (audit
 * finding). Compares the two candidate inks and keeps whichever reads better.
 */
const POUR_DARK_TEXT = '#3f2a06'
const POUR_LIGHT_TEXT = '#fdf6e8'

function relLum (hex) {
  const c = hex.replace('#', '')
  const [r, g, b] = [0, 2, 4].map((i) => {
    const v = parseInt(c.slice(i, i + 2), 16) / 255
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrast (a, b) {
  const [la, lb] = [relLum(a), relLum(b)]
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

export const pourText = (bg) =>
  contrast(POUR_DARK_TEXT, bg) >= contrast(POUR_LIGHT_TEXT, bg)
    ? POUR_DARK_TEXT
    : POUR_LIGHT_TEXT

/*
 * Build the CSS gradient for a track clipped to [min, max] SRM: one colour stop
 * per integer SRM step across exactly that span, so the visible band shows only
 * the colours reachable in this style.
 */
export function srmGradient (min, max) {
  const lo = Math.round(min)
  const hi = Math.max(lo, Math.round(max))
  const stops = []
  for (let s = lo; s <= hi; s++) stops.push(srmHex(s))
  if (stops.length === 1) stops.push(stops[0])
  return `linear-gradient(90deg, ${stops.join(',')})`
}
