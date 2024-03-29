<template>
  <div>
    <div class="columns">
      <!-- Sensory Constraint Buuidler -->
      <div class="column is-4">
        <FermentableSensoryDescriptorBox v-if="currentStyleSensory !== ''" />
      </div>
      <!-- Radar Chart -->
      <div class="column is-8">
        <b-tabs v-model="activeTab">
          <b-tab-item label="Sensory">
            <FermentableSensoryChartDescriptors :chartData="sensoryChartData" />
            <b-loading :is-full-page="false" :active.sync="this.isLoading('sensoryData')"></b-loading>
          </b-tab-item>
          <b-tab-item label="Beer Color">
            <FermentableSensoryChartColor :chartData="recipeChartData" />
            <b-loading :is-full-page="false" :active.sync="this.isLoading('recipeData')"></b-loading>
          </b-tab-item>
        </b-tabs>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import FermentableSensoryChartDescriptors from '@/components/FermentableSensory/FermentableSensoryChartDescriptors'
import FermentableSensoryChartColor from '@/components/FermentableSensory/FermentableSensoryChartColor.vue'
import FermentableSensoryDescriptorBox from '@/components/FermentableSensory/FermentableSensoryDescriptorBox'

export default {
  name: 'FermentableSensory',
  components: {
    FermentableSensoryChartDescriptors,
    FermentableSensoryChartColor,
    FermentableSensoryDescriptorBox
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

      var styleMean = sensoryData.map(descriptor => {
        return descriptor.style.mean
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
            name: 'Style Average',
            data: styleMean
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
