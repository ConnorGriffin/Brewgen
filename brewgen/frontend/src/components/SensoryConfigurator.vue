<template>
  <!-- Defines the Sensory Configurator modal -->
  <div class="modal-card">
    <header class="modal-card-head">
      <p class="modal-card-title">{{ name }}</p>
      <a class="delete is-medium is-pulled-right" @click="$parent.close()"></a>
    </header>
    <div class="has-background-light range-slider-div">
      <section class="section range-slider-section">
        <b-field label="Style" style="padding-top: .25rem" custom-class="is-size-7 has-text-grey">
          <b-slider
            v-model="styleSliderRange"
            :min="sliderMin"
            :max="sliderMax"
            disabled
            size="is-small"
            type="is-rosewood"
            style="padding-left: 1rem; padding-right: 1rem"
          >
            <b-slider-tick
              v-for="(tick, index) in sliderTicks(styleRange[0], styleRange[1])"
              :key="index"
              :value="tick.value"
              class="is-tick-hidden"
            >{{ tick.label }}</b-slider-tick>
          </b-slider>
        </b-field>
        <b-field
          label="Possible in Current Model"
          style="padding-top: .25rem"
          custom-class="is-size-7 has-text-grey"
        >
          <b-slider
            v-model="possibleSliderRange"
            :min="sliderMin"
            :max="sliderMax"
            disabled
            size="is-small"
            type="is-info"
            style="padding-left: 1rem; padding-right: 1rem"
          >
            <b-slider-tick
              v-for="(tick, index) in sliderTicks(possibleRange[0], possibleRange[1])"
              :key="index"
              :value="tick.value"
              class="is-tick-hidden"
            >{{ tick.label }}</b-slider-tick>
          </b-slider>
        </b-field>
        <b-field label="Desired" custom-class="is-size-7 has-text-grey">
          <b-slider
            v-model="desiredSliderRange"
            :min="sliderMin"
            :max="sliderMax"
            type="is-primary"
            size="is-small"
            disabled
            style="padding-left: 1rem; padding-right: 1rem"
          >
            <b-slider-tick
              v-for="(tick, index) in sliderTicks(desiredSliderRange[0], desiredSliderRange[1])"
              :key="index"
              :value="tick.value"
              class="is-tick-hidden"
            >{{ tick.label }}</b-slider-tick>
          </b-slider>
        </b-field>
      </section>
    </div>
    <section class="modal-card-body" style="overflow-y: auto">
      <b-field label="Desired Range" custom-class="title">
        <b-slider
          v-model="desiredSliderRange"
          :min="possibleSliderRange[0]"
          :max="possibleSliderRange[1]"
          :step=".001"
          type="is-primary"
          style="padding-left: 1rem; padding-right: 1rem"
          class="has-thumb"
        >
          <b-slider-tick
            v-for="(tick, index) in sliderTicks(desiredSliderRange[0], desiredSliderRange[1])"
            :key="index"
            :value="tick.value"
            class="is-tick-hidden"
          >{{ tick.label }}</b-slider-tick>
        </b-slider>
      </b-field>
    </section>
    <footer class="modal-card-foot">
      <b-button @click="$parent.close()">Cancel</b-button>
      <b-button type="is-primary" @click="addConstraint">Add to Recipe Constraints</b-button>
    </footer>
  </div>
</template>

<script>
import { mapActions } from 'vuex';

export default {
  name: 'SensoryConfigurator',
  props: {
    name: String,
    styleRange: Array,
    possibleRange: Array,
    tickSpace: Number,
    sliderMin: Number,
    sliderMax: Number
  },
  data() {
    return {
      styleSliderRange: this.styleRange,
      possibleSliderRange: this.possibleRange,
      desiredSliderRange: this.possibleRange
    };
  },
  methods: {
    ...mapActions([
      'setSensoryConstraint',
      'fetchSensoryData',
      'fetchRecipeData'
    ]),
    sliderTicks: function(min, max) {
      if (max - min >= this.tickSpace) {
        return [
          {
            value: min,
            label: min
          },
          {
            value: max,
            label: max
          }
        ];
      } else if (min === max) {
        return [
          {
            value: min,
            label: min
          }
        ];
      } else {
        return [
          {
            value: (min + max) / 2,
            label: `${min}\xa0-\xa0${max}`
          }
        ];
      }
    },
    addConstraint: function() {
      this.setSensoryConstraint({
        name: this.name.toLowerCase(),
        min: this.desiredSliderRange[0],
        max: this.desiredSliderRange[1]
      });
      this.$parent.close();
      this.fetchSensoryData();
      this.fetchRecipeData({ colorOnly: true });
    }
  }
};
</script>

<style scoped lang="scss">
@import '~bulma/sass/utilities/_all';

.range-slider-section {
  padding-top: 1rem;
  padding-bottom: 1rem;
}
.range-slider-div {
  border-bottom: 1px solid $grey-lighter;
}
.has-thumb ::v-deep .b-slider-thumb {
  display: block !important;
}
</style>