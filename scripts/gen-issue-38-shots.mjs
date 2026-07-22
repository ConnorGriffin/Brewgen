/*
 * Generate the issue #38 results-shelf screenshot set via the canonical harness
 * (scripts/screenshots.mjs). Builds a per-shot config from the frontend's own
 * fixture data, clicks Generate (and, for the spines shot, opens a card), and
 * runs the harness against the offline build. Usage:
 *   cd brewgen/frontend && npm run build:offline
 *   node scripts/gen-issue-38-shots.mjs <out-dir>
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
const outDir = resolve(process.argv[2] || 'docs/screenshots/issue-38/local')
const indexUrl = 'file://' + join(repoRoot, 'brewgen/frontend/offline/index.html')

// Stub keys are matched by substring, most-specific first. `recipes` is the
// generation answer the shelf renders (complete or infeasible per shot).
const stub = (recipes) => ({
  '/api/v1/grains/recipes': recipes,
  '/api/v1/grains/sensory-range': { status: 'feasible', name: 'malty', min: 0.1, max: 2.6 },
  '/api/v1/grains/feasibility': { status: 'feasible' },
  '/api/v1/styles/american-pale-ale': apa.style,
  '/api/v1/styles': apa.styles
})

const GENERATE = '.form-foot .generate'
const OPEN_SECOND = '.shelf .card:nth-child(2)'

const desktop = { width: 1280, height: 1080 }
const mobile = { width: 375, height: 900 }

const shot = (name, theme, viewport, recipes, clicks) => ({
  url: indexUrl,
  theme,
  viewport,
  clicks,
  settle: 700,
  out: join(outDir, `${name}.png`),
  fetchStub: stub(recipes)
})

// Four states × light/dark: flat shelf, selected-spines, mobile-spines, infeasible.
const shots = []
for (const theme of ['light', 'dark']) {
  shots.push(shot(`shelf-desktop-${theme}`, theme, desktop, apa.recipesComplete, [GENERATE]))
  shots.push(shot(`spines-desktop-${theme}`, theme, desktop, apa.recipesComplete, [GENERATE, OPEN_SECOND]))
  shots.push(shot(`results-mobile-${theme}`, theme, mobile, apa.recipesComplete, [GENERATE]))
  shots.push(shot(`infeasible-desktop-${theme}`, theme, desktop, apa.recipesInfeasible, [GENERATE]))
}

const configPath = join(tmpdir(), `issue-38-shots-${Date.now()}.json`)
writeFileSync(configPath, JSON.stringify({ shots }, null, 2))

execFileSync('node', [join(repoRoot, 'scripts/screenshots.mjs'), configPath], { stdio: 'inherit' })
