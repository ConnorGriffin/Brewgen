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
        <b-tabs v-model="activeTab">
          <b-tab-item label="Sensory">
            <SensoryRadar :chartData="sensoryChartData" />
          </b-tab-item>
          <b-tab-item label="Beer Color">
            <RecipeChart :chartData="recipeChartData" />
          </b-tab-item>
        </b-tabs>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import SensoryRadar from '@/components/SensoryRadar.vue';
import RecipeChart from '@/components/RecipeChart.vue';
import SensoryBox from '@/components/SensoryBox.vue';

export default {
  name: 'RecipeBuilder',
  components: {
    SensoryRadar,
    RecipeChart,
    SensoryBox
  },
  data() {
    return {
      activeTab: 0
    };
  },
  computed: {
    ...mapGetters(['sensoryData', 'recipeColorData', 'currentStyleStats']),
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
    },
    recipeChartData: function() {
      if (this.currentStyleStats != '') {
        var annotations = {
          xaxis: [
            {
              x: this.currentStyleStats.srm.low,
              x2: this.currentStyleStats.srm.high,
              fillColor: '#98C9A3',
              opacity: 0.4,
              label: {
                text: 'Style Range'
              }
            }
          ]
        };
      } else {
        var annotations = {};
      }
      // Return the data formatted for ApexCharts
      return {
        options: {
          chart: {
            id: 'recipe-srm-distribution'
          },
          xaxis: {
            title: {
              text: 'SRM',
              style: {
                fontSize: '1.25rem'
              }
            },
            categories: this.recipeColorData.map(recipe => recipe.srm)
          },
          yaxis: {
            title: {
              text: 'Recipe Count',
              style: {
                fontSize: '1.25rem'
              }
            }
          },
          annotations
        },
        series: [
          {
            name: 'SRM',
            data: this.recipeColorData.map(recipe => recipe.count)
          }
        ]
      };
    }
  }
};
</script>

<style>
</style>