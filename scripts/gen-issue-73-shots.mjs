/*
 * Generate the issue #73 before/after screenshots: what the brief editor looks
 * like after a *generation* is refused and the visitor returns to the brief.
 *
 *   before — Generate is still live and the feasibility line reads normally, so
 *            the very next nudge fires a check inside the wait Brewgen quoted.
 *   after  — the refusal's wait is carried back: the editor is counting down and
 *            Generate is held until it expires.
 *
 * Both bundles are built offline and driven with the canonical harness
 * (scripts/screenshots.mjs). The stubs are identical for before and after — the
 * only difference is the app code — so each pair is a like-for-like comparison.
 *
 * Usage:
 *   cd brewgen/frontend && npm run build:offline          # the "after" bundle
 *   # build the pre-change bundle into .shots-before/…, then:
 *   node scripts/gen-issue-73-shots.mjs <out-dir> <before-index.html>
 */
import { writeFileSync } from 'node:fs'
import { join, resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { tmpdir } from 'node:os'
import { execFileSync } from 'node:child_process'
import * as apa from '../brewgen/frontend/tests/fixtures/apa.js'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const outDir = resolve(process.argv[2] || 'docs/screenshots/issue-73/local')
const afterIndex = 'file://' + join(repoRoot, 'brewgen/frontend/offline/index.html')
const beforeIndex = 'file://' + resolve(process.argv[3] || '.shots-before/brewgen/frontend/offline/index.html')

const reads = {
  '/api/v1/styles/american-pale-ale': apa.style,
  '/api/v1/styles': apa.styles
}

/*
 * A refusal exactly as the server sends it: problem+json with the real status
 * code, the `retry_after` body field, and the `Retry-After` header. A spent
 * burst refills in ten seconds — the wait the issue's story is built around.
 */
const RATE_LIMITED = {
  $response: {
    status: 429,
    headers: { 'Retry-After': '10' },
    body: {
      type: 'about:blank', title: 'Too many requests',
      status: 429, outcome: 'rate_limited', retry_after: 10
    }
  }
}

// A feasible brief (so Generate is live), then a refused *generation*. The two
// clicks press Generate and then return to the brief, which is the exact moment
// this issue is about: is the editor honouring the wait or ignoring it?
const stub = {
  ...reads,
  '/api/v1/grains/sensory-range': { status: 'feasible', min: 0.1, max: 2.6 },
  '/api/v1/grains/feasibility': { status: 'feasible' },
  '/api/v1/grains/recipes': RATE_LIMITED
}

const screen = {
  name: 'brief-after-refused-generation',
  fetchStub: stub,
  clicks: ['.form-foot .generate', '.results-screen .edit-brief'],
  settle: 500
}

const shots = []
for (const [stage, url] of [['before', beforeIndex], ['after', afterIndex]]) {
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

const configPath = join(tmpdir(), `issue-73-shots-${process.pid}.json`)
writeFileSync(configPath, JSON.stringify({ shots }, null, 2))

execFileSync('node', [join(repoRoot, 'scripts/screenshots.mjs'), configPath], { stdio: 'inherit' })
