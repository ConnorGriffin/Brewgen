<template>
  <b-col>
    <apexchart type="bar" :options="chartData.options" :series="chartData.series" />
  </b-col>
</template>

<script>
export default {
  name: 'RecipeChart',
  props: ['chartData']
}
</script>

<style>
</style>
