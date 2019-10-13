<template>
  <a class="list-item has-background-light">
    <div class="columns is-vcentered is-flex is-gapless">
      <div class="column is-4">
        <span class="has-text-weight-bold">{{ styleData.name }}</span>
        <br />
        <span class="subtitle is-7">{{ styleData.category }}</span>
      </div>
      <div class="column is-8">
        <!-- Render stat data only if stats exist -->
        <div class="columns is-flex is-gapless has-text-black is-size-7" v-if="hasStats">
          <div class="column is-8">
            <span
              class="is-pulled-right"
            >OG: {{ styleData.stats.og.low }} - {{ styleData.stats.og.high }}</span>
            <br />
            <span class="is-pulled-right">ABV: {{ styleData.stats.abv.low }} - {{ styleData.stats.abv.high }}%</span></span>
          </div>
          <div class="column is-4">
            <span class="is-pulled-right">SRM: {{ styleData.stats.srm.low }} - {{ styleData.stats.srm.high }}</span></span>
            <br />
            <span class="is-pulled-right">IBU: {{ styleData.stats.ibu.low }} - {{ styleData.stats.ibu.high }}</span></span>
          </div>
        </div>
        <!-- Display exception text if there are no stats -->
        <div class="columns is-flex is-gapless has-text-black is-size-7" v-else>
            <div class="column">
                <p class="has-text-right">
                {{ styleData.stats.exceptions }}
                </p>
            </div>

        </div>
      </div>
    </div>
  </a>
</template>

<script>
export default {
  name: 'StyleCard',
  props: ['styleData'],
  computed: {
      hasStats: function() {
          if (this.styleData.stats.exceptions === undefined) {
              return true
          } else {
              return false
          }
      }
  }
};
</script>

<style>
</style>