/*
 * Editorial malt-stack shelf — app logic for the issue #26 prototype.
 * Direction: mockups/DIRECTION.md (grilling session 2026-07-21).
 * Data contract: mockups/public-grain-bill-workflow.capture.json — the locked
 * issue #19 envelope. All rendering binds real capture fields only; the
 * implementation repoints fetch() at the live endpoint.
 */

const SERIF_PCT = (n) => `${Math.round(n)}%`;

/* Standard SRM hex chart; lovibond converts via Morey (SRM ≈ 1.35 L − 0.76). */
const SRM_HEX = [
  [1, '#ffe699'], [2, '#ffd878'], [3, '#ffca5a'], [4, '#ffbf42'], [5, '#fbb123'],
  [6, '#f8a600'], [7, '#f39c00'], [8, '#ea8f00'], [9, '#e58500'], [10, '#de7c00'],
  [11, '#d77200'], [12, '#cf6900'], [13, '#cb6200'], [14, '#c35900'], [15, '#bb5100'],
  [16, '#b54c00'], [17, '#b04500'], [18, '#a63e00'], [19, '#a13700'], [20, '#9b3200'],
  [22, '#8f2900'], [24, '#822000'], [26, '#771900'], [28, '#6d1200'], [30, '#630d00'],
  [35, '#520a00'], [40, '#4a0700'],
];

function srmHex(srm) {
  let hex = SRM_HEX[0][1];
  for (const [s, h] of SRM_HEX) { if (srm >= s) hex = h; else break; }
  return hex;
}
const lovToSrm = (lov) => Math.max(1, 1.3546 * lov - 0.76);
/* Grain kernels read far lighter than the beer their Lovibond predicts —
 * paint layers at a reduced effective SRM so Honey 20L looks golden-sweet,
 * not porter-brown (persona finding, Walt r2). */
const grainHex = (lov) => srmHex(Math.max(1, lov * 0.6));
/* Pick the pour-band text color by measured contrast, not a threshold guess —
 * mid-amber SRM colors (6–12) fail WCAG with cream text (audit finding). */
function relLum(hex) {
  const c = hex.replace('#', '');
  const [r, g, b] = [0, 2, 4].map((i) => {
    const v = parseInt(c.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrast(a, b) {
  const [la, lb] = [relLum(a), relLum(b)];
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}
const POUR_DARK_TEXT = '#3f2a06', POUR_LIGHT_TEXT = '#fdf6e8';
const pourText = (bg) =>
  contrast(POUR_DARK_TEXT, bg) >= contrast(POUR_LIGHT_TEXT, bg)
    ? POUR_DARK_TEXT : POUR_LIGHT_TEXT;

const SRM_WORDS = [
  [3, 'straw'], [5, 'gold'], [7, 'deep gold'], [10, 'amber-gold'],
  [13, 'amber'], [17, 'copper'], [22, 'brown'], [99, 'dark brown'],
];
const srmWord = (srm) => SRM_WORDS.find(([max]) => srm <= max)[1];

/* Word-step levels. "none" doubles as the avoid state. */
const LEVELS = ['none', 'hint', 'present', 'bold'];

/* Flavor adjectives for the brief sentence. */
const FLAVOR_WORDS = {
  malty: 'malty', honey: 'honeyed', toast: 'toasty', coffee: 'coffee',
  biscuit: 'biscuity', caramel: 'caramelly', 'stone fruit': 'stone-fruity',
  chocolate: 'chocolatey', nutty: 'nutty', smoke: 'smoky',
};

const state = {
  data: null,
  screen: 'brief',
  outcome: 'typical',
  selected: null,           /* letter of the open bill, null = flat shelf */
  abv: 5.2,
  srm: 8,
  /* flavor rows: name + level index. Defaults come from the style's
   * sensory_constraints once the capture loads. */
  flavors: [],
};

/* ---- derived ------------------------------------------------------------ */

function abvRange(style) {
  /* Style-typical apparent attenuation (75%); OG exposed only in Advanced. */
  const abv = (og) => ((og - (og - (og - 1) * 0.75)) * 131.25);
  const og = style.original_gravity;
  return { min: abv(og.style_min), max: abv(og.style_max), target: abv(og.target) };
}

function grainInfo(data, slug) {
  return data.fermentables.find((f) => f.slug === slug);
}

function currentBills() {
  const out = state.data.outcomes[state.outcome];
  const all = state.data.outcomes.typical.alternatives;
  if (out.alternatives) return out.alternatives;
  if (out.alternative_ids) return all.filter((a) => out.alternative_ids.includes(a.id));
  return [];
}

/* Sparse differentiators: one italic aside max per bill, only where the
 * spread across bills is meaningful (>15% of the max value). Wanted flavors
 * get "most X" on their unique max; avoided flavors get "lowest X" on the min. */
function differentiators(bills) {
  const asides = {};
  const wanted = state.flavors.filter((f) => f.level >= 2).map((f) => f.name);
  const avoided = state.flavors.filter((f) => f.level === 0).map((f) => f.name);
  const claim = (id, text) => { if (!asides[id]) asides[id] = text; };
  for (const name of wanted) {
    const vals = bills.map((b) => b.sensory[name] ?? 0);
    const max = Math.max(...vals), min = Math.min(...vals);
    if (max <= 0 || (max - min) / max < 0.15) continue;
    claim(bills[vals.indexOf(max)].id, `most ${name}`);
  }
  for (const name of avoided) {
    const vals = bills.map((b) => b.sensory[name] ?? 0);
    const max = Math.max(...vals), min = Math.min(...vals);
    /* Only differentiate when some bill carries a tasteable amount —
     * "lowest coffee" over five near-zeros misleads (Walt r2). */
    if (max < 0.3 || (max - min) / max < 0.15) continue;
    claim(bills[vals.indexOf(min)].id, `lowest ${name}`);
  }
  return asides;
}

/* ---- brief sentence ----------------------------------------------------- */

function briefSentence() {
  const style = state.data.style.name;
  const word = (f) => FLAVOR_WORDS[f.name] || f.name;
  const main = state.flavors.filter((f) => f.level >= 2).map(word);
  const hints = state.flavors.filter((f) => f.level === 1).map((f) => f.name);
  const nones = state.flavors.filter((f) => f.level === 0).map((f) => f.name);
  const u = (t) => `<span class="u">${t}</span>`;
  const ur = (t) => `<span class="u ur">${t}</span>`;
  let flavor = '';
  if (main.length) flavor += joinAnd([cap(main[0]), ...main.slice(1)].map(u));
  if (hints.length) flavor += (flavor ? ', ' : 'A ') + `${flavor ? 'a ' : ''}hint of ${joinAnd(hints.map(u))}`;
  if (nones.length) flavor += (flavor ? ', ' : 'No ') + `${flavor ? 'no ' : ''}${joinAnd(nones.map(ur))}`;
  const facts = `About ${u(state.abv.toFixed(1) + '%')}, ${u(srmWord(state.srm))}.`;
  return `${u(style)}. ${flavor}. ${facts}`;
}
const joinAnd = (a) => a.length < 2 ? a.join('') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1];
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

/* ---- render: malt stack ------------------------------------------------- */

function stackHtml(bill, heightPx) {
  const rows = bill.grains.map((g) => {
    const f = grainInfo(state.data, g.slug);
    return `<div class="layer" style="flex:${g.percent};background:${grainHex(f.color_lovibond)}"></div>`;
  }).join('');
  return `<div class="stack" style="height:${heightPx}px">${rows}</div>`;
}

function pourBandHtml(bill) {
  const bg = srmHex(bill.srm);
  return `<div class="pour" style="background:${bg};color:${pourText(bg)}">` +
    `<span>${srmWord(bill.srm)} · ${bill.srm.toFixed(1)} SRM · ${state.abv.toFixed(1)}% ABV</span></div>`;
}

/* Per-bill flavor evidence: the bill's sensory values read back in the same
 * word-step vocabulary as the brief, normalized against the style's range. */
function tastesLine(bill) {
  const parts = state.flavors.filter((f) => f.name in bill.sensory).map((f) => {
    const v = bill.sensory[f.name];
    const c = state.data.sensory_constraints.find((sc) => sc.name === f.name);
    const t = c ? (v - c.style_min) / (c.style_max - c.style_min) : v / 2;
    const word = t < 0.08 ? `no ${f.name}` : t < 0.4 ? `a hint of ${f.name}`
      : t < 0.75 ? `${f.name} present` : `bold ${f.name}`;
    return word;
  });
  return `<p class="tastes">${parts.join(' · ')}</p>`;
}

function grainListHtml(bill, expanded) {
  return `<div class="grains">` + bill.grains.map((g) => {
    const f = grainInfo(state.data, g.slug);
    const color = grainHex(f.color_lovibond);
    return `<div class="grain-row">
      <span class="grain-name"><span class="swatch" style="background:${color}"></span>
        <span>${f.name}<small>${f.brand}</small></span></span>
      <span class="grain-nums">${expanded ? `<small>${g.pounds.toFixed(1)} lb</small>` : ''}
        <b>${SERIF_PCT(g.percent)}</b></span>
    </div>`;
  }).join('') + `</div>`;
}

/* ---- render: shelf / spines --------------------------------------------- */

function renderResults() {
  const bills = currentBills();
  const out = state.data.outcomes[state.outcome];
  const shelf = document.getElementById('shelf');
  const note = document.getElementById('result-note');
  const title = document.getElementById('result-title');
  document.getElementById('brief-line').innerHTML = briefSentence();

  if (!bills.length) {
    title.textContent = out.status === 'infeasible' ? 'No grain bill fits' : 'Ran out of time';
    note.innerHTML = '';
    shelf.className = 'shelf empty-state';
    shelf.innerHTML = `<div class="notice">
      <p class="notice-msg">${out.status === 'infeasible'
        ? 'No grain bill satisfies every part of this brief.'
        : 'The clock ran out before a grain bill came together.'}</p>
      ${out.suggestions ? `<div class="suggestions">${out.suggestions.map((s) =>
        `<button class="suggestion" onclick="alert('Mock scaffold: would relax this constraint and regenerate.')">${s}</button>`).join('')}</div>` : ''}
      ${out.status === 'deadline_exceeded'
        ? '<button class="generate retry" onclick="setOutcome(\'typical\')">Try again</button>' : ''}
    </div>`;
    return;
  }

  /* Mobile always renders focused; default focus = first bill. */
  const mobile = window.matchMedia('(max-width: 640px)').matches;
  const selected = state.selected || (mobile ? bills[0].id : null);
  if (mobile && !bills.some((b) => b.id === selected)) state.selected = bills[0].id;

  title.textContent = `${bills.length} grain bill${bills.length > 1 ? 's' : ''}`;
  note.innerHTML = out.status === 'partial'
    ? `Only ${bills.length} distinct grain bills fit this brief.` : '';
  if (selected && !mobile) note.innerHTML += `${note.innerHTML ? ' · ' : ''}<a href="#" onclick="clearSelection(event)">show all</a>`;

  const asides = differentiators(bills);
  shelf.className = selected ? 'shelf focused' : 'shelf';
  shelf.innerHTML = bills.map((b) => {
    if (selected && b.id !== selected) {
      return `<button class="spine" onclick="selectBill('${b.id}')" aria-label="Open grain bill ${b.id}">
        <span class="spine-letter">${b.id}</span>${stackHtml(b, 0)}</button>`;
    }
    const open = b.id === selected;
    const header = `<header><span class="letter">${b.id}</span>
        ${asides[b.id] ? `<span class="aside">${asides[b.id]}</span>` : ''}</header>`;
    if (open) {
      return `<article class="card open">${header}
        <div class="open-body">
          <div class="open-left">${stackHtml(b, 190)}<div class="chev">⌄</div>${pourBandHtml(b)}</div>
          <div class="open-right">${grainListHtml(b, true)}
            ${tastesLine(b)}
            <p class="batch-note">${b.grains.reduce((s, g) => s + g.pounds, 0).toFixed(1)} lb grain
              · ${state.data.equipment.batch_volume_gallons} gal batch
              · OG ${state.data.style.original_gravity.target.toFixed(3)}
              · ${state.data.equipment.mash_efficiency_percent}% efficiency</p></div>
        </div>
      </article>`;
    }
    return `<article class="card" onclick="selectBill('${b.id}')" tabindex="0" role="button" aria-label="Open grain bill ${b.id}">
      ${header}
      ${stackHtml(b, 130)}
      <div class="chev">⌄</div>
      ${pourBandHtml(b)}
      ${grainListHtml(b, false)}
    </article>`;
  }).join('');
}

function selectBill(id) { state.selected = id; renderResults(); }
function clearSelection(ev) { ev.preventDefault(); state.selected = null; renderResults(); }

/* ---- render: brief form ------------------------------------------------- */

function renderFlavors() {
  const host = document.getElementById('flavor-rows');
  host.innerHTML = state.flavors.map((f, i) => `
    <div class="flavor-row">
      <span class="flavor-name">${f.name}</span>
      <span class="steps" role="radiogroup" aria-label="${f.name} level">
        ${LEVELS.map((lvl, li) => `<button role="radio" aria-checked="${li === f.level}"
          class="step${li === f.level ? (li === 0 ? ' on-none' : ' on') : ''}"
          onclick="setFlavor(${i},${li})">${lvl}</button>`).join('')}
      </span>
      <button class="remove" onclick="removeFlavor(${i})" aria-label="Remove ${f.name}">✕</button>
    </div>`).join('') +
    (state.flavors.length < 5
      ? `<div class="add-wrap"><input id="flavor-search" placeholder="add a flavor"
           oninput="renderSuggestions(this.value)" autocomplete="off" />
         <div id="flavor-suggestions"></div></div>`
      : `<p class="max-note">five flavors is the limit — remove one to add another</p>`);
}

/* Style-relevant flavors come from the capture's sensory_constraints; the
 * extended list below stands in for the sensory model's full descriptor set. */
const EXTRA_FLAVORS = ['coffee', 'biscuit', 'caramel', 'chocolate', 'nutty', 'smoke', 'stone fruit'];

function renderSuggestions(q) {
  const host = document.getElementById('flavor-suggestions');
  const have = new Set(state.flavors.map((f) => f.name));
  const pool = [...state.data.sensory_constraints.map((c) => c.name), ...EXTRA_FLAVORS]
    .filter((n) => !have.has(n) && n.includes(q.toLowerCase()));
  host.innerHTML = pool.slice(0, 6).map((n) =>
    `<button class="sugg" onclick="addFlavor('${n}')">${n}</button>`).join('');
}

function addFlavor(name) {
  state.flavors.push({ name, level: 2 });
  renderFlavors();
}
function removeFlavor(i) { state.flavors.splice(i, 1); renderFlavors(); }
function setFlavor(i, lvl) { state.flavors[i].level = lvl; renderFlavors(); }

function renderBrief() {
  const style = state.data.style;
  const r = abvRange(style);
  const abvEl = document.getElementById('abv');
  abvEl.min = r.min.toFixed(1); abvEl.max = r.max.toFixed(1); abvEl.value = state.abv;
  document.getElementById('abv-out').textContent = `${state.abv.toFixed(1)}%`;

  const c = style.color_srm;
  const srmEl = document.getElementById('srm');
  srmEl.min = c.style_min; srmEl.max = c.style_max; srmEl.value = state.srm;
  const stops = [];
  for (let s = c.style_min; s <= c.style_max; s++) stops.push(srmHex(s));
  document.getElementById('srm-track').style.background =
    `linear-gradient(90deg, ${stops.join(',')})`;
  document.getElementById('srm-out').textContent = `${state.srm} SRM · ${srmWord(state.srm)}`;
  renderFlavors();
}

/* ---- screens & scaffold ------------------------------------------------- */

function show(screen) {
  state.screen = screen;
  document.getElementById('screen-brief').hidden = screen !== 'brief';
  document.getElementById('screen-results').hidden = screen !== 'results';
  if (screen === 'results') renderResults();
}

function setOutcome(name) {
  state.outcome = name;
  state.selected = null;
  document.querySelectorAll('#scaffold [data-outcome]').forEach((b) =>
    b.classList.toggle('active', b.dataset.outcome === name));
  show('results');
}

async function boot() {
  const res = await fetch('public-grain-bill-workflow.capture.json');
  state.data = await res.json();
  const r = abvRange(state.data.style);
  state.abv = Number(r.target.toFixed(1));
  const c = state.data.style.color_srm;
  state.srm = Math.round((c.target_min + c.target_max) / 2);
  /* Style-mentioned flavors land pre-set; demo brief adds coffee = none. */
  state.flavors = state.data.sensory_constraints.map((sc) => ({
    name: sc.name,
    level: sc.style_mean >= 2 ? 3 : sc.style_mean >= 0.8 ? 2 : 1,
  }));
  state.flavors.push({ name: 'coffee', level: 0 });

  document.getElementById('abv').addEventListener('input', (e) => {
    state.abv = Number(e.target.value);
    document.getElementById('abv-out').textContent = `${state.abv.toFixed(1)}%`;
  });
  document.getElementById('srm').addEventListener('input', (e) => {
    state.srm = Number(e.target.value);
    document.getElementById('srm-out').textContent = `${state.srm} SRM · ${srmWord(state.srm)}`;
  });
  window.addEventListener('resize', () => { if (state.screen === 'results') renderResults(); });
  /* Keyboard: Enter/Space activates card articles carrying role="button". */
  document.getElementById('shelf').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const card = e.target.closest('[role="button"]');
    if (card && card.hasAttribute('onclick')) { e.preventDefault(); card.click(); }
  });

  renderBrief();

  /* Mock-only scaffold: deep-link states for review/screenshots. */
  const q = new URLSearchParams(location.search);
  if (q.get('outcome')) setOutcome(q.get('outcome'));
  if (q.get('select')) { state.selected = q.get('select'); }
  show(q.get('screen') || (q.get('outcome') || q.get('select') ? 'results' : 'brief'));
}

boot();
