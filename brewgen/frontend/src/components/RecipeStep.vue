<template>
  <!-- Recipes output step -->
  <div v-if="!this.isLoading('recipeData')">
    <b-pagination
      :total="recipeData.length"
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
      perPage: 5
    }
  },
  computed: {
    ...mapGetters(['recipeData', 'isLoading']),
    currentPageRecipes: function() {
      let firstItem = (this.currentPage - 1) * this.perPage
      let lastItem = (this.currentPage - 1) * this.perPage + this.perPage
      let pageRecipes = this.recipeData.slice(firstItem, lastItem)
      pageRecipes.forEach((recipe, index) => {
        recipe.index = index + firstItem
      })
      return pageRecipes
    }
  }
}
</script>

<style>
</style>