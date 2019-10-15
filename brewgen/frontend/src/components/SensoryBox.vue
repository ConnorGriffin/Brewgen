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
    <div class="keyword-box"></div>
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
    ...mapGetters(['currentStyleSensory'])
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