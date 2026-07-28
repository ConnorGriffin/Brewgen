import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import BriefEditor from '@/components/BriefEditor.vue'
import * as apa from './fixtures/apa.js'

const QUIET_MS = 60000

const jsonValue = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: () => Promise.resolve(data)
})
const json = (data, status = 200) => Promise.resolve(jsonValue(data, status))

/*
 * Public HTTP recorder for the rendered editor. Feasibility can be deferred so
 * tests can resolve old and new answers out of order; focused ranges can be
 * narrowed so invalidation is visible through the row's reachable-step classes.
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
      const answer = opts.rangeAnswer
        ? opts.rangeAnswer(body.descriptor)
        : apa.sensoryRange(body.descriptor)
      return json(answer)
    }
    if (method === 'POST' && path === '/api/v1/grains/feasibility') {
      if (opts.deferFeasibility) {
        return new Promise((resolve) => {
          feasQueue.push((status) => resolve(jsonValue({ status })))
        })
      }
      if (opts.feasibilityResponse) return opts.feasibilityResponse()
      return json(apa.feasibility)
    }
    return json({}, 404)
  })
  return { calls, feasQueue }
}

async function mountLoaded () {
  const wrapper = mount(BriefEditor)
  await flushPromises() // styles list + style detail
  return wrapper
}

const paths = (calls, path) => calls.filter((call) => call.path === path)
const computeCalls = (calls) => calls.filter((call) =>
  call.path.startsWith('/api/v1/grains/'))

async function setRange (wrapper, selector, value) {
  const input = wrapper.find(selector)
  input.element.value = String(value)
  await input.trigger('input')
  await flushPromises()
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.useFakeTimers()
})
afterEach(() => {
  vi.useRealTimers()
  delete global.fetch
})

describe('public brief editor compute policy', () => {
  it('loads silently, enables Generate from style data, and emits one current version-one brief', async () => {
    const { calls } = installFetch()
    const wrapper = await mountLoaded()

    expect(computeCalls(calls)).toHaveLength(0)
    expect(wrapper.find('.generate').attributes('disabled')).toBeUndefined()

    await wrapper.find('.generate').trigger('click')
    expect(wrapper.emitted('generate')).toHaveLength(1)
    const generated = wrapper.emitted('generate')[0][0].payload
    const expectedKeys = [
      'color_srm', 'equipment', 'fermentables', 'sensory', 'style', 'version'
    ]
    expect(Object.keys(generated).sort()).toEqual(expectedKeys)
    expect(generated.version).toBe(1)
    expect(Object.keys(generated.style).sort()).toEqual(
      ['original_gravity', 'slug'])
    expect(Object.keys(generated.equipment).sort()).toEqual(
      ['batch_volume_gallons', 'mash_efficiency_percent'])
    expect(Object.keys(generated.fermentables).sort()).toEqual(
      ['allowed_slugs', 'bounds', 'maximum_count'])

    await setRange(wrapper, '#abv', 5.1)
    await vi.advanceTimersByTimeAsync(QUIET_MS)
    await flushPromises()
    const feasibility = paths(calls, '/api/v1/grains/feasibility').at(-1)
    expect(Object.keys(feasibility.body).sort()).toEqual(expectedKeys)
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

    const selected = wrapper.findAll('.flavor-row')[0].findAll('.step').find(
      (step) => step.attributes('aria-checked') === 'true')
    await selected.trigger('click')
    await flushPromises()
    const range = paths(calls, '/api/v1/grains/sensory-range').at(-1)
    expect(Object.keys(range.body).sort()).toEqual(
      [...expectedKeys, 'descriptor'].sort())
    expect(range.body.descriptor).toBe('malty')

    expect(JSON.stringify([generated, feasibility.body, range.body])).not.toMatch(
      /fermentable_list|category_model|sensory_model|max_unique_fermentables|equipment_profile|beer_profile/)

    wrapper.unmount()
  })

  it('seeds the locked style flavors and keeps the SRM gradient clipped to its range', async () => {
    installFetch()
    const wrapper = await mountLoaded()

    expect(wrapper.findAll('.flavor-name').map((node) => node.text()))
      .toEqual(['malty', 'bready', 'caramel'])

    const track = wrapper.find('.srm-track').attributes('style')
    expect(track).toContain('linear-gradient')
    expect(track).toContain('#fbb123') // 5 SRM
    expect(track).toContain('#c35900') // 14 SRM
    expect(track).not.toContain('#ffe699') // below the style's range

    wrapper.unmount()
  })

  it('waits for exactly 60 seconds of quiet, restarts on edits, and ignores no-op input', async () => {
    const { calls } = installFetch()
    const wrapper = await mountLoaded()
    calls.length = 0

    const initialAbv = wrapper.find('#abv').element.value
    await setRange(wrapper, '#abv', initialAbv) // same value: no real edit
    await vi.advanceTimersByTimeAsync(QUIET_MS)
    expect(paths(calls, '/api/v1/grains/feasibility')).toHaveLength(0)

    await setRange(wrapper, '#abv', 5.0)
    await vi.advanceTimersByTimeAsync(QUIET_MS - 1)
    expect(paths(calls, '/api/v1/grains/feasibility')).toHaveLength(0)

    await setRange(wrapper, '#abv', 5.1) // restart the trailing clock
    await vi.advanceTimersByTimeAsync(QUIET_MS - 1)
    expect(paths(calls, '/api/v1/grains/feasibility')).toHaveLength(0)
    await vi.advanceTimersByTimeAsync(1)
    await flushPromises()

    const previews = paths(calls, '/api/v1/grains/feasibility')
    expect(previews).toHaveLength(1)
    expect(previews[0].body.style.original_gravity).toBeGreaterThan(1)

    await setRange(wrapper, '#abv', 5.1) // unchanged brief never resubmits
    await vi.advanceTimersByTimeAsync(QUIET_MS)
    expect(paths(calls, '/api/v1/grains/feasibility')).toHaveLength(1)

    wrapper.unmount()
  })

  it('Generate cancels a queued or active preview and no hidden preview appears later', async () => {
    const { calls, feasQueue } = installFetch({ deferFeasibility: true })
    const wrapper = await mountLoaded()

    await setRange(wrapper, '#abv', 5.0)
    await vi.advanceTimersByTimeAsync(QUIET_MS - 1)
    await wrapper.find('.generate').trigger('click')
    await vi.advanceTimersByTimeAsync(QUIET_MS + 1)
    expect(paths(calls, '/api/v1/grains/feasibility')).toHaveLength(0)
    expect(wrapper.emitted('generate')).toHaveLength(1)

    await setRange(wrapper, '#abv', 5.1)
    await vi.advanceTimersByTimeAsync(QUIET_MS)
    expect(paths(calls, '/api/v1/grains/feasibility')).toHaveLength(1)
    expect(feasQueue).toHaveLength(1)

    await wrapper.find('.generate').trigger('click')
    expect(wrapper.emitted('generate')).toHaveLength(2)
    feasQueue[0]('infeasible') // an aborted stub may still resolve; it must lose
    await flushPromises()
    await vi.advanceTimersByTimeAsync(QUIET_MS * 2)

    expect(wrapper.find('.feas').text()).not.toContain('No grain bill')
    expect(paths(calls, '/api/v1/grains/feasibility')).toHaveLength(1)

    wrapper.unmount()
  })

  it('reuses a flavor range across its own level changes and lazily refreshes stale hints', async () => {
    const { calls } = installFetch({
      rangeAnswer: (descriptor) => ({
        status: 'feasible', name: descriptor, min: 1.5, max: 1.5
      })
    })
    const wrapper = await mountLoaded()
    calls.length = 0

    const malty = () => wrapper.findAll('.flavor-row')[0]
    const selected = malty().findAll('.step').find(
      (step) => step.attributes('aria-checked') === 'true')

    // A no-op click is still the first real engagement and fetches one hint.
    await selected.trigger('click')
    await flushPromises()
    expect(paths(calls, '/api/v1/grains/sensory-range')).toHaveLength(1)
    expect(malty().findAll('.unreachable').length).toBeGreaterThan(0)

    // Only the target's own bound changes; the server ignores it for this range.
    await malty().findAll('.step')[1].trigger('click')
    await malty().findAll('.step')[2].trigger('click')
    await flushPromises()
    expect(paths(calls, '/api/v1/grains/sensory-range')).toHaveLength(1)

    // Strength genuinely changes every range, so exact hints clear immediately
    // without a fan-out; engaging malty later refreshes only malty.
    await setRange(wrapper, '#abv', 5.7)
    expect(malty().findAll('.unreachable')).toHaveLength(0)
    expect(paths(calls, '/api/v1/grains/sensory-range')).toHaveLength(1)

    await malty().findAll('.step')[3].trigger('click')
    await flushPromises()
    const ranges = paths(calls, '/api/v1/grains/sensory-range')
    expect(ranges).toHaveLength(2)
    expect(ranges.map((call) => call.body.descriptor)).toEqual(['malty', 'malty'])
    expect(paths(calls, '/api/v1/grains/sensory-profiles')).toHaveLength(0)

    wrapper.unmount()
  })

  it('adding one flavor requests only that descriptor and invalidates no row eagerly', async () => {
    const { calls } = installFetch()
    const wrapper = await mountLoaded()
    calls.length = 0

    const toast = wrapper.findAll('.sugg').find((button) => button.text() === 'toast')
    await toast.trigger('click')
    await flushPromises()

    const ranges = paths(calls, '/api/v1/grains/sensory-range')
    expect(ranges).toHaveLength(1)
    expect(ranges[0].body.descriptor).toBe('toast')
    expect(paths(calls, '/api/v1/grains/sensory-profiles')).toHaveLength(0)

    await wrapper.findAll('.sugg')[0].trigger('click')
    await flushPromises()
    expect(wrapper.findAll('.flavor-row')).toHaveLength(5)
    expect(wrapper.find('.flavor-search').exists()).toBe(false)
    expect(wrapper.find('.max-note').exists()).toBe(true)

    wrapper.unmount()
  })

  it('drops an old active preview when a later brief wins', async () => {
    const { feasQueue } = installFetch({ deferFeasibility: true })
    const wrapper = await mountLoaded()

    await setRange(wrapper, '#abv', 5.0)
    await vi.advanceTimersByTimeAsync(QUIET_MS)
    expect(feasQueue).toHaveLength(1)

    await setRange(wrapper, '#abv', 6.0) // abort/drop first, queue latest
    await vi.advanceTimersByTimeAsync(QUIET_MS)
    expect(feasQueue).toHaveLength(2)

    feasQueue[1]('feasible')
    await flushPromises()
    feasQueue[0]('infeasible')
    await flushPromises()

    expect(wrapper.find('.feas').classes()).toContain('ok')
    expect(wrapper.find('.feas').text()).toContain('can meet this brief')

    wrapper.unmount()
  })

  it('keeps every preview outcome advisory rather than gating Generate', async () => {
    const { calls } = installFetch({
      feasibilityResponse: () => json({ status: 'infeasible' })
    })
    const wrapper = await mountLoaded()

    await setRange(wrapper, '#srm', 12)
    await vi.advanceTimersByTimeAsync(QUIET_MS)
    await flushPromises()

    expect(paths(calls, '/api/v1/grains/feasibility')).toHaveLength(1)
    expect(wrapper.find('.feas').classes()).toContain('no')
    expect(wrapper.find('.feas').text()).toContain('No grain bill fits this brief')
    expect(wrapper.find('.feas').text()).not.toMatch(/infeasible|solver|400|status/i)
    expect(wrapper.find('.generate').attributes('disabled')).toBeUndefined()

    wrapper.unmount()
  })

  it('preserves cooldown suppression and resumes only after expiry plus a later edit', async () => {
    const { calls } = installFetch({
      feasibilityResponse: () =>
        json({ status: 503, outcome: 'busy', retry_after: 3 }, 503)
    })
    const wrapper = await mountLoaded()

    await setRange(wrapper, '#abv', 5.0)
    await vi.advanceTimersByTimeAsync(QUIET_MS)
    await flushPromises()
    expect(wrapper.find('.feas').text()).toMatch(/try again in 3 seconds/)
    expect(wrapper.find('.generate').attributes('disabled')).toBeDefined()

    calls.length = 0
    await setRange(wrapper, '#abv', 5.7)
    await wrapper.findAll('.flavor-row')[0].findAll('.step')[3].trigger('click')
    await vi.advanceTimersByTimeAsync(QUIET_MS)
    expect(computeCalls(calls)).toHaveLength(0)
    expect(wrapper.find('#abv').element.value).toBe('5.7')

    await vi.advanceTimersByTimeAsync(3000)
    expect(wrapper.find('.generate').attributes('disabled')).toBeUndefined()
    expect(computeCalls(calls)).toHaveLength(0)

    await setRange(wrapper, '#srm', 12)
    await vi.advanceTimersByTimeAsync(QUIET_MS - 1)
    expect(paths(calls, '/api/v1/grains/feasibility')).toHaveLength(0)
    await vi.advanceTimersByTimeAsync(1)
    await flushPromises()
    expect(paths(calls, '/api/v1/grains/feasibility')).toHaveLength(1)

    wrapper.unmount()
  })

  it('a focused-range refusal cancels the queued preview for the whole cooldown', async () => {
    const calls = []
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
    const wrapper = await mountLoaded()
    calls.length = 0

    await wrapper.findAll('.flavor-row')[0].findAll('.step')[3].trigger('click')
    await flushPromises()
    expect(wrapper.find('.feas').text()).toMatch(/10 seconds/)

    await vi.advanceTimersByTimeAsync(QUIET_MS)
    expect(paths(calls, '/api/v1/grains/feasibility')).toHaveLength(0)

    wrapper.unmount()
  })
})
