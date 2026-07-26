/*
 * Generate issue #52 screenshots: the support link in light/dark on desktop and mobile.
 * Usage:
 *   cd brewgen/frontend && npm run build:offline
 *   node scripts/gen-issue-52-shots.mjs <out-dir>
 */
import { writeFileSync } from 'node:fs'
import { join, resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { execFileSync } from 'node:child_process'
import * as apa from '../brewgen/frontend/tests/fixtures/apa.js'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const outDir = resolve(process.argv[2] || 'docs/screenshots/issue-52/local')
const indexUrl = 'file://' + join(repoRoot, 'brewgen/frontend/offline/index.html')

const fetchStub = {
  '/api/v1/grains/feasibility': { status: 'feasible' },
  '/api/v1/grains/sensory-range': { status: 'feasible', name: 'malty', min: 0.1, max: 2.6 },
  '/api/v1/styles/american-pale-ale': apa.style,
  '/api/v1/styles': apa.styles
}

const shots = []
for (const theme of ['light', 'dark']) {
  shots.push({
    url: indexUrl, theme, fetchStub,
    viewport: { width: 1280, height: 900 },
    out: join(outDir, `desktop-${theme}.png`)
  })
  shots.push({
    url: indexUrl, theme, fetchStub,
    viewport: { width: 390, height: 844 },
    out: join(outDir, `mobile-${theme}.png`)
  })
}

const configPath = join(repoRoot, 'scripts', `issue-52-shots-config.json`)
writeFileSync(configPath, JSON.stringify({ shots }, null, 2))

execFileSync('node', [join(repoRoot, 'scripts/screenshots.mjs'), configPath], { stdio: 'inherit' })
