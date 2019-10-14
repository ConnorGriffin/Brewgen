<template>
  <div class="keyword-div">
    <!-- Sensory constraint control buttons -->
    <div class="buttons">
      <b-button class="is-primary">Add Constraint</b-button>
      <b-button disabled>Clear</b-button>
    </div>
    <!-- Box containing sensory constraint cards -->
    <div class="keyword-box">
      <SensoryCard editable :sensoryData="sensoryCard" />
      <SensoryCard editable :sensoryData="sensoryCard" />
    </div>
  </div>
</template>

<script>
import SensoryCard from '@/components/SensoryCard.vue';

export default {
  name: 'SensoryBox',
  components: {
    SensoryCard
  },
  data() {
    return {
      sensoryCard: {
        name: 'Toast',
        configured: {
          min: 0.5,
          max: 1.25
        },
        style: {
          min: 0.25,
          max: 1.35
        },
        tags: ['in style notes', 'wide range']
      }
    };
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