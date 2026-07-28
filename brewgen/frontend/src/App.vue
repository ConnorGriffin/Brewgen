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
const editor = ref(null)
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
  // A refused generation quotes a retry wait on the results notice. The brief
  // editor is still mounted behind it, so hand the same wait back and start its
  // cooldown now — the clock runs while results are read, and returning to the
  // brief finds automatic checks and Generate already held for the remainder.
  if (answer && (answer.outcome === 'busy' || answer.outcome === 'rate_limited')) {
    editor.value?.enterCooldown(answer.outcome, answer.retryAfter)
  }
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
    <BriefEditor ref="editor" v-show="screen === 'brief'" @generate="onGenerate" />
    <ResultsShelf
      v-if="screen === 'results'"
      :context="context"
      :result="result"
      :loading="generating"
      @edit="editBrief"
    />
    <a
      class="support-link"
      href="https://github.com/sponsors/ConnorGriffin"
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Support this project on GitHub Sponsors (opens in a new tab)"
    >Support this project</a>
  </div>
</template>
