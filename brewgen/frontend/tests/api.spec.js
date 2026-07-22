import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { fetchRecipes, fetchFeasibility, fetchSensoryRange } from '@/api.js'

/*
 * The compute endpoints answer failures with application/problem+json carrying a
 * machine `outcome` tag. These tests pin the fetch layer's job: a limit or an
 * overload must be surfaced as its honest outcome, never mistaken for solver
 * data and never leaked as a raw status code.
 */

/* A minimal problem+json / json response, as the browser Response would parse. */
function respond (status, body) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': status === 200 ? 'application/json' : 'application/problem+json' }
  }))
}

beforeEach(() => { vi.restoreAllMocks() })
afterEach(() => { vi.unstubAllGlobals() })

describe('fetchRecipes outcome mapping', () => {
  const cases = [
    ['busy', 503, 'busy', 'busy'],
    ['rate-limited', 429, 'rate_limited', 'rate_limited'],
    ['infeasible', 422, 'infeasible', 'infeasible'],
    ['deadline', 503, 'deadline', 'deadline'],
    ['oversized collapses to malformed', 413, 'oversized', 'malformed'],
    ['invalid collapses to malformed', 422, 'invalid', 'malformed']
  ]
  for (const [label, status, tag, expected] of cases) {
    it(`maps a ${label} response to the ${expected} shelf outcome`, async () => {
      vi.stubGlobal('fetch', vi.fn(() => respond(status, { title: 'x', status, outcome: tag })))
      const result = await fetchRecipes({})
      expect(result).toEqual({ outcome: expected })
    })
  }

  it('returns the solver body unchanged on a 200', async () => {
    const body = { status: 'complete', alternatives: [{ grains: [] }] }
    vi.stubGlobal('fetch', vi.fn(() => respond(200, body)))
    expect(await fetchRecipes({})).toEqual(body)
  })

  it('reports malformed when the network request throws', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('offline'))))
    expect(await fetchRecipes({})).toEqual({ outcome: 'malformed' })
  })
})

describe('focused endpoints surface limits honestly', () => {
  it('passes a feasible range through untouched', async () => {
    const body = { status: 'feasible', name: 'bready', min: 0.1, max: 2.6 }
    vi.stubGlobal('fetch', vi.fn(() => respond(200, body)))
    expect(await fetchSensoryRange({ descriptor: 'bready' })).toEqual(body)
  })

  it('reduces a busy feasibility check to a status the editor can read', async () => {
    vi.stubGlobal('fetch', vi.fn(() => respond(503, { title: 'x', status: 503, outcome: 'busy' })))
    expect(await fetchFeasibility({})).toEqual({ status: 'busy' })
  })

  it('reduces a rate-limited feasibility check to a status the editor can read', async () => {
    vi.stubGlobal('fetch', vi.fn(() => respond(429, { title: 'x', status: 429, outcome: 'rate_limited' })))
    expect(await fetchFeasibility({})).toEqual({ status: 'rate_limited' })
  })

  it('never reports feasible from a problem+json failure body', async () => {
    vi.stubGlobal('fetch', vi.fn(() => respond(422, { title: 'x', status: 422, outcome: 'infeasible' })))
    const result = await fetchFeasibility({})
    expect(result.status).not.toBe('feasible')
    expect(result).toEqual({ status: 'infeasible' })
  })
})
