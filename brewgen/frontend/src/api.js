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
