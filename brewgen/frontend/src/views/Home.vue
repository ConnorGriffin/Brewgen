<template>
  <div>
    <!-- Nav bar -->
    <Navbar />
    <!-- Main Body-->
    <div class="container">
      <section class="section">
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
      </section>
      <!-- Recipe Builder -->
      <section class="section">
        <RecipeBuilder v-if="currentStyleName !== 'None Selected'" />
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
import RecipeBuilder from '@/components/RecipeBuilder.vue'

export default {
  name: 'Home',
  components: {
    Navbar,
    Footer,
    EquipmentField,
    StyleField,
    RecipeBuilder
  },
  filters: {
    inCategory: function (value, categoryName) {
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
    updateRecipeData: function () {
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
    recipeChartData: function () {
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
    sortedStyles: function () {
      return this.styles.sort((a, b) => (a.name > b.name ? 1 : -1))
    }
  },
  created () {
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
