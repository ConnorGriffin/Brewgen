import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import BriefEditor from '@/components/BriefEditor.vue'
import * as apa from './fixtures/apa.js'

const wait = (ms) => new Promise((r) => setTimeout(r, ms))

/*
 * A recording fetch stub. Every request is logged so a test can prove which
 * endpoints the screen touched. Feasibility responses can be deferred and
 * resolved out of order to exercise the stale-response guard.
 */
function installFetch (opts = {}) {
  const calls = []
  const feasQueue = []
  global.fetch = vi.fn((url, init = {}) => {
    const path = String(url).replace(/^https?:\/\/[^/]+/, '')
    const method = (init.method || 'GET').toUpperCase()
    const body = init.body ? JSON.parse(init.body) : null
    calls.push({ path, method, body })

    if (method === 'GET' && path === '/api/v1/styles') return json(apa.styles)
    if (method === 'GET' && path.startsWith('/api/v1/styles/')) return json(apa.style)
    if (method === 'POST' && path === '/api/v1/grains/sensory-range') {
      return json(apa.sensoryRange(body.descriptor))
    }
    if (method === 'POST' && path === '/api/v1/grains/feasibility') {
      if (opts.deferFeasibility) {
        return new Promise((resolve) => {
          feasQueue.push((status) => resolve(jsonValue({ status })))
        })
      }
      return json(apa.feasibility)
    }
    return json({}, 404)
  })
  return { calls, feasQueue }
}

const jsonValue = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: () => Promise.resolve(data)
})
const json = (data, status = 200) => Promise.resolve(jsonValue(data, status))

async function mountLoaded () {
  const wrapper = mount(BriefEditor)
  await flushPromises() // styles list + style detail
  await wait(350) // initial debounced feasibility
  await flushPromises()
  return wrapper
}

const paths = (calls, path) => calls.filter((c) => c.path === path)

beforeEach(() => { vi.restoreAllMocks() })
afterEach(() => { delete global.fetch })

describe('public brief editor', () => {
  it('sends only the version-one choice brief for range, feasibility, and generation', async () => {
    const { calls } = installFetch()
    const wrapper = await mountLoaded()

    const expectedKeys = [
      'color_srm', 'equipment', 'fermentables', 'sensory', 'style', 'version'
    ]
    const feasibility = paths(calls, '/api/v1/grains/feasibility').at(-1)
    expect(Object.keys(feasibility.body).sort()).toEqual(expectedKeys)
    expect(feasibility.body.version).toBe(1)
    expect(Object.keys(feasibility.body.style).sort()).toEqual(
      ['original_gravity', 'slug'])
    expect(Object.keys(feasibility.body.equipment).sort()).toEqual(
      ['batch_volume_gallons', 'mash_efficiency_percent'])
    expect(Object.keys(feasibility.body.fermentables).sort()).toEqual(
      ['allowed_slugs', 'bounds', 'maximum_count'])
    expect(Object.keys(feasibility.body.fermentables.bounds[0]).sort()).toEqual(
      ['maximum_percent', 'minimum_percent', 'slug'])
    expect(Object.keys(feasibility.body.sensory[0]).sort()).toEqual(
      ['maximum', 'minimum', 'name'])
    expect(Object.keys(feasibility.body.color_srm).sort()).toEqual(
      ['maximum', 'minimum'])
    expect(feasibility.body.fermentables.bounds.every(
      (bound) => Number.isInteger(bound.minimum_percent) &&
        Number.isInteger(bound.maximum_percent)
    )).toBe(true)

    await wrapper.find('.generate').trigger('click')
    const generated = wrapper.emitted('generate').at(-1)[0].payload
    expect(Object.keys(generated).sort()).toEqual(expectedKeys)

    calls.length = 0
    await wrapper.findAll('.flavor-row')[0].findAll('.step')[3].trigger('click')
    await flushPromises()
    const range = paths(calls, '/api/v1/grains/sensory-range')[0]
    expect(Object.keys(range.body).sort()).toEqual(
      [...expectedKeys, 'descriptor'].sort())
    expect(range.body.descriptor).toBe('malty')

    const serialized = JSON.stringify([feasibility.body, generated, range.body])
    expect(serialized).not.toMatch(
      /fermentable_list|category_model|sensory_model|max_unique_fermentables|equipment_profile|beer_profile/)
  })

  it('seeds style-mentioned flavors and renders the SRM gradient clipped to the style range', async () => {
    installFetch()
    const wrapper = await mountLoaded()

    const names = wrapper.findAll('.flavor-name').map((n) => n.text())
    expect(names).toEqual(['malty', 'bready', 'caramel']) // the BJCP-mentioned set

    const track = wrapper.find('.srm-track').attributes('style')
    // Clipped to [5,14]: gold-through-copper stops, not the full 1..40 chart.
    expect(track).toContain('linear-gradient')
    expect(track).toContain('#fbb123') // 5 SRM
    expect(track).toContain('#c35900') // 14 SRM
    expect(track).not.toContain('#ffe699') // 1 SRM — below the clip
  })

  it('a single flavor edit fires exactly one focused range request and never the all-descriptor sweep', async () => {
    const { calls } = installFetch()
    const wrapper = await mountLoaded()
    calls.length = 0 // ignore load traffic; measure only the edit

    // Click "bold" on the first flavor row (malty).
    await wrapper.findAll('.flavor-row')[0].findAll('.step')[3].trigger('click')
    await flushPromises()

    const range = paths(calls, '/api/v1/grains/sensory-range')
    expect(range).toHaveLength(1) // one flavor, one request — no 48-range fan-out
    expect(range[0].body.descriptor).toBe('malty')

    // The forbidden plural path is never touched, here or anywhere.
    expect(paths(calls, '/api/v1/grains/sensory-profiles')).toHaveLength(0)
    expect(calls.every((c) => !c.path.includes('sensory-profiles'))).toBe(true)
  })

  it('adding a flavor asks only for that one descriptor and enforces the five-row cap', async () => {
    const { calls } = installFetch()
    const wrapper = await mountLoaded()
    calls.length = 0

    // Add "toast" via a suggestion button.
    const suggByName = () => wrapper.findAll('.sugg').find((b) => b.text() === 'toast')
    await suggByName().trigger('click')
    await flushPromises()

    const range = paths(calls, '/api/v1/grains/sensory-range')
    expect(range).toHaveLength(1)
    expect(range[0].body.descriptor).toBe('toast')

    // Seeded 3 + toast = 4; add one more to hit the cap of 5.
    await wrapper.findAll('.sugg')[0].trigger('click')
    await flushPromises()
    expect(wrapper.findAll('.flavor-row')).toHaveLength(5)
    // At the cap the add control disappears and the limit note shows.
    expect(wrapper.find('.flavor-search').exists()).toBe(false)
    expect(wrapper.find('.max-note').exists()).toBe(true)
  })

  it('discards a stale feasibility response so it cannot overwrite newer state', async () => {
    const { feasQueue } = installFetch({ deferFeasibility: true })
    const wrapper = await mountLoaded() // initial feasibility now pending in the queue

    // First edit dispatches another feasibility request (kept pending).
    const abv = wrapper.find('#abv')
    abv.element.value = '5.0'
    await abv.trigger('input')
    await wait(350)
    await flushPromises()

    // Second edit dispatches the newest feasibility request (kept pending).
    abv.element.value = '6.0'
    await abv.trigger('input')
    await wait(350)
    await flushPromises()

    // Several requests are now in flight; the last enqueued is the newest brief.
    expect(feasQueue.length).toBeGreaterThanOrEqual(2)
    // The newest resolves first as feasible…
    feasQueue[feasQueue.length - 1]('feasible')
    await flushPromises()
    // …then an older, stale request resolves infeasible and must be ignored.
    feasQueue[0]('infeasible')
    await flushPromises()

    expect(wrapper.find('.feas').classes()).toContain('ok')
    expect(wrapper.find('.feas').text()).toContain('can meet this brief')
  })

  it('honors the retry cooldown: no compute until it expires, brief preserved, then an intentional edit resumes', async () => {
    vi.useFakeTimers()
    const calls = []
    // Feasibility answers busy with a three-second retry; ranges answer feasible.
    global.fetch = vi.fn((url, init = {}) => {
      const path = String(url).replace(/^https?:\/\/[^/]+/, '')
      const method = (init.method || 'GET').toUpperCase()
      const body = init.body ? JSON.parse(init.body) : null
      calls.push({ path, method, body })
      if (method === 'GET' && path === '/api/v1/styles') return json(apa.styles)
      if (method === 'GET' && path.startsWith('/api/v1/styles/')) return json(apa.style)
      if (path === '/api/v1/grains/sensory-range') return json(apa.sensoryRange(body.descriptor))
      if (path === '/api/v1/grains/feasibility') {
        return json({ status: 503, outcome: 'busy', retry_after: 3 }, 503)
      }
      return json({}, 404)
    })

    const wrapper = mount(BriefEditor)
    await flushPromises() // styles + style detail
    await vi.advanceTimersByTimeAsync(300) // debounced feasibility fires
    await flushPromises()

    // The busy answer put the editor into a countdown.
    expect(wrapper.find('.feas').text()).toMatch(/try again in 3 seconds/)
    const flavorsBefore = wrapper.findAll('.flavor-row').length
    expect(flavorsBefore).toBeGreaterThan(0)

    calls.length = 0 // measure only what happens during the cooldown

    // Editing during cooldown updates the brief but fires no compute request.
    const abv = wrapper.find('#abv')
    abv.element.value = '5.7'
    await abv.trigger('input')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await wrapper.findAll('.flavor-row')[0].findAll('.step')[3].trigger('click')
    await flushPromises()

    const computePaths = calls.filter((c) => c.path.startsWith('/api/v1/grains/'))
    expect(computePaths).toHaveLength(0) // no hidden retry before the stated time
    // The brief survived the cooldown: same flavor rows, the edited strength kept.
    expect(wrapper.findAll('.flavor-row')).toHaveLength(flavorsBefore)
    expect(wrapper.find('#abv').element.value).toBe('5.7')

    // Let the countdown elapse, then an intentional edit resumes compute.
    await vi.advanceTimersByTimeAsync(3000)
    await flushPromises()
    calls.length = 0
    const srm = wrapper.find('#srm')
    srm.element.value = String(Number(srm.element.value) + 1)
    await srm.trigger('input')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    expect(calls.filter((c) => c.path === '/api/v1/grains/feasibility').length)
      .toBeGreaterThan(0)

    vi.useRealTimers()
  })

  it('cancels an already-queued check when a flavour edit is the thing that hits the limit', async () => {
    vi.useFakeTimers()
    const calls = []
    // The focused range refuses; the whole-brief check would happily answer. A
    // single flavour edit fires both, so the refusal has to stop the queued one.
    global.fetch = vi.fn((url, init = {}) => {
      const path = String(url).replace(/^https?:\/\/[^/]+/, '')
      const method = (init.method || 'GET').toUpperCase()
      calls.push({ path, method })
      if (method === 'GET' && path === '/api/v1/styles') return json(apa.styles)
      if (method === 'GET' && path.startsWith('/api/v1/styles/')) return json(apa.style)
      if (path === '/api/v1/grains/sensory-range') {
        return json({ status: 429, outcome: 'rate_limited', retry_after: 10 }, 429)
      }
      if (path === '/api/v1/grains/feasibility') return json(apa.feasibility)
      return json({}, 404)
    })

    const wrapper = mount(BriefEditor)
    await flushPromises()
    await vi.advanceTimersByTimeAsync(300) // the initial debounced check answers
    await flushPromises()
    calls.length = 0

    // One flavour edit: the focused range goes out immediately and comes back
    // rate-limited, while the whole-brief check sits on its 300 ms debounce.
    await wrapper.findAll('.flavor-row')[0].findAll('.step')[3].trigger('click')
    await flushPromises()
    expect(wrapper.find('.feas').text()).toMatch(/10 seconds/)

    await vi.advanceTimersByTimeAsync(300) // the debounce would have fired here
    await flushPromises()
    expect(calls.filter((c) => c.path === '/api/v1/grains/feasibility')).toHaveLength(0)

    vi.useRealTimers()
  })

  it('shows the locked infeasible voice without leaking solver internals', async () => {
    installFetch()
    global.fetch = vi.fn((url, init = {}) => {
      const path = String(url).replace(/^https?:\/\/[^/]+/, '')
      const method = (init.method || 'GET').toUpperCase()
      if (method === 'GET' && path === '/api/v1/styles') return json(apa.styles)
      if (method === 'GET' && path.startsWith('/api/v1/styles/')) return json(apa.style)
      if (path === '/api/v1/grains/sensory-range') {
        return json({ status: 'infeasible', name: JSON.parse(init.body).descriptor })
      }
      return json({ status: 'infeasible' })
    })
    const wrapper = await mountLoaded()

    const feas = wrapper.find('.feas')
    expect(feas.classes()).toContain('no')
    expect(feas.text()).toContain('No grain bill fits this brief')
    // No status codes, endpoint names, or solver jargon leak into the copy.
    expect(feas.text()).not.toMatch(/infeasible|solver|400|status/i)
  })
})
