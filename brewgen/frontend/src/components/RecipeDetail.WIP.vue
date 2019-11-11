<template>
  <div class="card">
    <div class="card-content">
      <h1 class="title is-5" style="margin-top:1.25rem">Recipe {{ recipe.index }}</h1>
      <h1 class="title is-5" style="margin-top:1.25rem">Fermentables</h1>
      <b-table :data="grains" :columns="columns" :default-sort="['use_percent', 'desc']"></b-table>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'RecipeCard',
  props: ['recipe'],
  data() {
    return {
      columns: [
        {
          field: 'name',
          label: 'Name',
          sortable: true
        },
        {
          field: 'brand',
          label: 'Brand',
          sortable: true
        },
        {
          field: 'color',
          label: 'Color (L)',
          numeric: true,
          sortable: true
        },
        {
          field: 'use_percent',
          label: 'Usage (%)',
          numeric: true,
          sortable: true
        },
        {
          field: 'use_pounds',
          label: 'Usage (lbs)',
          sortable: true
        }
      ]
    }
  },
  computed: {
    ...mapGetters(['allFermentables']),
    grains: function() {
      // Merge the recipe fermentables data with the allFermentables data, which is more thorough
      return this.recipe.grains.map(recipeFermentable => {
        recipeFermentable.use_pounds = Number(
          recipeFermentable.use_pounds
        ).toFixed(2)
        let matchedFermentable = this.allFermentables.find(fermentable => {
          return fermentable.slug === recipeFermentable.slug
        })
        Object.assign(recipeFermentable, matchedFermentable)
        return recipeFermentable
      })
      // return fermentableData.sort((f1, f2) => f2.use_percent - f1.use_percent)
    }
  }
}
</script>

<style>
</style>