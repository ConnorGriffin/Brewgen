/*
 * Generate the issue #37 brief-editor screenshot set via the canonical harness
 * (scripts/screenshots.mjs). Builds a per-shot config from the frontend's own
 * fixture data and runs the harness against the offline build. Usage:
 *   cd brewgen/frontend && npm run build:offline
 *   node scripts/gen-issue-37-shots.mjs <out-dir>
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
const outDir = resolve(process.argv[2] || 'docs/screenshots/issue-37/local')
const indexUrl = 'file://' + join(repoRoot, 'brewgen/frontend/offline/index.html')

// Stub keys are matched by substring, most-specific first.
const baseStub = (feasibility) => ({
  '/api/v1/grains/sensory-range': { status: 'feasible', name: 'malty', min: 0.1, max: 2.6 },
  '/api/v1/grains/feasibility': { status: feasibility },
  '/api/v1/styles/american-pale-ale': apa.style,
  '/api/v1/styles': apa.styles
})

const desktop = { width: 1280, height: 1000 }
const mobile = { width: 390, height: 900 }

const shot = (name, theme, viewport, feasibility) => ({
  url: indexUrl,
  theme,
  viewport,
  settle: 800,
  out: join(outDir, `${name}.png`),
  fetchStub: baseStub(feasibility)
})

const shots = [
  shot('brief-desktop-light', 'light', desktop, 'feasible'),
  shot('brief-desktop-dark', 'dark', desktop, 'feasible'),
  shot('brief-mobile-light', 'light', mobile, 'feasible'),
  shot('brief-mobile-dark', 'dark', mobile, 'feasible'),
  shot('brief-infeasible-desktop-light', 'light', desktop, 'infeasible'),
  shot('brief-infeasible-desktop-dark', 'dark', desktop, 'infeasible')
]

const configPath = join(tmpdir(), `issue-37-shots-${Date.now()}.json`)
writeFileSync(configPath, JSON.stringify({ shots }, null, 2))

execFileSync('node', [join(repoRoot, 'scripts/screenshots.mjs'), configPath], { stdio: 'inherit' })
