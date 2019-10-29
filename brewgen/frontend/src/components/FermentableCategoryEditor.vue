<template>
  <div>
    <h1 class="title is-5">
      Category Usage
      <b-button type="is-success" class="is-pulled-right">Save Changes</b-button>
    </h1>
    <b-field grouped group-multiline>
      <b-field label="Minimum Usage">
        <b-field>
          <b-input type="number" v-model.number="minUsage" min="0" max="100"></b-input>
          <b-button class="is-static">%</b-button>
        </b-field>
      </b-field>

      <b-field label="Maximum Usage">
        <b-field>
          <b-input type="number" v-model.number="maxUsage" min="0" max="100"></b-input>
          <b-button class="is-static">%</b-button>
        </b-field>
      </b-field>
    </b-field>

    <h1 class="title is-5" style="margin-top:1.25rem">Category Fermentables</h1>
    <b-table
      :data="categoryFermentables"
      :columns="columns"
      hoverable
      @click="editFermentable"
      default-sort="name"
    ></b-table>

    <!-- Fermentable Configurator -->
    <b-modal :active.sync="showFermentableConfigurator" has-modal-card trap-focus scroll="keep">
      <FermentableConfigurator :fermentable="editingFermentable" />
    </b-modal>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import FermentableConfigurator from '@/components/FermentableConfigurator.vue'

export default {
  name: 'FermentableCategoryEditor',
  props: ['category'],
  components: {
    FermentableConfigurator
  },
  data() {
    return {
      minUsage: null,
      maxUsage: null,
      showFermentableConfigurator: false,
      editingFermentable: null,
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
          field: 'styleUsage.min_percent',
          label: 'Min %',
          numeric: true,
          sortable: true
        },
        {
          field: 'styleUsage.max_percent',
          label: 'Max %',
          numeric: true,
          sortable: true
        },
        {
          field: 'color',
          label: 'Color (L)',
          numeric: true,
          sortable: true
        }
      ]
    }
  },
  watch: {
    editingFermentableCategory: {
      handler() {
        let category = this.fermentableCategories.find(category => {
          return category.name === this.editingFermentableCategory
        })
        this.minUsage = category.min_percent
        this.maxUsage = category.max_percent
      },
      immediate: true
    },
    // Increment min and max usage together if they conflict
    minUsage: _.debounce(
      function(value) {
        this.fixUsage('minUsage')
      },
      600,
      { trailing: true }
    ),
    maxUsage: _.debounce(
      function(value) {
        this.fixUsage('maxUsage')
      },
      600,
      { trailing: true }
    )
  },
  computed: {
    ...mapGetters([
      'fermentableCategories',
      'editingFermentableCategory',
      'allFermentables',
      'currentStyleFermentables',
      'fermentableChanges'
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

      return allFermentables.filter(
        fermentable => fermentable.category === this.editingFermentableCategory
      )
    }
  },
  methods: {
    editFermentable: function(value) {
      let styleUsage = this.fermentableStyleUsage(value.slug)
      if (styleUsage === undefined) {
        Object.assign(value, {
          styleUsage: {
            min_percent: 0,
            max_percent: 0
          }
        })
      } else {
        Object.assign(value, { styleUsage })
      }

      this.editingFermentable = value
      this.showFermentableConfigurator = true
    },
    fermentableStyleUsage: function(fermentableSlug) {
      // Return data from the unsaved fermentableChanges table if it exists, otherwise use the currentStyleFermentables
      try {
        return this.fermentableChanges.find(
          fermentable => fermentable.slug == fermentableSlug
        )
      } catch {
        return this.currentStyleFermentables.find(
          fermentable => fermentable.slug == fermentableSlug
        )
      }
    },
    fixUsage: function(changedInput) {
      if (changedInput === 'minUsage') {
        if (this.minUsage > this.maxUsage) {
          this.maxUsage = this.minUsage
        }
      } else if (changedInput === 'maxUsage') {
        if (this.minUsage > this.maxUsage) {
          this.minUsage = this.maxUsage
        }
      }
    }
  }
}
</script>

<style>
</style>