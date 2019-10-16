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
        v-for="(sensoryData, index) in configuredSensory"
        :key="index"
        :sensoryData="sensoryData"
        :sliderMin="sliderMin"
        :sliderMax="sliderMax"
        type="added"
        cardBg="white"
        :tickSpace="0.4"
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
      showSensoryPicker: false
    };
  },
  computed: {
    ...mapGetters(['currentStyleSensory']),
    configuredSensory: function() {
      return this.currentStyleSensory.filter(sensoryData => {
        return sensoryData.configured !== undefined;
      });
    },
    sliderMin: function() {
      // Returns lowest possible min sensory value in sensory array
      let values = this.currentStyleSensory.map(sensoryData => {
        return sensoryData.style.min;
      });
      values.sort();
      return values[0];
    },
    sliderMax: function() {
      // Returns highest possible max sensory value in sensory array
      let values = this.currentStyleSensory.map(sensoryData => {
        return sensoryData.style.max;
      });
      values.sort(function(a, b) {
        return b - a;
      });
      return values[0];
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
  overflow-y: auto;
}
.keyword-div {
  height: 100%;
  max-height: 60vh;
}
</style>