<template>
  <!-- Recipes output step -->
  <div v-if="!this.isLoading('recipeData')">
    <div class="columns">
      <div class="column is-narrow">
        <!-- Defines recipe filter section -->
        <h1 class="title is-5">Filter Recipes</h1>
        <b-collapse class="card" open>
          <div slot="trigger" slot-scope="props" class="card-header" role="button">
            <p class="card-header-title">Fermentables</p>
            <a class="card-header-icon">
              <b-icon :icon="props.open ? 'caret-down' : 'caret-up'"></b-icon>
            </a>
          </div>
          <div class="card-content">
            <div class="content">
              <div
                :class="filterClass(index)"
                :key="index"
                v-for="(category, index) in categoryFermentables"
              >
                <p class="title is-6">{{ category.name | titleCase }}</p>
                <div
                  class="field"
                  :key="index"
                  v-for="(fermentable, index) in category.fermentables"
                >
                  <b-checkbox
                    v-model="category.fermentableCheckbox"
                    :native-value="fermentable.slug"
                  >{{ fermentable.name }}</b-checkbox>
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
        <RecipeCard
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
import RecipeCard from '@/components/RecipeCard.vue'

export default {
  name: 'RecipeStep',
  components: {
    RecipeCard
  },
  data() {
    return {
      currentPage: 1,
      perPage: 5,
      categoryFermentables: []
    }
  },
  watch: {
    recipeData: {
      immediate: true,
      handler() {
        console.log('recipe data changed?')
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
        return enabledRecipeFermentables.length === recipe.grains.length
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
    }
  },
  methods: {
    filterClass: function(index) {
      if (index !== 0) {
        return 'has-mt-1rem'
      }
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
.has-mt-1rem {
  margin-top: 1rem;
}
</style>