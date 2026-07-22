/*
 * Generate the issue #39 screenshot set via the canonical harness
 * (scripts/screenshots.mjs). Proves the two new public-compute outcome notices
 * — "busy" (a 503 from the two-slot ceiling) and "rate-limited" (a 429 from the
 * per-visitor budget) — render in the locked #42 single-notice treatment, in
 * both light and dark themes. Usage:
 *   cd brewgen/frontend && npm run build:offline
 *   node scripts/gen-issue-39-shots.mjs <out-dir>
 * Each PNG lands in <out-dir>; embed them in the PR from the immutable commit
 * that adds them.
 */
import { writeFileSync } from 'node:fs'
import { join, resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { tmpdir } from 'node:os'
import { execFileSync } from 'node:child_process'
import * as apa from '../brewgen/frontend/tests/fixtures/apa.js'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const outDir = resolve(process.argv[2] || 'docs/screenshots/issue-39/local')
const indexUrl = 'file://' + join(repoRoot, 'brewgen/frontend/offline/index.html')

// The generation answer decides the outcome. A failure arrives as the fetch
// layer's resolved machine outcome ({outcome:'busy'} / {outcome:'rate_limited'})
// — the same object a real 503/429 problem+json produces — so the shelf renders
// the matching honest notice. The read + focused endpoints stay feasible so the
// brief editor enables Generate.
const stub = (recipes) => ({
  '/api/v1/grains/recipes': recipes,
  '/api/v1/grains/sensory-range': { status: 'feasible', name: 'malty', min: 0.1, max: 2.6 },
  '/api/v1/grains/feasibility': { status: 'feasible' },
  '/api/v1/styles/american-pale-ale': apa.style,
  '/api/v1/styles': apa.styles
})

const GENERATE = '.form-foot .generate'
const desktop = { width: 1280, height: 1080 }

const shot = (name, theme, recipes) => ({
  url: indexUrl,
  theme,
  viewport: desktop,
  clicks: [GENERATE],
  settle: 700,
  out: join(outDir, `${name}.png`),
  fetchStub: stub(recipes)
})

// Two new transient outcomes × light/dark.
const shots = []
for (const theme of ['light', 'dark']) {
  shots.push(shot(`busy-${theme}`, theme, { outcome: 'busy' }))
  shots.push(shot(`rate-limited-${theme}`, theme, { outcome: 'rate_limited' }))
}

const configPath = join(tmpdir(), `issue-39-shots-${Date.now()}.json`)
writeFileSync(configPath, JSON.stringify({ shots }, null, 2))

execFileSync('node', [join(repoRoot, 'scripts/screenshots.mjs'), configPath], { stdio: 'inherit' })
