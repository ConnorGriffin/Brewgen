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

async function postJson (path, body, signal) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal
  })
  // The focused endpoints answer 400 with a stable {status:"invalid"} body for
  // malformed briefs; surface that as data rather than throwing.
  return res.json()
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

/*
 * Generation for the results shelf. A 200 carries the solver status
 * (complete/partial) and the bills. A failure answers application/problem+json
 * with a stable machine code; we surface that code as {error:true, code} so the
 * shelf can map it to the locked notice for that outcome, without ever leaking
 * the HTTP status or an endpoint name.
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
    return { error: true }
  }
  let body = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (res.ok) return body || { error: true }
  return { error: true, code: (body && body.code) || null }
}
