<template>
  <!-- Recipes output step -->
  <div v-if="!this.isLoading('recipeData')">
    <div class="columns">
      <div class="column is-narrow">
        <!-- Defines recipe filter section -->
        <h1 class="title is-5">Filter Recipes</h1>
        <!-- Wort properties filter -->
        <b-collapse class="card filter" open>
          <div slot="trigger" slot-scope="props" class="card-header" role="button">
            <p class="card-header-title">Wort Properties</p>
            <a class="card-header-icon">
              <b-icon :icon="props.open ? 'caret-down' : 'caret-up'"></b-icon>
            </a>
          </div>
          <div class="card-content">
            <div class="content">
              <!-- Color Filter -->
              <div class="filteritem">
                <b-field label="Color (SRM)">
                  <b-slider
                    v-model="srmRange"
                    type="is-primary"
                    :min="srmSliderRange[0]"
                    :max="srmSliderRange[1]"
                    :step=".1"
                    lazy
                    style="padding-left: .5rem; padding-right: .5rem"
                  >
                    <b-slider-tick :value="srmSliderRange[0]">{{ srmSliderRange[0] }}</b-slider-tick>
                    <b-slider-tick :value="srmSliderRange[1]">{{ srmSliderRange[1] }}</b-slider-tick>
                    <b-slider-tick
                      :value="tickValue"
                      :key="index"
                      v-for="(tickValue, index) in tickValues(srmSliderRange)"
                    ></b-slider-tick>
                  </b-slider>
                </b-field>
              </div>
              <!-- Unique Fermentable Count Filter -->
              <div
                class="filteritem"
                v-if="uniqueFermentablesSliderRange[0] !== uniqueFermentablesSliderRange[1]"
              >
                <b-field label="Unique Fermentables">
                  <b-slider
                    v-model="uniqueFermentablesRange"
                    type="is-primary"
                    :min="uniqueFermentablesSliderRange[0]"
                    :max="uniqueFermentablesSliderRange[1]"
                    :step="1"
                    lazy
                    style="padding-left: .5rem; padding-right: .5rem"
                  >
                    <b-slider-tick
                      :value="uniqueFermentablesSliderRange[0]"
                    >{{ uniqueFermentablesSliderRange[0] }}</b-slider-tick>
                    <b-slider-tick
                      :value="uniqueFermentablesSliderRange[1]"
                    >{{ uniqueFermentablesSliderRange[1] }}</b-slider-tick>
                    <b-slider-tick
                      :value="tickValue"
                      :key="index"
                      v-for="(tickValue, index) in tickValues(uniqueFermentablesSliderRange)"
                    ></b-slider-tick>
                  </b-slider>
                </b-field>
              </div>
            </div>
          </div>
        </b-collapse>

        <!-- Fermentables filter -->
        <b-collapse class="card filter" open>
          <div slot="trigger" slot-scope="props" class="card-header" role="button">
            <p class="card-header-title">Fermentables</p>
            <a class="card-header-icon">
              <b-icon :icon="props.open ? 'caret-down' : 'caret-up'"></b-icon>
            </a>
          </div>
          <div class="card-content">
            <div class="content">
              <div
                class="filteritem"
                :key="index"
                v-for="(category, index) in categoryFermentables"
              >
                <p class="title is-6">{{ category.name | titleCase }}</p>
                <div
                  class="field"
                  :key="index"
                  v-for="(fermentable, index) in category.fermentables"
                >
                  <div class="level">
                    <div class="level-left">
                      <b-checkbox
                        v-model="category.fermentableCheckbox"
                        :native-value="fermentable.slug"
                        class="is-size-6"
                      >
                        {{ fermentable.name }}
                        <br />
                        <p
                          class="is-size-7 has-text-grey"
                        >{{ fermentable.brand | titleCase }} &ndash; {{ fermentable.color }} L</p>
                      </b-checkbox>
                    </div>
                    <div class="level-right">
                      <span
                        class="is-pulled-right is-size-7 has-text-grey"
                        style="margin-left: .5rem"
                      >{{ fermentableRecipeCount(fermentable.slug).join(' | ') }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </b-collapse>
      </div>
      <div class="column">
        <b-pagination
          :total="filteredRecipes.length"
          :current.sync="currentPage"
          :per-page="perPage"
          size="is-small"
        ></b-pagination>
        <hr />
        <RecipeOutputRecipeCard
          v-for="(recipe, index) in currentPageRecipes"
          :key="index"
          :recipe="recipe"
          :has-margin-top="index > 0"
        />
      </div>
    </div>
  </div>
  <b-loading :is-full-page="false" :active.sync="this.isLoading('recipeData')" v-else></b-loading>
</template>

<script>
import { mapGetters } from 'vuex'
import RecipeOutputRecipeCard from '@/components/RecipeOutput/RecipeOutputRecipeCard.vue'
import round from 'lodash'

export default {
  name: 'RecipeOutput',
  components: {
    RecipeOutputRecipeCard
  },
  data() {
    return {
      currentPage: 1,
      perPage: 5,
      categoryFermentables: [],
      srmRange: [],
      srmSliderRange: [],
      uniqueFermentablesRange: []
    }
  },
  watch: {
    recipeData: {
      immediate: true,
      handler() {
        // Set the SRM slider values
        let recipeSrm = this.recipeData.map(recipe => recipe.srm)
        let srmRange = [
          _.round(Math.min(...recipeSrm), 1),
          _.round(Math.max(...recipeSrm), 1)
        ]
        this.srmRange = this.srmSliderRange = srmRange
        this.uniqueFermentablesRange = this.uniqueFermentablesSliderRange

        // Build a checkbox array for each fermentable category
        let newCategoryFermentables = []
        let uniqueFermentableSlugs = this.uniqueFermentables.map(
          fermentable => fermentable.slug
        )
        this.fermentableCategories.forEach(category => {
          let categoryFermentableData = this.allFermentables.filter(
            fermentable => {
              return (
                fermentable.category === category.name &&
                uniqueFermentableSlugs.includes(fermentable.slug)
              )
            }
          )

          if (categoryFermentableData.length > 0) {
            newCategoryFermentables.push({
              name: category.name,
              fermentables: categoryFermentableData,
              fermentableCheckbox: categoryFermentableData.map(
                fermentable => fermentable.slug
              )
            })
          }
        })
        this.categoryFermentables = newCategoryFermentables
      }
    }
  },
  computed: {
    ...mapGetters([
      'recipeData',
      'isLoading',
      'allFermentables',
      'fermentableCategories'
    ]),
    currentPageRecipes: function() {
      let firstItem = (this.currentPage - 1) * this.perPage
      let lastItem = (this.currentPage - 1) * this.perPage + this.perPage
      let pageRecipes = this.filteredRecipes.slice(firstItem, lastItem)
      pageRecipes.forEach((recipe, index) => {
        recipe.index = index + firstItem
      })
      return pageRecipes
    },
    enabledFermentables: function() {
      // List of slugs of enabled fermentables, just combing the checkbox array for each category
      let enabledFermentables = []
      this.categoryFermentables.forEach(category => {
        category.fermentableCheckbox.forEach(fermentable => {
          enabledFermentables.push(fermentable)
        })
      })
      return enabledFermentables
    },
    filteredRecipes: function() {
      return this.recipeData.filter(recipe => {
        // Filter on enabled fermentables
        let enabledRecipeFermentables = recipe.grains.filter(rf => {
          return this.enabledFermentables.includes(rf.slug)
        })
        let roundedSrm = _.round(recipe.srm, 1)
        return (
          enabledRecipeFermentables.length === recipe.grains.length &&
          roundedSrm >= this.srmRange[0] &&
          roundedSrm <= this.srmRange[1] &&
          recipe.grains.length >= this.uniqueFermentablesRange[0] &&
          recipe.grains.length <= this.uniqueFermentablesRange[1]
        )
      })
    },
    uniqueFermentables: function() {
      // Build a list with data for every fermentable used
      var fermentableList = []
      this.recipeData.forEach(recipe => {
        return recipe.grains.forEach(fermentable => {
          if (
            !fermentableList
              .map(fermentable => fermentable.slug)
              .includes(fermentable.slug)
          ) {
            let matchedFermentable = this.allFermentables.find(
              af => af.slug === fermentable.slug
            )
            fermentableList.push(matchedFermentable)
          }
        })
      })
      return fermentableList
    },
    uniqueFermentablesSliderRange: function() {
      // Return the min and max number of unique fermentables in each recipe (for filtering)
      let fermentableCount = this.recipeData.map(recipe => {
        return recipe.grains.length
      })
      return [Math.min(...fermentableCount), Math.max(...fermentableCount)]
    }
  },
  methods: {
    tickValues: function(range) {
      // Return all whole numbers between two values excluding those values
      var ticks = []
      if (Number.isInteger(range[0])) {
        var start = range[0] + 1
      } else {
        var start = Math.ceil(range[0])
      }

      if (Number.isInteger(range[1])) {
        var end = range[1] - 1
      } else {
        var end = Math.floor(range[1])
      }

      for (let i = start; i <= end; i++) {
        ticks.push(i)
      }

      return ticks
    },
    fermentableRecipeCount: function(slug) {
      let filteredCount = this.filteredRecipes.filter(recipe => {
        return recipe.grains.map(grain => grain.slug).includes(slug)
      }).length
      let unfilteredCount = this.recipeData.filter(recipe => {
        return recipe.grains.map(grain => grain.slug).includes(slug)
      }).length
      return [filteredCount, unfilteredCount]
    }
  },
  filters: {
    titleCase: function(value) {
      var ignore = ['and']
      value = value.toLowerCase().split(' ')
      for (var i = 0; i < value.length; i++) {
        if (!ignore.includes(value[i])) {
          value[i] = value[i].charAt(0).toUpperCase() + value[i].slice(1)
        }
      }
      return value.join(' ')
    }
  }
}
</script>

<style scoped>
.filteritem:not(:first-child) {
  padding-top: 1rem;
}
.filter:not(:last-child) {
  margin-bottom: 1rem;
}
</style>