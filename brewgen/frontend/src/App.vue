<script setup>
import { ref } from 'vue'
import BriefEditor from './components/BriefEditor.vue'
import ResultsShelf from './components/ResultsShelf.vue'
import { fetchRecipes } from '@/api.js'

/* The public workflow is two screens: build a brief, then read the shelf. The
 * brief editor stays mounted (v-show) so "edit brief" returns to the exact form
 * the visitor left, without refetching styles or losing their flavors. */
const screen = ref('brief')
const context = ref(null)
const result = ref(null)
const generating = ref(false)
let genAbort = null

async function onGenerate ({ payload, context: ctx }) {
  context.value = ctx
  result.value = null
  generating.value = true
  screen.value = 'results'
  if (genAbort) genAbort.abort()
  genAbort = new AbortController()
  const answer = await fetchRecipes(payload, genAbort.signal)
  result.value = answer
  generating.value = false
}

function editBrief () {
  screen.value = 'brief'
}
</script>

<template>
  <div class="page">
    <div class="masthead">
      <span class="mark">▲</span>
      <span class="name">Brewgen</span>
    </div>
    <BriefEditor v-show="screen === 'brief'" @generate="onGenerate" />
    <ResultsShelf
      v-if="screen === 'results'"
      :context="context"
      :result="result"
      :loading="generating"
      @edit="editBrief"
    />
  </div>
</template>
