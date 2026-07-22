<script setup>
import { computed } from 'vue'
import {
  stackLayers, pourBand, tastesWords, batchNote, grainSwatch
} from '@/results.js'

const props = defineProps({
  bill: { type: Object, required: true },
  mode: { type: String, default: 'card' }, // 'card' | 'open' | 'spine'
  aside: { type: String, default: '' },
  abv: { type: Number, required: true },
  flavors: { type: Array, default: () => [] }
})

const emit = defineEmits(['select'])

const layers = computed(() => stackLayers(props.bill))
const pour = computed(() => pourBand(props.bill, props.abv))
const tastes = computed(() => tastesWords(props.bill, props.flavors))
const note = computed(() => batchNote(props.bill, props.abv))
const stackHeight = computed(() => (props.mode === 'open' ? 190 : 130))

const pct = (n) => `${Math.round(n)}%`
</script>

<template>
  <!-- Compressed spine: letter + mini malt stack, still tappable. -->
  <button
    v-if="mode === 'spine'"
    class="spine"
    type="button"
    :aria-label="`Open grain bill ${bill.letter}`"
    @click="emit('select', bill.letter)"
  >
    <span class="spine-letter">{{ bill.letter }}</span>
    <div class="stack">
      <div
        v-for="(layer, i) in layers" :key="i"
        class="layer" :style="{ flex: layer.flex, background: layer.background }"
      ></div>
    </div>
  </button>

  <!-- Open card: stack + pour on the left, grain list + tastes on the right. -->
  <article v-else-if="mode === 'open'" class="card open">
    <header>
      <span class="letter">{{ bill.letter }}</span>
      <span v-if="aside" class="aside">{{ aside }}</span>
    </header>
    <div class="open-body">
      <div class="open-left">
        <div class="stack" :style="{ height: stackHeight + 'px' }">
          <div
            v-for="(layer, i) in layers" :key="i"
            class="layer" :style="{ flex: layer.flex, background: layer.background }"
          ></div>
        </div>
        <div class="chev">⌄</div>
        <div class="pour" :style="{ background: pour.background, color: pour.color }">
          <span>{{ pour.label }}</span>
        </div>
      </div>
      <div class="open-right">
        <div class="grains">
          <div v-for="g in bill.grains" :key="g.slug" class="grain-row">
            <span class="grain-name">
              <span class="swatch" :style="{ background: grainSwatch(g) }"></span>
              <span>{{ g.name }}<small>{{ g.brand }}</small></span>
            </span>
            <span class="grain-nums">
              <small>{{ g.use_pounds.toFixed(1) }} lb</small>
              <b>{{ pct(g.use_percent) }}</b>
            </span>
          </div>
        </div>
        <p v-if="tastes.length" class="tastes">{{ tastes.join(' · ') }}</p>
        <p class="batch-note">{{ note }}</p>
      </div>
    </div>
  </article>

  <!-- Closed full card: click or keyboard to open. -->
  <article
    v-else
    class="card"
    tabindex="0"
    role="button"
    :aria-label="`Open grain bill ${bill.letter}`"
    @click="emit('select', bill.letter)"
    @keydown.enter.prevent="emit('select', bill.letter)"
    @keydown.space.prevent="emit('select', bill.letter)"
  >
    <header>
      <span class="letter">{{ bill.letter }}</span>
      <span v-if="aside" class="aside">{{ aside }}</span>
    </header>
    <div class="stack" :style="{ height: stackHeight + 'px' }">
      <div
        v-for="(layer, i) in layers" :key="i"
        class="layer" :style="{ flex: layer.flex, background: layer.background }"
      ></div>
    </div>
    <div class="chev">⌄</div>
    <div class="pour" :style="{ background: pour.background, color: pour.color }">
      <span>{{ pour.label }}</span>
    </div>
    <div class="grains">
      <div v-for="g in bill.grains" :key="g.slug" class="grain-row">
        <span class="grain-name">
          <span class="swatch" :style="{ background: grainSwatch(g) }"></span>
          <span>{{ g.name }}<small>{{ g.brand }}</small></span>
        </span>
        <span class="grain-nums">
          <b>{{ pct(g.use_percent) }}</b>
        </span>
      </div>
    </div>
  </article>
</template>
