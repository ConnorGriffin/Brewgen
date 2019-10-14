<template>
  <div class="container">
    <h1 class="title is-size-5">Recipe Designer</h1>
    <div class="columns">
      <!-- Sensory Contstraint Buuidler -->
      <div class="column is-4">
        <SensoryBox />
      </div>
      <!-- Radar Chart -->
      <div class="column is-8">
        <SensoryRadar :chartData="sensoryChartData" />
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import SensoryRadar from '@/components/SensoryRadar.vue';
import SensoryBox from '@/components/SensoryBox.vue';

export default {
  name: 'RecipeBuilder',
  components: {
    SensoryRadar,
    SensoryBox
  },
  computed: {
    ...mapGetters(['sensoryData']),
    sensoryChartData: function() {
      // Get the labels in deslugged title-case
      var chartLabels = this.sensoryData.map(element => {
        var value = element.name;
        value = value
          .replace('_', ' ')
          .toLowerCase()
          .split(' ');
        for (var i = 0; i < value.length; i++) {
          value[i] = value[i].charAt(0).toUpperCase() + value[i].slice(1);
        }
        return value.join(' ');
      });

      // Set Radar chart series data
      var minData = this.sensoryData.map(element => {
        return element.min;
      });
      var maxData = this.sensoryData.map(element => {
        return element.max;
      });

      // Return the data formatted for ApexCharts
      return {
        options: {
          chart: {
            id: 'sensory-min-max'
          },
          plotOptions: {
            radar: {
              fill: {
                colors: ['#5C80BC', '#fff']
              }
            }
          },
          labels: chartLabels.slice(0, 9)
        },
        series: [
          {
            name: 'Minimum',
            data: minData.slice(0, 9)
          },
          {
            name: 'Maximum',
            data: maxData.slice(0, 9)
          }
        ]
      };
    }
  }
};
</script>

<style>
</style>