/*
 * Real-browser regression guard for the retired 48-range fan-out.
 *
 * Drives the actual built public brief editor in a real (headless Chromium)
 * browser and proves that ONE flavor edit produces exactly ONE focused
 * single-descriptor range request — never the all-descriptor sweep. Run with:
 *   npm run test:browser        (builds the offline bundle, then this script)
 *
 * Sandbox recipe (Chromium args, file:// navigation, fetch stubbed via
 * addInitScript) matches the canonical agentflow screenshot harness — the same
 * approach that survives the agent sandbox. page.route cannot intercept file://
 * fetches, so the stub is injected into the page and doubles as the request
 * counter, read back afterwards via page.evaluate.
 */
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'
import { existsSync } from 'node:fs'
import { execSync } from 'node:child_process'
import * as apa from '../fixtures/apa.js'

const here = dirname(fileURLToPath(import.meta.url))
const indexHtml = resolve(here, '../../offline/index.html')

async function loadPlaywright () {
  const candidates = ['playwright']
  try {
    const globalRoot = execSync('npm root -g', { encoding: 'utf8' }).trim()
    if (globalRoot) candidates.push(join(globalRoot, 'playwright', 'index.mjs'))
  } catch { /* npm not on PATH */ }
  candidates.push('/opt/homebrew/lib/node_modules/playwright/index.mjs')
  for (const c of candidates) {
    try { const m = await import(c); return m.default || m } catch { /* try next */ }
  }
  throw new Error('Cannot resolve playwright')
}

/* Injected into the page: stub the five endpoints and record every focused
 * range request (by descriptor) and any forbidden all-descriptor call. */
function initScript (fixture) {
  return `(function () {
    var f = ${JSON.stringify(fixture)};
    window.__range = [];
    window.__plural = 0;
    window.fetch = function (url, init) {
      var s = String(url);
      var body = init && init.body ? JSON.parse(init.body) : null;
      var data = {};
      if (s.indexOf('/grains/sensory-range') !== -1) { window.__range.push(body && body.descriptor); data = { status: 'feasible', name: body && body.descriptor, min: 0.1, max: 2.6 }; }
      else if (s.indexOf('/grains/sensory-profiles') !== -1) { window.__plural++; data = {}; }
      else if (s.indexOf('/grains/feasibility') !== -1) { data = { status: 'feasible' }; }
      else if (s.indexOf('/styles/') !== -1) { data = f.style; }
      else if (s.indexOf('/styles') !== -1) { data = f.styles; }
      return Promise.resolve(new Response(JSON.stringify(data), {
        status: 200, headers: { 'Content-Type': 'application/json' }
      }));
    };
  })();`
}

const CHROMIUM_ARGS = [
  '--no-sandbox', '--disable-setuid-sandbox', '--single-process',
  '--allow-file-access-from-files'
]

function fail (msg) { console.error('FAIL: ' + msg); process.exit(1) }

if (!existsSync(indexHtml)) fail('offline build missing — run `npm run build:offline` first (' + indexHtml + ')')

const pw = await loadPlaywright()
const browser = await pw.chromium.launch({ args: CHROMIUM_ARGS })
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
await context.addInitScript(initScript({ styles: apa.styles, style: apa.style }))
const page = await context.newPage()

try {
  await page.goto('file://' + indexHtml, { waitUntil: 'networkidle' })
  await page.waitForSelector('.flavor-row')

  // Pre-set flavors must not trigger any focused range request on load.
  const onLoad = await page.evaluate(() => window.__range.length)
  if (onLoad !== 0) fail(`expected 0 range requests on load, saw ${onLoad}`)

  // One flavor edit: click "bold" on the first flavor row.
  await page.locator('.flavor-row').first().locator('.step').nth(3).click()
  await page.waitForTimeout(500)

  const range = await page.evaluate(() => window.__range)
  const plural = await page.evaluate(() => window.__plural)
  if (range.length !== 1) fail(`one flavor edit should make exactly one focused range request, saw ${range.length} (${range})`)
  if (plural !== 0) fail(`the all-descriptor sweep must never be called, saw ${plural}`)

  console.log(`PASS: one flavor edit -> one focused range request for "${range[0]}", zero all-descriptor calls`)
} finally {
  await browser.close()
}
