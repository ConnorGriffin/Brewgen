<template>
  <!-- Defines a sensory card, containing a descriptor name, typical values, and tags -->
  <div class="is-pulled-right">
    <p>
      <span class="has-text-weight-semibold">Style:</span>
      &nbsp;{{ currentStyleName }}
    </p>
    <p>
      <span class="has-text-weight-semibold">Target OG:</span>
      &nbsp;{{ beerProfile.originalSg }}
    </p>
    <p>
      <span class="has-text-weight-semibold">Target SRM:</span>
      &nbsp;{{ beerProfile.minSrm }} - {{ beerProfile.maxSrm }}
    </p>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'CurrentStyleCard',
  props: ['customClass'],
  computed: {
    ...mapGetters(['currentStyleName', 'equipmentProfile', 'beerProfile'])
  }
}
</script>

<style>
</style>