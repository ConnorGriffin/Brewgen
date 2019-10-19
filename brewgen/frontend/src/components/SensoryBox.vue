<template>
  <div class="keyword-div">
    <!-- Sensory constraint control buttons -->
    <div class="buttons">
      <b-button class="is-primary" @click="showSensoryPicker = true">Add Constraint</b-button>
      <b-button disabled>Clear</b-button>
    </div>
    <!-- SensoryPicker modal and contents -->
    <b-modal :active.sync="showSensoryPicker" has-modal-card trap-focus scroll="keep">
      <SensoryPicker />
    </b-modal>
    <!-- Box containing sensory constraint cards -->
    <div class="keyword-box">
      <SensoryCard
        v-for="(sensoryData, index) in filteredStyleSensory"
        :key="index"
        :sensoryData="sensoryData"
        :sliderMin="sliderMin"
        :sliderMax="sliderMax"
        type="picker"
        cardBg="white"
        :tickSpace="0.2"
      />
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import SensoryCard from '@/components/SensoryCard.vue';
import SensoryPicker from '@/components/SensoryPicker.vue';

export default {
  name: 'SensoryBox',
  components: {
    SensoryCard,
    SensoryPicker
  },
  data() {
    return {
      showSensoryPicker: false,
      alwaysLoading: true
    };
  },
  computed: {
    ...mapGetters(['currentStyleSensory', 'isLoading']),
    sliderMin: function() {
      // Returns lowest possible min sensory value in sensory array
      let values = [];
      this.currentStyleSensory.forEach(sensoryData => {
        values.push(sensoryData.style.min);
        if (sensoryData.possible !== undefined) {
          values.push(sensoryData.possible.min);
        }
        if (sensoryData.configured !== undefined) {
          values.push(sensoryData.configured.min);
        }
      });
      values.sort();
      return values[0];
    },
    sliderMax: function() {
      // Returns highest possible max sensory value in sensory array
      let values = [];
      this.currentStyleSensory.forEach(sensoryData => {
        values.push(sensoryData.style.max);
        if (sensoryData.possible !== undefined) {
          values.push(sensoryData.possible.max);
        }
        if (sensoryData.configured !== undefined) {
          values.push(sensoryData.configured.max);
        }
      });
      values.sort(function(a, b) {
        return b - a;
      });
      return values[0];
    },
    filteredStyleSensory: function() {
      return this.currentStyleSensory.filter(sensoryData => {
        // Always show configured values
        if (sensoryData.configured !== undefined) {
          return true;
        }
        // For unconfigured, only show ones with a wide range
        if (sensoryData.possible !== undefined) {
          return sensoryData.possible.max - sensoryData.possible.min >= 0.5;
        } else {
          return false;
        }
      });
    }
  }
};
</script>

<style scoped>
.is-keyword-button {
  width: 100%;
}
.keyword-box {
  padding: 0px;
  height: 100%;
  max-height: 60vh;
  overflow-y: auto;
}
.keyword-div {
  height: 100%;
  max-height: 60vh;
  margin-bottom: 3rem;
}
</style>