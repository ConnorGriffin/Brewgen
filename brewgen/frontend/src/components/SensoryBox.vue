<template>
  <div class="keyword-box">
    <!-- Sensory constraint control buttons -->
    <div class="buttons">
      <b-button class="is-primary">Add Constraint</b-button>
      <b-button disabled>Clear</b-button>
    </div>
    <!-- Box containing sensory constraint cards -->
    <div class="box keyword-box">
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
  height: 100%;
  padding: 0px;
  padding-bottom: 2rem;
}
</style>