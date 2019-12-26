<template>
  <div>
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
      'visibleSensoryDescriptors',
      'isLoading'
    ]),
    sensoryChartData: function() {
      // Get the labels in deslugged title-case
      var chartLabels = this.visibleSensoryDescriptors.map(value => {
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
      let sensoryData = this.visibleSensoryDescriptors.map(descriptor => {
        return this.currentStyleSensory.find(
          sensory => sensory.name === descriptor
        )
      })

      var minData = sensoryData.map(descriptor => {
        if (descriptor.possible) {
          return descriptor.possible.min
        } else {
          return descriptor.style.min
        }
      })

      var maxData = sensoryData.map(descriptor => {
        if (descriptor.possible) {
          return descriptor.possible.max
        } else {
          return descriptor.style.max
        }
      })

      var styleAvg = sensoryData.map(descriptor => {
        return (descriptor.style.min + descriptor.style.max) / 2
      })

      // Return the data formatted for ApexCharts
      return {
        options: {
          chart: {
            id: 'sensory-min-max'
          },
          fill: {
            opacity: 0.1
          },
          colors: ['#39A9DB', '#59CD90', '#EE6352'],
          plotOptions: {
            radar: {
              polygons: {
                strokeColor: '#e9e9e9',
                fill: {
                  colors: ['#f7f9f9', '#fbfffe']
                }
              }
            }
          },
          labels: chartLabels
        },
        series: [
          {
            name: 'Minimum',
            data: minData
          },
          {
            name: 'Maximum',
            data: maxData
          },
          {
            name: 'Style Avg.',
            data: styleAvg
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
              opacity: 0.1,
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
          colors: ['#39A9DB'],
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
