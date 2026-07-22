/*
 * The public brief editor's only channel to the backend. It talks to exactly
 * three read endpoints and the two focused #36 solver endpoints:
 *   - GET  /api/v1/styles                 style list for the dropdown
 *   - GET  /api/v1/styles/:slug           one style's seed data
 *   - POST /api/v1/grains/sensory-range   ONE descriptor's conditional range
 *   - POST /api/v1/grains/feasibility     whole-brief feasibility
 * It deliberately has no reference to the retired all-descriptor
 * `/api/v1/grains/sensory-profiles` sweep — that fan-out must never be reached
 * from this screen.
 */

const BASE =
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE) || ''

async function getJson (path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`)
  return res.json()
}

/*
 * The public compute endpoints answer failures with `application/problem+json`
 * carrying a stable machine `outcome` tag (oversized, invalid, infeasible,
 * rate_limited, busy, deadline, …). Turn any response into that outcome tag so
 * a limit or overload is never mistaken for solver data. Falls back to the
 * status code when the body is unreadable.
 */
async function readOutcome (res) {
  let body = {}
  try { body = await res.json() } catch { body = {} }
  if (res.ok) return { ok: true, body }
  if (body && body.outcome) return { ok: false, outcome: body.outcome }
  if (res.status === 429) return { ok: false, outcome: 'rate_limited' }
  if (res.status === 503) return { ok: false, outcome: 'busy' }
  return { ok: false, outcome: 'invalid' }
}

async function postJson (path, body, signal) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal
  })
  // A 200 carries the solver body ({status:"feasible", …}); a failure is
  // reduced to {status:"<outcome>"} so callers surface a limit/overload
  // honestly instead of treating the problem+json body as solver data.
  const r = await readOutcome(res)
  return r.ok ? r.body : { status: r.outcome }
}

export const listStyles = () => getJson('/api/v1/styles')

export const getStyle = (slug) => getJson(`/api/v1/styles/${slug}`)

/* One descriptor, one request — the focused replacement for the 48-range sweep. */
export function fetchSensoryRange (payload, signal) {
  return postJson('/api/v1/grains/sensory-range', payload, signal)
}

export function fetchFeasibility (payload, signal) {
  return postJson('/api/v1/grains/feasibility', payload, signal)
}

/* Map a compute failure's machine outcome tag onto the shelf's own outcome
 * vocabulary: a transient limit/overload gets its honest notice; everything
 * else (oversized, wrong media, unreadable) collapses to the stable malformed
 * notice so no status code or endpoint name is ever leaked. */
const SHELF_OUTCOME = {
  infeasible: 'infeasible',
  deadline: 'deadline',
  rate_limited: 'rate_limited',
  busy: 'busy'
}

/*
 * Generation for the results shelf. A 200 returns the solver body unchanged; a
 * failure is reduced to {outcome:"<shelf-state>"} so the shelf renders the
 * matching quiet notice — busy and rate-limited included — without leaking a
 * status code or endpoint name.
 */
export async function fetchRecipes (payload, signal) {
  let res
  try {
    res = await fetch(`${BASE}/api/v1/grains/recipes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal
    })
  } catch {
    return { outcome: 'malformed' }
  }
  const r = await readOutcome(res)
  if (r.ok) return r.body
  return { outcome: SHELF_OUTCOME[r.outcome] || 'malformed' }
}
