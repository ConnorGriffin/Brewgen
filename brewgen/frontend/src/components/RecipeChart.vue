<template>
  <div class="recipe-chart">
    <apexchart type="bar" :options="chartData.options" :series="chartData.series" height="100%" />
  </div>
</template>

<script>
export default {
  name: 'RecipeChart',
  props: ['chartData']
};
</script>

<style>
.recipe-chart {
  /* Not a typo, setting height relative to width */
  height: 80vw;
  max-height: 60vh;
}
</style>