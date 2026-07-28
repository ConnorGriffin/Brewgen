/*
 * Capture issue #54's one visible state change in the locked brief editor:
 * before, Generate waits for the automatic feasibility preview; after, style
 * data makes Generate ready immediately and the advisory preview stays quiet.
 *
 * Both bundles use the same style and compute stubs through the canonical
 * screenshot harness. The artificial "checking" preview answer keeps the
 * feasibility line visually neutral in the before bundle, isolating the button
 * state as the only visible difference.
 *
 * Usage:
 *   cd brewgen/frontend && npm run build:offline
 *   node scripts/gen-issue-54-shots.mjs <out-dir> <before-index.html>
 */
import { execFileSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import * as apa from '../brewgen/frontend/tests/fixtures/apa.js'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const outDir = resolve(process.argv[2] || 'docs/screenshots/issue-54/local')
const afterIndex = 'file://' + join(repoRoot, 'brewgen/frontend/offline/index.html')
const beforeIndex = 'file://' + resolve(
  process.argv[3] || '.shots-before/brewgen/frontend/offline/index.html')

const fetchStub = {
  '/api/v1/styles/american-pale-ale': apa.style,
  '/api/v1/styles': apa.styles,
  '/api/v1/grains/feasibility': { status: 'checking' }
}

const shots = []
for (const [stage, url] of [['before', beforeIndex], ['after', afterIndex]]) {
  for (const theme of ['light', 'dark']) {
    shots.push({
      url,
      theme,
      fetchStub,
      settle: 600,
      viewport: { width: 1280, height: 900 },
      out: join(outDir, stage, `brief-generate-ready-${theme}.png`)
    })
  }
}

const configPath = join(tmpdir(), `issue-54-shots-${process.pid}.json`)
writeFileSync(configPath, JSON.stringify({ shots }, null, 2))
execFileSync(
  'node',
  [join(repoRoot, 'scripts/screenshots.mjs'), configPath],
  { stdio: 'inherit' }
)
