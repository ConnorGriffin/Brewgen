<template>
  <div>
    <h1 class="title is-5">Fermentables</h1>
    <b-table :data="categoryFermentables" :columns="columns" hoverable @click="editFermentable"></b-table>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'FermentableCategoryEditor',
  data() {
    return {
      columns: [
        {
          field: 'name',
          label: 'Name'
        },
        {
          field: 'brand',
          label: 'Brand'
        },
        {
          field: 'styleUsage.min_percent',
          label: 'Min %',
          numeric: true
        },
        {
          field: 'styleUsage.max_percent',
          label: 'Max %',
          numeric: true
        },
        {
          field: 'color',
          label: 'Color (L)',
          numeric: true
        }
      ]
    }
  },
  computed: {
    ...mapGetters([
      'editingFermentableCategory',
      'allFermentables',
      'currentStyleFermentables'
    ]),
    categoryFermentables: function() {
      // Return fermentables in the category with details from allFermentables for each one
      let allFermentables = this.allFermentables

      // Add styleUsage to fermentable detail, set to zero if not used
      allFermentables.forEach(fermentable => {
        let styleUsage = this.fermentableStyleUsage(fermentable.slug)
        if (styleUsage === undefined) {
          Object.assign(fermentable, {
            styleUsage: {
              name: fermentable.name,
              slug: fermentable.slug,
              min_percent: 0,
              max_percent: 0
            }
          })
        } else {
          Object.assign(fermentable, { styleUsage })
        }
      })

      return allFermentables
        .filter(
          fermentable =>
            fermentable.category === this.editingFermentableCategory
        )
        .sort((f1, f2) => {
          if (f1.name < f2.name) return -1
          if (f1.name > f2.name) return 1
          return 0
        })
    }
  },
  methods: {
    editFermentable: function(value) {
      console.log(value)
    },
    fermentableStyleUsage: function(fermentableSlug) {
      return this.currentStyleFermentables.find(
        fermentable => fermentable.slug == fermentableSlug
      )
    }
  }
}
</script>

<style>
</style>