<template>
  <div>
    <b-col class="mt-3">
      <h5 class="mb-3">Recipe Distribution</h5>
    </b-col>
    <b-col>
      <!-- <apexchart type="line" :options="chartData.options" :series="chartData.series" /> -->
    </b-col>
  </div>
</template>

<script>
export default {
  name: "RecipeChart",
  props: ["chartData"]
};
</script>

<style>
</style>