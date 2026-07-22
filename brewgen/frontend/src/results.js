/*
 * Results-shelf model helpers, ported from the locked #26 mockup
 * (mockups/public-grain-bill-workflow-editorial-shelf.js). Everything the shelf
 * shows is derived here from the real /api/v1/grains/recipes response and the
 * brief the visitor submitted — letters, outcome state, the order-ticket
 * readback, malt-stack layers, the tastes line, and the sparse differentiators.
 * No sensory value is invented; each bill's sensory ride-along comes straight
 * from the solver's sensory model.
 */

import { srmHex, srmWord, grainHex, pourText } from '@/srm.js'
import { humanize, abvToOg, BATCH_GALLONS, MASH_EFFICIENCY } from '@/brief.js'

/* Bills are lettered, never ranked. Order is the deterministic solver order, so
 * a letter stays glued to its bill across selection. */
export const LETTERS = 'ABCDEFGHIJ'.split('')

export function withLetters (alternatives) {
  return (alternatives || []).map((alt, i) => ({
    ...alt,
    letter: LETTERS[i] || `#${i + 1}`
  }))
}

/*
 * Six outcome states from four solver statuses plus two UI-only states:
 * `malformed` (an invalid brief or a non-200 answer) and `empty` (nothing was
 * submitted, or nothing came back to show). Leaks no solver/server internals.
 */
export function resolveOutcome (result) {
  if (!result) return 'empty'
  if (result.error || !result.status) return 'malformed'
  if (result.status === 'infeasible') return 'infeasible'
  if (result.status === 'deadline_exceeded') return 'deadline'
  const bills = result.alternatives || []
  if (!bills.length) return 'empty'
  if (result.status === 'partial') return 'partial'
  if (result.status === 'complete') return 'complete'
  return 'malformed'
}

/* Stable plain-language copy for the states that replace the shelf. Complete and
 * partial keep the shelf; the rest render a single quiet notice. */
export const OUTCOME_NOTICE = {
  infeasible: {
    title: 'No grain bill fits',
    message: 'No grain bill satisfies every part of this brief. Ease a flavor or widen the color, then send it again.'
  },
  deadline: {
    title: 'Ran out of time',
    message: 'The clock ran out before a grain bill came together. Send the brief again in a moment.'
  },
  malformed: {
    title: 'That brief slipped through',
    message: 'This brief did not come through cleanly. Head back and send it again.'
  },
  empty: {
    title: 'No brief yet',
    message: 'Start with a brief and Brewgen will find the grain bills.'
  }
}

/* ---- order-ticket brief readback --------------------------------------- */

const FLAVOR_WORDS = {
  malty: 'malty', honey: 'honeyed', toast: 'toasty', coffee: 'coffee',
  biscuit: 'biscuity', bready: 'bready', caramel: 'caramelly',
  stone_fruit: 'stone-fruity', chocolate: 'chocolatey',
  dark_chocolate: 'dark chocolate', nutty: 'nutty', smoke: 'smoky'
}

const esc = (s) => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1)
const joinAnd = (a) =>
  a.length < 2 ? a.join('') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1]

/*
 * The brief read back as one flat serif sentence in order-ticket voice, with
 * underlined terms and no em-dashes: "American Pale Ale. Malty and honeyed, no
 * coffee. About 5.5%, amber-gold." Returns an HTML string (underline spans).
 */
export function briefSentence (context) {
  const flavors = context.flavors || []
  const word = (f) => FLAVOR_WORDS[f.name] || humanize(f.name)
  const main = flavors.filter((f) => f.level >= 2).map(word)
  const hints = flavors.filter((f) => f.level === 1).map((f) => humanize(f.name))
  const nones = flavors.filter((f) => f.level === 0).map((f) => humanize(f.name))
  const u = (t) => `<span class="u">${esc(t)}</span>`
  const ur = (t) => `<span class="u ur">${esc(t)}</span>`

  let flavor = ''
  if (main.length) flavor += joinAnd([cap(main[0]), ...main.slice(1)].map(u))
  if (hints.length) flavor += (flavor ? ', a hint of ' : 'A hint of ') + joinAnd(hints.map(u))
  if (nones.length) flavor += (flavor ? ', no ' : 'No ') + joinAnd(nones.map(ur))

  const facts = `About ${u(Number(context.abv).toFixed(1) + '%')}, ${u(srmWord(context.srm))}.`
  const style = u(context.styleName)
  return flavor ? `${style}. ${flavor}. ${facts}` : `${style}. ${facts}`
}

/* ---- per-bill sensory read-back ---------------------------------------- */

/*
 * Sparse differentiators: at most one italic aside per bill, and only where the
 * spread across bills is meaningful (>15% of the max). Wanted flavors earn
 * "most X" on their standout bill; avoided flavors earn "lowest X" — but only
 * when some bill actually carries a tasteable amount, so "lowest coffee" over
 * five near-zeros never misleads.
 */
export function differentiators (bills, flavors) {
  const asides = {}
  const wanted = flavors.filter((f) => f.level >= 2).map((f) => f.name)
  const avoided = flavors.filter((f) => f.level === 0).map((f) => f.name)
  const valuesOf = (name) => bills.map((b) => (b.sensory && b.sensory[name]) || 0)
  const claim = (letter, text) => { if (!asides[letter]) asides[letter] = text }

  for (const name of wanted) {
    const vals = valuesOf(name)
    const max = Math.max(...vals)
    const min = Math.min(...vals)
    if (max <= 0 || (max - min) / max < 0.15) continue
    claim(bills[vals.indexOf(max)].letter, `most ${humanize(name)}`)
  }
  for (const name of avoided) {
    const vals = valuesOf(name)
    const max = Math.max(...vals)
    const min = Math.min(...vals)
    if (max < 0.3 || (max - min) / max < 0.15) continue
    claim(bills[vals.indexOf(min)].letter, `lowest ${humanize(name)}`)
  }
  return asides
}

/*
 * The bill's flavors read back in the brief's own none/hint/present/bold
 * vocabulary, each normalized against that descriptor's style span.
 */
export function tastesWords (bill, flavors) {
  return flavors
    .filter((f) => bill.sensory && f.name in bill.sensory)
    .map((f) => {
      const v = bill.sensory[f.name]
      const lo = Number(f.styleMin) || 0
      const hi = Number(f.styleMax) || 0
      const span = hi - lo
      const t = span > 0 ? (v - lo) / span : v / 2
      const label = humanize(f.name)
      if (t < 0.08) return `no ${label}`
      if (t < 0.4) return `a hint of ${label}`
      if (t < 0.75) return `${label} present`
      return `bold ${label}`
    })
}

/* ---- malt stack + pour band -------------------------------------------- */

/* One layer per grain: colour from the malt's real (reduced) Lovibond, flex
 * weight from its percentage, so height tracks usage. */
export function stackLayers (bill) {
  return bill.grains.map((g) => ({
    flex: g.use_percent,
    background: grainHex(g.color_lovibond)
  }))
}

export function pourBand (bill, abv) {
  const background = srmHex(bill.srm)
  return {
    background,
    color: pourText(background),
    label: `${srmWord(bill.srm)} · ${bill.srm.toFixed(1)} SRM · ${Number(abv).toFixed(1)}% ABV`
  }
}

export const grainSwatch = (g) => grainHex(g.color_lovibond)

/* The quiet batch footnote on the open card: total grain, batch volume, target
 * OG (from the brief's strength), and the fixed mash efficiency. */
export function batchNote (bill, abv) {
  const totalPounds = bill.grains.reduce((s, g) => s + g.use_pounds, 0)
  const og = abvToOg(abv)
  return `${totalPounds.toFixed(1)} lb grain · ${BATCH_GALLONS} gal batch · ` +
    `OG ${og.toFixed(3)} · ${MASH_EFFICIENCY}% efficiency`
}
