/*
 * Real-browser walkthrough of the public results shelf.
 *
 * Drives the actual built public app in headless Chromium: submits a feasible
 * brief, then proves the shelf renders 2–5 lettered, unranked bills; that
 * selecting a desktop card compresses the rest to spines; and that each of the
 * six outcome states (complete, partial, infeasible, deadline, malformed,
 * empty) renders its stable plain-language state. Run with:
 *   npm run test:browser   (builds the offline bundle first)
 *
 * Sandbox recipe (Chromium args, file:// navigation, fetch stubbed via
 * addInitScript) matches the canonical agentflow screenshot harness. The stub
 * returns whatever window.__recipes holds for the recipes endpoint, so the test
 * can flip the outcome between generations without reloading the page.
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

/* Stub the read + focused endpoints as feasible, and answer /grains/recipes
 * from window.__recipes (or a 400 when window.__malformed is set). */
function initScript (fixture) {
  return `(function () {
    var f = ${JSON.stringify(fixture)};
    window.__recipes = f.recipesComplete;
    window.__malformed = false;
    window.__problem = null;
    window.fetch = function (url) {
      var s = String(url), data = {}, status = 200;
      if (s.indexOf('/grains/recipes') !== -1) {
        if (window.__problem) {
          // A real application/problem+json failure (429 rate-limited, 503 busy)
          // carrying only the stable machine outcome tag — no echoed input.
          status = window.__problem.status;
          data = { title: 'compute failure', status: status, outcome: window.__problem.outcome };
        } else if (window.__malformed) { status = 400; data = {}; }
        else { data = window.__recipes; }
      } else if (s.indexOf('/grains/sensory-range') !== -1) {
        data = { status: 'feasible', min: 0.1, max: 2.6 };
      } else if (s.indexOf('/grains/feasibility') !== -1) {
        data = { status: 'feasible' };
      } else if (s.indexOf('/styles/') !== -1) {
        data = f.style;
      } else if (s.indexOf('/styles') !== -1) {
        data = f.styles;
      }
      return Promise.resolve(new Response(JSON.stringify(data), {
        status: status, headers: { 'Content-Type': 'application/json' }
      }));
    };
  })();`
}

const CHROMIUM_ARGS = [
  '--no-sandbox', '--disable-setuid-sandbox', '--single-process',
  '--allow-file-access-from-files'
]

function fail (msg) { console.error('FAIL: ' + msg); process.exit(1) }
function assert (cond, msg) { if (!cond) fail(msg) }

if (!existsSync(indexHtml)) fail('offline build missing — run `npm run build:offline` first (' + indexHtml + ')')

const pw = await loadPlaywright()
const browser = await pw.chromium.launch({ args: CHROMIUM_ARGS })
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
await context.addInitScript(initScript({
  styles: apa.styles,
  style: apa.style,
  recipesComplete: apa.recipesComplete,
  recipesPartial: apa.recipesPartial,
  recipesInfeasible: apa.recipesInfeasible,
  recipesDeadline: apa.recipesDeadline
}))
const page = await context.newPage()

const count = (sel) => page.$$eval(sel, (els) => els.length)
const noLeak = (t) => assert(!/infeasible|deadline_exceeded|solver|status/i.test(t),
  'outcome copy leaked a solver/server internal: ' + t)

async function setRecipes (value) {
  await page.evaluate((v) => { window.__recipes = v; window.__malformed = false; window.__problem = null }, value)
}
async function setMalformed () {
  await page.evaluate(() => { window.__malformed = true; window.__problem = null })
}
async function setProblem (status, outcome) {
  await page.evaluate((p) => { window.__problem = p; window.__malformed = false }, { status, outcome })
}
async function generate () {
  await page.waitForFunction(() => {
    const b = document.querySelector('.generate')
    return b && !b.disabled
  })
  await page.click('.form-foot .generate')
}
async function backToBrief () {
  // Either the edit-brief link (shelf) or the notice's button returns to the form.
  await page.click('.edit-brief, .notice .generate')
  await page.waitForFunction(() => {
    const el = document.querySelector('.brief-card')
    return el && el.offsetParent !== null
  })
}

try {
  await page.goto('file://' + indexHtml, { waitUntil: 'networkidle' })
  await page.waitForSelector('.flavor-row')

  // 1) Complete: five lettered, unranked bills in one flat shelf.
  await generate()
  await page.waitForSelector('.shelf .card')
  const letters = await page.$$eval('.shelf .letter', (els) => els.map((e) => e.textContent.trim()))
  assert(JSON.stringify(letters) === JSON.stringify(['A', 'B', 'C', 'D', 'E']),
    'expected lettered bills A–E, saw ' + JSON.stringify(letters))
  assert((await count('.card')) === 5, 'expected five full cards')
  assert((await count('.spine')) === 0, 'a flat shelf shows no spines')
  const title = await page.$eval('.result-head h2', (e) => e.textContent.trim())
  assert(title === '5 grain bills', 'expected "5 grain bills", saw ' + title)
  assert(!/#?\b[1-9](st|nd|rd|th)?\b\s*(pick|rank|best)/i.test(await page.content()),
    'bills must be lettered, never ranked')

  // 2) Selecting a desktop card expands it and compresses the rest to spines.
  await page.click('.shelf .card:nth-child(2)')
  await page.waitForSelector('.card.open')
  assert((await count('.card.open')) === 1, 'exactly one card should open')
  assert((await count('.spine')) === 4, 'the other four bills should become spines')
  const openLetter = await page.$eval('.card.open .letter', (e) => e.textContent.trim())
  assert(openLetter === 'B', 'the clicked bill (B) should be the open one')

  // 3) Partial: fewer bills, with the plain-language partial note.
  await backToBrief()
  await setRecipes(apa.recipesPartial)
  await generate()
  await page.waitForSelector('.shelf .card')
  assert((await count('.shelf .card')) === 3, 'partial should show three bills')
  const note = await page.$eval('.result-note', (e) => e.textContent)
  assert(/Only 3 distinct grain bills fit this brief\./.test(note), 'missing partial note, saw ' + note)

  // 4) Infeasible.
  await backToBrief()
  await setRecipes(apa.recipesInfeasible)
  await generate()
  await page.waitForSelector('.notice-infeasible')
  assert((await page.$eval('.notice-title', (e) => e.textContent.trim())) === 'No grain bill fits',
    'infeasible title mismatch')
  noLeak(await page.$eval('.notice', (e) => e.textContent))

  // 5) Deadline exceeded.
  await backToBrief()
  await setRecipes(apa.recipesDeadline)
  await generate()
  await page.waitForSelector('.notice-deadline')
  assert((await page.$eval('.notice-title', (e) => e.textContent.trim())) === 'Ran out of time',
    'deadline title mismatch')
  noLeak(await page.$eval('.notice', (e) => e.textContent))

  // 6) Malformed: a non-200 answer.
  await backToBrief()
  await setMalformed()
  await generate()
  await page.waitForSelector('.notice-malformed')
  noLeak(await page.$eval('.notice', (e) => e.textContent))

  // 7) Empty: nothing to show.
  await backToBrief()
  await setRecipes({ status: 'complete', alternatives: [] })
  await generate()
  await page.waitForSelector('.notice-empty')
  noLeak(await page.$eval('.notice', (e) => e.textContent))

  // 8) Busy: a real 503 from the two-slot concurrency ceiling.
  await backToBrief()
  await setProblem(503, 'busy')
  await generate()
  await page.waitForSelector('.notice-busy')
  assert((await page.$eval('.notice-title', (e) => e.textContent.trim())) === 'Brewgen is catching its breath',
    'busy title mismatch')
  noLeak(await page.$eval('.notice', (e) => e.textContent))

  // 9) Rate-limited: a real 429 from the per-visitor request budget.
  await backToBrief()
  await setProblem(429, 'rate_limited')
  await generate()
  await page.waitForSelector('.notice-rate_limited')
  assert((await page.$eval('.notice-title', (e) => e.textContent.trim())) === 'One brief at a time',
    'rate-limited title mismatch')
  noLeak(await page.$eval('.notice', (e) => e.textContent))

  console.log('PASS: feasible generation renders 2–5 lettered unranked bills, selection yields spines, and all eight outcomes (incl. real 503 busy + 429 rate-limited) render')
} finally {
  await browser.close()
}
