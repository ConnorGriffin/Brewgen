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
