<template>
  <div class="sensory-radar">
    <apexchart type="radar" :options="chartData.options" :series="chartData.series" height="100%" />
  </div>
</template>

<script>
export default {
  name: 'SensoryRadar',
  props: ['chartData']
}
</script>

<style>
.sensory-radar {
  /* Not a typo, setting height relative to width */
  height: 80vw;
  max-height: 60vh;
}
</style>
