<template>
  <div>
    <b-col class="mt-3">
      <h5 class="mb-3">Sensory Possibilities</h5>
    </b-col>
    <b-col>
      <apexchart
        type="radar"
        :options="sensoryChartData.options"
        :series="sensoryChartData.series"
      />
    </b-col>
  </div>
</template>

<script>
export default {
  name: "SensoryRadar",
  props: ["sensoryChartData"]
};
</script>

<style>
</style>