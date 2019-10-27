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
          field: 'min_percent',
          label: 'Min %',
          numeric: true
        },
        {
          field: 'max_percent',
          label: 'Max %',
          numeric: true
        }
      ]
    }
  },
  computed: {
    ...mapGetters(['editingFermentableCategory', 'allFermentables']),
    categoryFermentables: function() {
      return this.allFermentables
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
    }
  }
}
</script>

<style>
</style>