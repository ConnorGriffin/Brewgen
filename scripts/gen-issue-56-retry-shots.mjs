/*
 * Generate the issue #56 before/after screenshots: retry timing on the brief
 * editor's cooldown line and on the results shelf's busy / one-brief-at-a-time
 * notices, in light and dark.
 *
 * Both bundles are built offline and driven with the canonical harness
 * (scripts/screenshots.mjs). The stubs are identical for before and after — the
 * only difference is the app code — so each pair is a like-for-like comparison.
 *
 * Usage:
 *   cd brewgen/frontend && npm run build:offline          # the "after" bundle
 *   # build the pre-change bundle somewhere, then:
 *   node scripts/gen-issue-56-retry-shots.mjs <out-dir> <before-index.html>
 */
import { writeFileSync } from 'node:fs'
import { join, resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { tmpdir } from 'node:os'
import { execFileSync } from 'node:child_process'
import * as apa from '../brewgen/frontend/tests/fixtures/apa.js'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const outDir = resolve(process.argv[2] || 'docs/screenshots/issue-56/local')
const afterIndex = 'file://' + join(repoRoot, 'brewgen/frontend/offline/index.html')
const beforeIndex = 'file://' + resolve(process.argv[3] || '.shots-before/brewgen/frontend/offline/index.html')

const reads = {
  '/api/v1/styles/american-pale-ale': apa.style,
  '/api/v1/styles': apa.styles
}

/*
 * A refusal exactly as the server sends it: problem+json with the real status
 * code, the `retry_after` body field, and the `Retry-After` header. Driving the
 * shots through this shape (rather than a 200 carrying a made-up field) is the
 * point — it is the wiring these screenshots are evidence for.
 *
 * The two waits below are the only ones a visitor can actually be quoted: a
 * busy shed is always one second, and a spent burst refills in ten.
 */
const refusal = (status, outcome, retryAfter) => ({
  $response: {
    status,
    headers: { 'Retry-After': String(retryAfter) },
    body: {
      type: 'about:blank',
      title: outcome === 'busy' ? 'Service busy' : 'Too many requests',
      status,
      outcome,
      retry_after: retryAfter
    }
  }
})

const RATE_LIMITED = refusal(429, 'rate_limited', 10)
const BUSY = refusal(503, 'busy', 1)

// The editor's automatic feasibility check comes back rate-limited, which is
// what puts the brief editor into its cooldown.
const editorStub = {
  ...reads,
  '/api/v1/grains/sensory-range': { status: 'feasible', min: 0.1, max: 2.6 },
  '/api/v1/grains/feasibility': RATE_LIMITED
}

// The shelf shots need a feasible brief (so Generate is live) and a refused
// generation.
const shelfStub = (outcome) => ({
  ...reads,
  '/api/v1/grains/sensory-range': { status: 'feasible', min: 0.1, max: 2.6 },
  '/api/v1/grains/feasibility': { status: 'feasible' },
  '/api/v1/grains/recipes': outcome === 'busy' ? BUSY : RATE_LIMITED
})

const screens = [
  { name: 'editor-rate-limited', fetchStub: editorStub, settle: 1400 },
  { name: 'shelf-busy', fetchStub: shelfStub('busy'), clicks: ['.form-foot .generate'], settle: 700 },
  { name: 'shelf-rate-limited', fetchStub: shelfStub('rate_limited'), clicks: ['.form-foot .generate'], settle: 700 }
]

const shots = []
for (const [stage, url] of [['before', beforeIndex], ['after', afterIndex]]) {
  for (const screen of screens) {
    for (const theme of ['light', 'dark']) {
      shots.push({
        url,
        theme,
        fetchStub: screen.fetchStub,
        clicks: screen.clicks,
        settle: screen.settle,
        viewport: { width: 1280, height: 900 },
        out: join(outDir, stage, `${screen.name}-${theme}.png`)
      })
    }
  }
}

const configPath = join(tmpdir(), `issue-56-retry-shots-${Date.now()}.json`)
writeFileSync(configPath, JSON.stringify({ shots }, null, 2))

execFileSync('node', [join(repoRoot, 'scripts/screenshots.mjs'), configPath], { stdio: 'inherit' })
