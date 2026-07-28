import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import App from '@/App.vue'
import * as apa from './fixtures/apa.js'

/*
 * The whole public flow, end to end: build a feasible brief, press Generate,
 * and have the generation come back refused with a quoted wait. These tests
 * prove the refusal's wait is carried back to the still-mounted brief editor —
 * the one path where the timing was known on the results screen but discarded.
 */

const jsonValue = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: () => Promise.resolve(data)
})
const json = (data, status = 200) => Promise.resolve(jsonValue(data, status))

/* A recording fetch stub for the full flow: style load, feasible automatic
 * checks, and a generation answer chosen per test. Every call is logged so a
 * test can prove no compute request escaped during the cooldown. */
function installFetch (recipes) {
  const calls = []
  global.fetch = vi.fn((url, init = {}) => {
    const path = String(url).replace(/^https?:\/\/[^/]+/, '')
    const method = (init.method || 'GET').toUpperCase()
    const body = init.body ? JSON.parse(init.body) : null
    calls.push({ path, method, body })
    if (method === 'GET' && path === '/api/v1/styles') return json(apa.styles)
    if (method === 'GET' && path.startsWith('/api/v1/styles/')) return json(apa.style)
    if (path === '/api/v1/grains/sensory-range') return json(apa.sensoryRange(body.descriptor))
    if (path === '/api/v1/grains/feasibility') return json(apa.feasibility)
    if (path === '/api/v1/grains/recipes') return recipes()
    return json({}, 404)
  })
  return { calls }
}

async function mountReadyToGenerate () {
  const wrapper = mount(App, { attachTo: document.body })
  await flushPromises() // styles list + style detail
  return wrapper
}

const briefFeas = (w) => w.find('.brief-screen .feas')
const briefGenerate = (w) => w.find('.brief-screen .generate')
const computeCalls = (calls) => calls.filter((c) => c.path.startsWith('/api/v1/grains/'))

beforeEach(() => { vi.restoreAllMocks(); vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers(); delete global.fetch })

describe('generation refusal carries its wait back to the brief editor', () => {
  it('holds the brief editor for the quoted wait, burns the clock while results are read, and never restarts it', async () => {
    const { calls } = installFetch(
      () => json({ status: 429, outcome: 'rate_limited', retry_after: 10 }, 429))
    const wrapper = await mountReadyToGenerate()

    // Style data alone makes Generate live; initial load spends no compute.
    expect(computeCalls(calls)).toHaveLength(0)
    expect(briefGenerate(wrapper).attributes('disabled')).toBeUndefined()

    // Generate → results screen → refused, quoting a ten-second wait.
    await briefGenerate(wrapper).trigger('click')
    await flushPromises()
    expect(wrapper.find('.results-screen').exists()).toBe(true)

    // The still-mounted brief editor is now counting down that same wait, and
    // Generate is held even though the brief itself is still feasible.
    expect(briefFeas(wrapper).text()).toMatch(/edit again in 10 seconds/)
    expect(briefGenerate(wrapper).attributes('disabled')).toBeDefined()

    // Four seconds spent reading results come off the wait…
    await vi.advanceTimersByTimeAsync(4000)
    await flushPromises()
    // …and returning to the brief shows only the remainder — never a fresh ten.
    await wrapper.find('.results-screen .edit-brief').trigger('click')
    await flushPromises()
    expect(briefFeas(wrapper).text()).toMatch(/edit again in 6 seconds/)

    // Editing during the wait changes the preserved brief but sends no compute.
    calls.length = 0
    const abv = wrapper.find('#abv')
    abv.element.value = '5.7'
    await abv.trigger('input')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await wrapper.findAll('.flavor-row')[0].findAll('.step')[3].trigger('click')
    await flushPromises()
    expect(computeCalls(calls)).toHaveLength(0)
    expect(wrapper.find('#abv').element.value).toBe('5.7')
    expect(briefGenerate(wrapper).attributes('disabled')).toBeDefined()

    // Once the wait elapses Generate is eligible again (brief still feasible),
    // and only the next intentional edit resumes automatic checks.
    await vi.advanceTimersByTimeAsync(6000)
    await flushPromises()
    expect(briefGenerate(wrapper).attributes('disabled')).toBeUndefined()
    calls.length = 0
    const srm = wrapper.find('#srm')
    srm.element.value = String(Number(srm.element.value) + 1)
    await srm.trigger('input')
    await vi.advanceTimersByTimeAsync(59999)
    expect(calls.filter((c) => c.path === '/api/v1/grains/feasibility')).toHaveLength(0)
    await vi.advanceTimersByTimeAsync(1)
    await flushPromises()
    expect(calls.filter((c) => c.path === '/api/v1/grains/feasibility').length)
      .toBeGreaterThan(0)

    wrapper.unmount()
  })

  it('a busy generation refusal starts the one-second cooldown and holds Generate', async () => {
    installFetch(() => json({ status: 503, outcome: 'busy', retry_after: 1 }, 503))
    const wrapper = await mountReadyToGenerate()

    await briefGenerate(wrapper).trigger('click')
    await flushPromises()

    expect(briefFeas(wrapper).text()).toMatch(/try again in 1 second/)
    expect(briefGenerate(wrapper).attributes('disabled')).toBeDefined()

    wrapper.unmount()
  })
})
