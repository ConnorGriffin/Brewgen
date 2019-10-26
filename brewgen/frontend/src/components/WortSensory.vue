<template>
  <div class="container">
    <div class="columns">
      <!-- Sensory Constraint Buuidler -->
      <div class="column is-4">
        <SensoryBox v-if="currentStyleSensory !== ''" />
      </div>
      <!-- Radar Chart -->
      <div class="column is-8">
        <b-tabs v-model="activeTab">
          <b-tab-item label="Sensory">
            <SensoryRadar :chartData="sensoryChartData" />
            <b-loading :is-full-page="false" :active.sync="this.isLoading('sensoryData')"></b-loading>
          </b-tab-item>
          <b-tab-item label="Beer Color">
            <RecipeChart :chartData="recipeChartData" />
            <b-loading :is-full-page="false" :active.sync="this.isLoading('recipeData')"></b-loading>
          </b-tab-item>
        </b-tabs>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import SensoryRadar from '@/components/SensoryRadar.vue'
import RecipeChart from '@/components/RecipeChart.vue'
import SensoryBox from '@/components/SensoryBox.vue'

export default {
  name: 'WortSensory',
  components: {
    SensoryRadar,
    RecipeChart,
    SensoryBox
  },
  data() {
    return {
      activeTab: 0
    }
  },
  computed: {
    ...mapGetters([
      'sensoryData',
      'recipeColorData',
      'currentStyleStats',
      'currentStyleSensory',
      'isLoading'
    ]),
    sensoryChartData: function() {
      // Get the labels in deslugged title-case
      var chartLabels = this.sensoryData.map(element => {
        var value = element.name
        value = value
          .replace('_', ' ')
          .toLowerCase()
          .split(' ')
        for (var i = 0; i < value.length; i++) {
          value[i] = value[i].charAt(0).toUpperCase() + value[i].slice(1)
        }
        return value.join(' ')
      })

      // Set Radar chart series data
      var minData = this.sensoryData.map(element => {
        return element.min
      })
      var maxData = this.sensoryData.map(element => {
        return element.max
      })

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
      }
    },
    recipeChartData: function() {
      if (this.currentStyleStats != '') {
        var annotations = {
          xaxis: [
            {
              x: this.$store.state.brewgen.beerProfile.minSrm,
              x2: this.$store.state.brewgen.beerProfile.maxSrm,
              fillColor: '#98C9A3',
              opacity: 0.4,
              label: {
                text: 'Target Color'
              }
            }
          ]
        }
      } else {
        var annotations = {}
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
      }
    }
  }
}
</script>

<style>
</style>
