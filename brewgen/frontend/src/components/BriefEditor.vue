<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import FlavorRow from './FlavorRow.vue'
import { listStyles, getStyle, fetchSensoryRange, fetchFeasibility } from '@/api.js'
import { srmGradient, srmWord } from '@/srm.js'
import { seedLevel, briefPayload, humanize } from '@/brief.js'

const emit = defineEmits(['generate'])

const MAX_ROWS = 5
const DEBOUNCE_MS = 300

const styles = ref([])
const style = ref(null)
const selectedSlug = ref('')
const loadError = ref(false)

const brief = reactive({ abv: 0, srm: 0, flavors: [] })
const abvBounds = reactive({ min: 0, max: 0 })
const srmBounds = reactive({ min: 0, max: 0 })

const feas = reactive({ status: 'idle', checking: false })
const search = ref('')

/* Monotonic keys so out-of-order async answers can be dropped. One counter for
 * the whole-brief feasibility check; one per descriptor for focused ranges. */
let feasSeq = 0
let feasTimer = null
let feasAbort = null
const rangeSeq = {}
const rangeAbort = {}

/* ---- style / brief seeding --------------------------------------------- */

onMounted(async () => {
  try {
    styles.value = await listStyles()
  } catch {
    loadError.value = true
    return
  }
  const preferred = styles.value.find((s) => s.slug === 'american-pale-ale')
  const first = preferred || styles.value[0]
  if (first) await loadStyle(first.slug)
})

async function loadStyle (slug) {
  selectedSlug.value = slug
  let data
  try {
    data = await getStyle(slug)
  } catch {
    loadError.value = true
    return
  }
  loadError.value = false
  style.value = data

  const abv = data.stats?.abv || { low: 4, high: 6 }
  const srm = data.stats?.srm || { low: 2, high: 20 }
  abvBounds.min = round1(abv.low)
  abvBounds.max = round1(abv.high)
  brief.abv = round1((abv.low + abv.high) / 2)
  srmBounds.min = Math.round(srm.low)
  srmBounds.max = Math.round(srm.high)
  brief.srm = Math.round((srm.low + srm.high) / 2)

  brief.flavors = seedFlavors(data)
  scheduleFeasibility()
}

/* Style-mentioned flavours arrive pre-set (BJCP descriptors), seeded to a level
 * from their style mean, capped at five rows. No range requests fire here —
 * a focused range is fetched only when the visitor opens or adds a flavour. */
function seedFlavors (data) {
  const mentioned = Object.keys(data.bjcp_sensory || {})
  const byName = new Map((data.sensory_data || []).map((s) => [s.name, s]))
  return mentioned
    .filter((name) => byName.has(name))
    .slice(0, MAX_ROWS)
    .map((name) => {
      const sd = byName.get(name)
      return { name, level: seedLevel(sd.mean), styleMin: sd.min, styleMax: sd.max, range: null }
    })
}

/* ---- focused single-descriptor range ------------------------------------ */

async function refreshRange (flavor) {
  if (!style.value) return
  const name = flavor.name
  const seq = (rangeSeq[name] || 0) + 1
  rangeSeq[name] = seq
  if (rangeAbort[name]) rangeAbort[name].abort()
  const ctrl = new AbortController()
  rangeAbort[name] = ctrl

  const payload = { descriptor: name, ...briefPayload(style.value, brief) }
  let result
  try {
    result = await fetchSensoryRange(payload, ctrl.signal)
  } catch {
    return // aborted or network error — leave the prior range untouched
  }
  if (seq !== rangeSeq[name]) return // a newer edit to this flavour won
  flavor.range = result && result.status === 'feasible'
    ? { min: result.min, max: result.max }
    : null
}

/* ---- debounced whole-brief feasibility ---------------------------------- */

function scheduleFeasibility () {
  feas.checking = true
  if (feasTimer) clearTimeout(feasTimer)
  feasTimer = setTimeout(runFeasibility, DEBOUNCE_MS)
}

async function runFeasibility () {
  if (!style.value) return
  const seq = ++feasSeq
  if (feasAbort) feasAbort.abort()
  const ctrl = new AbortController()
  feasAbort = ctrl

  let result
  try {
    result = await fetchFeasibility(briefPayload(style.value, brief), ctrl.signal)
  } catch {
    return // aborted by a newer request, or transient failure
  }
  if (seq !== feasSeq) return // a newer brief already dispatched — drop this one
  feas.checking = false
  feas.status = (result && result.status) || 'invalid'
}

/* ---- visitor interactions ----------------------------------------------- */

function onStyleChange (event) {
  loadStyle(event.target.value)
}

function onAbv (event) {
  brief.abv = Number(event.target.value)
  scheduleFeasibility()
}

function onSrm (event) {
  brief.srm = Number(event.target.value)
  scheduleFeasibility()
}

/* A flavour edit: exactly one focused range request for that one descriptor,
 * plus the debounced whole-brief check. Never the all-descriptor sweep. */
function setFlavor (i, level) {
  brief.flavors[i].level = level
  refreshRange(brief.flavors[i])
  scheduleFeasibility()
}

function removeFlavor (i) {
  brief.flavors.splice(i, 1)
  scheduleFeasibility()
}

function addFlavor (name) {
  if (brief.flavors.length >= MAX_ROWS) return
  const sd = (style.value.sensory_data || []).find((s) => s.name === name)
  const flavor = reactive({
    name,
    level: 2,
    styleMin: sd ? sd.min : 0,
    styleMax: sd ? sd.max : 2,
    range: null
  })
  brief.flavors.push(flavor)
  search.value = ''
  refreshRange(flavor)
  scheduleFeasibility()
}

/* ---- derived view state ------------------------------------------------- */

const suggestions = computed(() => {
  if (!style.value) return []
  const have = new Set(brief.flavors.map((f) => f.name))
  const q = search.value.trim().toLowerCase()
  return (style.value.sensory_data || [])
    .map((s) => s.name)
    .filter((n) => !have.has(n) && humanize(n).includes(q))
    .slice(0, 8)
})

const srmTrack = computed(() => srmGradient(srmBounds.min, srmBounds.max))
const srmReadout = computed(() => `${brief.srm} SRM · ${srmWord(brief.srm)}`)
const atMax = computed(() => brief.flavors.length >= MAX_ROWS)

const feasLine = computed(() => {
  if (loadError.value) return { cls: 'no', text: '' }
  if (feas.checking) return { cls: 'checking', text: 'Checking this brief…' }
  switch (feas.status) {
    case 'feasible': return { cls: 'ok', text: 'A grain bill can meet this brief.' }
    case 'infeasible': return { cls: 'no', text: 'No grain bill fits this brief yet — ease a flavour or widen the colour.' }
    case 'deadline':
    case 'deadline_exceeded': return { cls: 'checking', text: 'This brief is taking a while to pin down.' }
    case 'busy': return { cls: 'checking', text: 'Brewgen is busy right now — try again in a moment.' }
    case 'rate_limited': return { cls: 'checking', text: 'Checking a lot right now — pause a moment, then edit again.' }
    case 'invalid': return { cls: 'checking', text: 'Add a little more to this brief.' }
    default: return { cls: 'checking', text: '' }
  }
})

const canGenerate = computed(() => feas.status === 'feasible')

/* Hand the results shelf both the solver payload and a display context: the
 * brief read back in its own terms (style, strength, colour, flavour steps). */
function onGenerate () {
  if (!canGenerate.value || !style.value) return
  emit('generate', {
    payload: briefPayload(style.value, brief),
    context: {
      styleName: style.value.name,
      abv: brief.abv,
      srm: brief.srm,
      flavors: brief.flavors.map((f) => ({
        name: f.name,
        level: f.level,
        styleMin: f.styleMin,
        styleMax: f.styleMax
      }))
    }
  })
}

function round1 (n) { return Math.round(Number(n) * 10) / 10 }
</script>

<template>
  <section class="brief-screen">
    <h1>Brew something</h1>
    <p class="sub">Say what you want to taste. Brewgen finds the grain bills.</p>

    <div v-if="loadError" class="notice">
      <p class="notice-msg">Couldn’t load the styles just now. Give it another moment.</p>
    </div>

    <div v-else-if="style" class="brief-card">
      <div class="field">
        <label for="style">Style</label>
        <select id="style" :value="selectedSlug" @change="onStyleChange">
          <option v-for="s in styles" :key="s.slug" :value="s.slug">{{ s.name }}</option>
        </select>
      </div>

      <div class="field">
        <label for="abv">Strength <span class="readout">{{ brief.abv.toFixed(1) }}%</span></label>
        <input
          id="abv" type="range" step="0.1"
          :min="abvBounds.min" :max="abvBounds.max" :value="brief.abv"
          @input="onAbv"
        />
      </div>

      <div class="field">
        <label for="srm">Color <span class="readout">{{ srmReadout }}</span></label>
        <div class="srm-wrap">
          <div class="srm-track" :style="{ background: srmTrack }"></div>
          <input
            id="srm" class="srm-range" type="range" step="1"
            :min="srmBounds.min" :max="srmBounds.max" :value="brief.srm"
            @input="onSrm"
          />
        </div>
      </div>

      <div class="field">
        <label>Flavors</label>
        <div class="flavor-rows">
          <FlavorRow
            v-for="(f, i) in brief.flavors"
            :key="f.name"
            :flavor="f"
            @set="(lvl) => setFlavor(i, lvl)"
            @remove="removeFlavor(i)"
          />
          <div v-if="!atMax" class="add-wrap">
            <input
              class="flavor-search" v-model="search"
              placeholder="add a flavor" autocomplete="off"
              aria-label="Add a flavor"
            />
            <div class="flavor-suggestions">
              <button
                v-for="n in suggestions" :key="n"
                class="sugg" type="button"
                @click="addFlavor(n)"
              >{{ humanize(n) }}</button>
            </div>
          </div>
          <p v-else class="max-note">five flavors is the limit — remove one to add another</p>
        </div>
      </div>

      <details class="advanced">
        <summary>Advanced</summary>
        <p>Original gravity, apparent attenuation, batch size, and mash
           efficiency use style-typical defaults.</p>
      </details>

      <div class="form-foot">
        <span class="feas" :class="feasLine.cls">{{ feasLine.text }}</span>
        <button class="generate" type="button" :disabled="!canGenerate" @click="onGenerate">Generate</button>
      </div>
    </div>
  </section>
</template>
