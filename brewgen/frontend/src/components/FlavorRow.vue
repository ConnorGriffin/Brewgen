<script setup>
import { computed } from 'vue'
import { LEVELS, humanize, reachableLevels } from '@/brief.js'

const props = defineProps({
  flavor: { type: Object, required: true }
})
const emit = defineEmits(['set', 'remove'])

const reachable = computed(() =>
  reachableLevels(props.flavor.styleMin, props.flavor.styleMax, props.flavor.range))

function stepClass (level) {
  const on = level === props.flavor.level
  return {
    step: true,
    on: on && level > 0,
    'on-none': on && level === 0,
    unreachable: !reachable.value[level]
  }
}
</script>

<template>
  <div class="flavor-row">
    <span class="flavor-name">{{ humanize(flavor.name) }}</span>
    <span class="steps" role="radiogroup" :aria-label="`${humanize(flavor.name)} level`">
      <button
        v-for="(lvl, li) in LEVELS"
        :key="lvl"
        type="button"
        role="radio"
        :aria-checked="li === flavor.level"
        :class="stepClass(li)"
        @click="emit('set', li)"
      >{{ lvl }}</button>
    </span>
    <button
      class="remove"
      type="button"
      :aria-label="`Remove ${humanize(flavor.name)}`"
      @click="emit('remove')"
    >✕</button>
  </div>
</template>
