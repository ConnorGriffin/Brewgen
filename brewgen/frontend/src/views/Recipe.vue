<template>
  <div>
    <!-- Nav bar -->
    <Navbar />
    <!-- Main Body-->
    <div class="container">
      <section class="section">
        <!-- Style and Equipment -->
        <b-steps v-model="activeStep" :animated="true" :has-navigation="true" size="is-small">
          <b-step-item label="Beer Style">
            <h1 class="title has-text-centered">Style</h1>
            <div class="columns">
              <!-- Style Setup -->
              <div class="column">
                <StyleField />
              </div>
              <!-- Equipment Profile -->
              <div class="column">
                <EquipmentField />
              </div>
            </div>
          </b-step-item>
          <!-- Fermentables -->
          <b-step-item label="Fermentables">
            <h1 class="title has-text-centered">Fermentables</h1>
          </b-step-item>
          <!-- Wort Sensory -->
          <b-step-item label="Wort Sensory">
            <h1 class="title has-text-centered">Wort Sensory</h1>
            <WortSensory />
          </b-step-item>
          <!-- Recipes -->
          <b-step-item label="Recipes">
            <h1 class="title has-text-centered">Recipes</h1>Lorem ipsum dolor sit amet.
          </b-step-item>
          <!-- Custom Nav -->
          <template slot="navigation" slot-scope="{previous, next}">
            <div class="buttons">
              <b-button
                outlined
                type="is-danger"
                icon-pack="fas"
                icon-left="backward"
                :disabled="previous.disabled"
                @click.prevent="previous.action"
              >Previous</b-button>
              <b-button
                outlined
                type="is-success"
                icon-pack="fas"
                icon-right="forward"
                :disabled="nextDisabled"
                @click.prevent="next.action"
              >Next</b-button>
            </div>
          </template>
        </b-steps>
      </section>
    </div>
    <!-- Footer -->
    <Footer />
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'
import Navbar from '@/components/Navbar.vue'
import Footer from '@/components/Footer.vue'
import EquipmentField from '@/components/EquipmentField.vue'
import StyleField from '@/components/StyleField.vue'
import WortSensory from '@/components/WortSensory.vue'

export default {
  name: 'Recipe',
  components: {
    Navbar,
    Footer,
    EquipmentField,
    StyleField,
    WortSensory
  },
  data() {
    return {
      activeStep: 0
    }
  },
  filters: {
    inCategory: function(value, categoryName) {
      return value.filter(object => object.category == categoryName)
    }
  },
  methods: {
    ...mapActions([
      'fetchGrainCategories',
      'fetchAllGrains',
      'fetchSensoryData',
      'fetchRecipeData',
      'fetchStyles'
    ]),
    updateRecipeData: function() {
      this.fetchRecipeData({ colorOnly: true })
    }
  },
  computed: {
    ...mapGetters([
      'grainCategories',
      'allGrains',
      'sensoryData',
      'recipeData',
      'recipeColorData',
      'styles',
      'currentStyleStats',
      'currentStyleName'
    ]),
    nextDisabled: function() {
      switch (this.activeStep) {
        case 0: // style
          if (this.currentStyleName === 'None Selected') {
            return true
          }
          return false
          break
      }
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
    },
    sortedStyles: function() {
      return this.styles.sort((a, b) => (a.name > b.name ? 1 : -1))
    }
  },
  created() {
    document.title = 'Brewgen'
    this.fetchStyles()
    // var prom2 = this.$store.dispatch('fetchAllGrains');
    // Promise.all([prom1, prom2]).then(() => {
    //   this.fetchSensoryData();
    //   this.fetchRecipeData({ colorOnly: true });
    // });
  }
}
</script>

<style>
</style>
