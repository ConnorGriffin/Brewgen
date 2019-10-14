<template>
  <!-- Defines each beer style card in the style modal -->
  <a class="list-item has-background-light" @click="setCurrentStyleAndClose">
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
            <span
              class="is-pulled-right"
            >ABV: {{ styleData.stats.abv.low }} - {{ styleData.stats.abv.high }}%</span>
          </div>
          <div class="column is-4">
            <span
              class="is-pulled-right"
            >SRM: {{ styleData.stats.srm.low }} - {{ styleData.stats.srm.high }}</span>
            <br />
            <span
              class="is-pulled-right"
            >IBU: {{ styleData.stats.ibu.low }} - {{ styleData.stats.ibu.high }}</span>
          </div>
        </div>
        <!-- Display exception text if there are no stats -->
        <div class="columns is-flex is-gapless has-text-black is-size-7" v-else>
          <div class="column">
            <p class="has-text-right">{{ styleData.stats.exceptions }}</p>
          </div>
        </div>
      </div>
    </div>
  </a>
</template>

<script>
import { mapActions } from 'vuex';

export default {
  name: 'StyleCard',
  props: ['styleData'],
  computed: {
    hasStats: function() {
      if (this.styleData.stats.exceptions === undefined) {
        return true;
      } else {
        return false;
      }
    }
  },
  methods: {
    ...mapActions([
      'setDataFromStyle',
      'setCurrentStyleStats',
      'fetchSensoryData',
      'fetchRecipeData'
    ]),
    setCurrentStyle: function() {
      // Set the current style name, get the style grains and sensory data
      this.$store.commit('setCurrentStyleName', this.styleData.name);
      this.$store.dispatch('setDataFromStyle', this.styleData.slug).then(() => {
        // Set the starting target OG in the middle of the style range
        let averageOg =
          (this.$store.state.brewgen.currentStyleStats.og.low +
            this.$store.state.brewgen.currentStyleStats.og.high) /
          2;
        this.$store.commit('setBeerProfileKey', {
          key: 'originalSg',
          value: Number(averageOg.toFixed(3))
        });

        // Set the high and low SRM to be the whole style range by default
        this.$store.commit('setBeerProfileKey', {
          key: 'minSrm',
          value: this.$store.state.brewgen.currentStyleStats.srm.low
        });
        this.$store.commit('setBeerProfileKey', {
          key: 'maxSrm',
          value: this.$store.state.brewgen.currentStyleStats.srm.high
        });

        // Get the sensory and recipe data after setting everything else
        this.fetchSensoryData();
        this.fetchRecipeData({ colorOnly: true });
      });
    },
    setCurrentStyleAndClose: function() {
      this.setCurrentStyle();
      this.$parent.$parent.close();
    }
  }
};
</script>

<style>
</style>