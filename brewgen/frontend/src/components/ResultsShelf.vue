<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import BillCard from './BillCard.vue'
import {
  withLetters, resolveOutcome, OUTCOME_NOTICE,
  briefSentence, differentiators
} from '@/results.js'

const props = defineProps({
  // { styleName, abv, srm, flavors:[{name, level, styleMin, styleMax}] }
  context: { type: Object, default: null },
  // { status, alternatives, error } straight from /api/v1/grains/recipes
  result: { type: Object, default: null },
  // True while a generation request is in flight (transient, not an outcome).
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['edit'])

/* Selected letter of the open bill; null on desktop means the flat shelf. */
const selected = ref(null)

/* Mobile starts in the spines composition, so the phone is never a flat card
 * list. matchMedia is guarded for the component-test environment. */
const isMobile = ref(false)
let mql = null
function syncMobile () {
  isMobile.value = !!(mql && mql.matches)
}
onMounted(() => {
  if (typeof window !== 'undefined' && window.matchMedia) {
    mql = window.matchMedia('(max-width: 640px)')
    syncMobile()
    mql.addEventListener('change', syncMobile)
  }
})
onBeforeUnmount(() => {
  if (mql) mql.removeEventListener('change', syncMobile)
})

const outcome = computed(() => resolveOutcome(props.result))
const hasBrief = computed(() => !!(props.context && props.context.styleName))
const onShelf = computed(() => outcome.value === 'complete' || outcome.value === 'partial')

const bills = computed(() =>
  onShelf.value ? withLetters(props.result.alternatives) : [])
const asides = computed(() =>
  bills.value.length ? differentiators(bills.value, props.context.flavors || []) : {})

const briefLine = computed(() => (hasBrief.value ? briefSentence(props.context) : ''))

/* On mobile one bill is always open (default the first); desktop may sit flat. */
const openLetter = computed(() => {
  if (!bills.value.length) return null
  if (isMobile.value) {
    const match = bills.value.find((b) => b.letter === selected.value)
    return match ? selected.value : bills.value[0].letter
  }
  return selected.value
})

function modeFor (letter) {
  if (openLetter.value === letter) return 'open'
  return openLetter.value ? 'spine' : 'card'
}

function selectBill (letter) { selected.value = letter }
function showAll () { selected.value = null }

const title = computed(() => {
  const n = bills.value.length
  return `${n} grain bill${n === 1 ? '' : 's'}`
})
const partialNote = computed(() =>
  outcome.value === 'partial'
    ? `Only ${bills.value.length} distinct grain bills fit this brief.`
    : '')
const canShowAll = computed(() => !isMobile.value && !!openLetter.value)

const notice = computed(() => OUTCOME_NOTICE[outcome.value] || null)
</script>

<template>
  <section class="results-screen">
    <!-- Order-ticket brief readback + the small edit action. -->
    <template v-if="hasBrief">
      <p class="brief-line" v-html="briefLine"></p>
      <button class="edit-brief" type="button" @click="emit('edit')">✎ edit brief</button>
    </template>

    <!-- Generation in flight: a quiet holding state, never the empty state. -->
    <div v-if="loading" class="notice notice-loading">
      <p class="notice-msg">Finding grain bills…</p>
    </div>

    <!-- Shelf: complete or partial. Every bill visible, letters not rankings. -->
    <template v-else-if="onShelf">
      <div class="result-head">
        <h2>{{ title }}</h2>
        <span class="result-note">
          {{ partialNote }}
          <template v-if="canShowAll">
            <span v-if="partialNote"> · </span>
            <a href="#" @click.prevent="showAll">show all</a>
          </template>
        </span>
      </div>

      <div class="shelf" :class="{ focused: !!openLetter }" aria-live="polite">
        <BillCard
          v-for="b in bills"
          :key="b.letter"
          :bill="b"
          :mode="modeFor(b.letter)"
          :aside="asides[b.letter] || ''"
          :abv="context.abv"
          :flavors="context.flavors || []"
          @select="selectBill"
        />
      </div>

      <p class="scope-note">All-grain bills. The grain is mashed, not steeped.
        Hops, yeast, and water are up to you.</p>
    </template>

    <!-- Infeasible / deadline / malformed / empty: one stable quiet notice. -->
    <div v-else-if="notice" class="notice" :class="'notice-' + outcome" aria-live="polite">
      <p class="notice-title">{{ notice.title }}</p>
      <p class="notice-msg">{{ notice.message }}</p>
      <button class="generate" type="button" @click="emit('edit')">
        {{ outcome === 'empty' ? 'Start a brief' : 'Back to brief' }}
      </button>
    </div>
  </section>
</template>
