<template>
  <div :class="'card ' + cardClass">
    <header class="card-header">
      <p class="card-header-title">Recipe {{ recipe.index + 1 }}</p>
      <p class="card-header-title has-text-right is-block">SRM:&nbsp;{{ recipe.srm.toFixed(1) }}</p>
    </header>
    <div class="card-content">
      <b-table :data="grainTableData" :columns="columns" :mobile-cards="false" narrowed></b-table>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'RecipeCard',
  props: ['recipe', 'has-margin-top'],
  data() {
    return {
      columns: [
        {
          field: 'name'
        },
        {
          field: 'color'
        },
        {
          field: 'percent'
        }
      ]
    }
  },
  computed: {
    ...mapGetters(['allFermentables']),
    grains: function() {
      // Merge the recipe fermentables data with the allFermentables data, which is more thorough
      let fermentableData = this.recipe.grains.map(recipeFermentable => {
        recipeFermentable.use_pounds = Number(
          recipeFermentable.use_pounds
        ).toFixed(2)
        let matchedFermentable = this.allFermentables.find(fermentable => {
          return fermentable.slug === recipeFermentable.slug
        })
        Object.assign(recipeFermentable, matchedFermentable)
        return recipeFermentable
      })
      return fermentableData.sort((f1, f2) => f2.use_percent - f1.use_percent)
    },
    grainTableData: function() {
      return this.grains.map(grain => {
        return {
          name: `${grain.brand} ${grain.name}`,
          color: `${grain.color} L`,
          percent: `${grain.use_percent}%`
        }
      })
    },
    cardClass: function() {
      // If this isn't the first card we want to add a margin to space them a bit
      if (this.hasMarginTop) {
        return 'is-not-first'
      } else {
        return ''
      }
    }
  }
}
</script>

<style scoped>
.card.is-not-first {
  margin-top: 1rem;
}
* >>> thead {
  display: none !important;
}
</style>