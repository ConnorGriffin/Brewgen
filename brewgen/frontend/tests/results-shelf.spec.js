import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ResultsShelf from '@/components/ResultsShelf.vue'
import * as apa from './fixtures/apa.js'

/* The shelf reads the width from matchMedia; stub it so a test can pin the
 * desktop (flat cards) or mobile (spines-first) composition deterministically. */
function stubWidth (mobile) {
  window.matchMedia = vi.fn().mockReturnValue({
    matches: mobile,
    addEventListener: () => {},
    removeEventListener: () => {}
  })
}

async function mountShelf (result, { mobile = false, context = apa.resultsContext } = {}) {
  stubWidth(mobile)
  const wrapper = mount(ResultsShelf, { props: { context, result, loading: false } })
  await flushPromises() // let onMounted settle the width
  return wrapper
}

/* Read the displayed percentages off each closed card, keyed by grain, so the
 * regression check works on what the visitor actually sees. */
function displayedBills (wrapper) {
  return wrapper.findAll('.card').map((card) => {
    const bill = {}
    card.findAll('.grain-row').forEach((row) => {
      const grain = row.find('.grain-name').text().trim()
      bill[grain] = parseInt(row.find('.grain-nums b').text(), 10)
    })
    return bill
  })
}

beforeEach(() => { vi.restoreAllMocks() })
afterEach(() => { delete window.matchMedia })

describe('public results shelf', () => {
  it('renders up to five lettered, unranked bills as a flat desktop shelf', async () => {
    const wrapper = await mountShelf(apa.recipesComplete)

    // Letters A..E, never rankings; all visible as full cards, none as spines.
    expect(wrapper.findAll('.letter').map((n) => n.text())).toEqual(['A', 'B', 'C', 'D', 'E'])
    expect(wrapper.findAll('.card')).toHaveLength(5)
    expect(wrapper.findAll('.card.open')).toHaveLength(0)
    expect(wrapper.findAll('.spine')).toHaveLength(0)
    expect(wrapper.find('.result-head h2').text()).toBe('5 grain bills')
  })

  it('shows whole percentages summing to 100, every displayed pair ≥10 points apart', async () => {
    const wrapper = await mountShelf(apa.recipesComplete)
    const bills = displayedBills(wrapper)
    expect(bills).toHaveLength(5)

    for (const bill of bills) {
      const total = Object.values(bill).reduce((a, b) => a + b, 0)
      expect(total).toBe(100)
      expect(Object.values(bill).every((p) => Number.isInteger(p))).toBe(true)
    }
    // The diversity floor the shelf promises: no two displayed bills within ten
    // summed percentage points of each other.
    for (let i = 0; i < bills.length; i++) {
      for (let j = i + 1; j < bills.length; j++) {
        const keys = new Set([...Object.keys(bills[i]), ...Object.keys(bills[j])])
        let distance = 0
        keys.forEach((k) => { distance += Math.abs((bills[i][k] || 0) - (bills[j][k] || 0)) })
        expect(distance).toBeGreaterThanOrEqual(10)
      }
    }
  })

  it('renders the malt stack, pour band, dot-leader percentages and tastes line', async () => {
    const wrapper = await mountShelf(apa.recipesComplete)
    const first = wrapper.findAll('.card')[0]

    // Layered malt stack with real-malt colours and swatches on the grain rows.
    expect(first.findAll('.stack .layer').length).toBeGreaterThanOrEqual(2)
    expect(first.find('.layer').attributes('style')).toContain('background')
    expect(first.find('.swatch').attributes('style')).toContain('background')
    // Pour band tinted to the bill's SRM, carrying the SRM/ABV line.
    const pour = first.find('.pour')
    expect(pour.attributes('style')).toContain('background')
    expect(pour.text()).toMatch(/SRM/)
    expect(pour.text()).toMatch(/ABV/)

    // Open one and confirm the per-bill tastes line reads back in brief words.
    await first.trigger('click')
    const tastes = wrapper.find('.card.open .tastes')
    expect(tastes.exists()).toBe(true)
    expect(tastes.text()).toMatch(/malty|bready|caramel/)
  })

  it('carries at most one sparse italic differentiator per bill', async () => {
    const wrapper = await mountShelf(apa.recipesComplete)
    const asides = wrapper.findAll('.aside').map((a) => a.text())
    // D carries the most caramel, E the most malty — the only meaningful spreads.
    expect(asides).toContain('most caramel')
    expect(asides).toContain('most malty')
    expect(asides.length).toBeLessThanOrEqual(wrapper.findAll('.card').length)
    expect(asides).toHaveLength(2)
  })

  it('expands a clicked desktop card and compresses the rest to spines', async () => {
    const wrapper = await mountShelf(apa.recipesComplete)
    await wrapper.findAll('.card')[1].trigger('click') // select B

    expect(wrapper.findAll('.card.open')).toHaveLength(1)
    expect(wrapper.find('.card.open .letter').text()).toBe('B')
    expect(wrapper.findAll('.spine')).toHaveLength(4)
    expect(wrapper.find('.shelf').classes()).toContain('focused')

    // "show all" returns to the flat shelf.
    await wrapper.find('.result-note a').trigger('click')
    expect(wrapper.findAll('.card.open')).toHaveLength(0)
    expect(wrapper.findAll('.spine')).toHaveLength(0)
  })

  it('begins mobile in the spines composition: one open bill, flanking spines', async () => {
    const wrapper = await mountShelf(apa.recipesComplete, { mobile: true })

    expect(wrapper.findAll('.card.open')).toHaveLength(1)
    expect(wrapper.find('.card.open .letter').text()).toBe('A')
    expect(wrapper.findAll('.spine')).toHaveLength(4)
    // Never a flat vertical card list on mobile.
    expect(wrapper.findAll('.card:not(.open)')).toHaveLength(0)
  })

  it('reads the brief back in order-ticket voice with underlined terms and no em-dash', async () => {
    const wrapper = await mountShelf(apa.recipesComplete)
    const line = wrapper.find('.brief-line')

    expect(line.html()).toContain('class="u"')
    expect(line.text()).toContain('American Pale Ale')
    expect(line.text()).not.toContain('—')
    expect(wrapper.find('.edit-brief').exists()).toBe(true)
  })

  it('shows the partial note when only some bills fit', async () => {
    const wrapper = await mountShelf(apa.recipesPartial)
    expect(wrapper.find('.result-head h2').text()).toBe('3 grain bills')
    expect(wrapper.find('.result-note').text()).toContain('Only 3 distinct grain bills fit this brief.')
  })

  const leakless = (text) => {
    expect(text).not.toMatch(/infeasible|deadline_exceeded|solver|status|\b[45]\d\d\b/i)
  }

  it('renders the infeasible state in the locked voice without leaking internals', async () => {
    const wrapper = await mountShelf(apa.recipesInfeasible)
    expect(wrapper.find('.notice-infeasible').exists()).toBe(true)
    expect(wrapper.find('.notice-title').text()).toBe('No grain bill fits')
    expect(wrapper.find('.shelf').exists()).toBe(false)
    leakless(wrapper.find('.notice').text())
  })

  it('renders the deadline state in the locked voice without leaking internals', async () => {
    const wrapper = await mountShelf(apa.recipesDeadline)
    expect(wrapper.find('.notice-deadline').exists()).toBe(true)
    expect(wrapper.find('.notice-title').text()).toBe('Ran out of time')
    leakless(wrapper.find('.notice').text())
  })

  it('renders the malformed state for a non-200 / unreadable answer', async () => {
    const wrapper = await mountShelf({ error: true })
    expect(wrapper.find('.notice-malformed').exists()).toBe(true)
    leakless(wrapper.find('.notice').text())
  })

  it('renders the empty state when no brief was submitted', async () => {
    const wrapper = await mountShelf(null, { context: null })
    expect(wrapper.find('.notice-empty').exists()).toBe(true)
    expect(wrapper.find('.notice-title').text()).toBe('No brief yet')
    expect(wrapper.find('.brief-line').exists()).toBe(false)
    leakless(wrapper.find('.notice').text())
  })
})
