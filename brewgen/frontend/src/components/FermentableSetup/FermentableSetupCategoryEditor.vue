<template>
  <div>
    <b-message
      type="is-danger"
      has-icon
      v-if="!isPossible"
    >Sum of minimum usage for top {{ equipmentProfile.maxUniqueFermentables }} fermentables is less than category minimum usage ({{ minUsage }}%).</b-message>
    <h1 class="title is-5">
      Category Usage
      <b-button
        type="is-success"
        class="is-pulled-right"
        @click="saveChanges"
        :disabled="!isSaveable"
      >Save Changes</b-button>
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

      <b-field label="Max Fermentables">
        <b-field>
          <b-input
            type="number"
            v-model.number="uniqueFermentableCount"
            min="0"
            :max="equipmentProfile.maxUniqueFermentables"
          ></b-input>
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
      <FermentableSetupFermentableEditor :fermentable="editingFermentable" />
    </b-modal>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'
import FermentableSetupFermentableEditor from '@/components/FermentableSetup/FermentableSetupFermentableEditor.vue'

export default {
  name: 'FermentableSetupCategoryEditor',
  components: {
    FermentableSetupFermentableEditor
  },
  data() {
    return {
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
        this.setFermentableCategoryUsageEdit({
          minUsage: category.min_percent,
          maxUsage: category.max_percent,
          uniqueFermentableCount: category.unique_fermentable_count
        })
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
      'fermentableChanges',
      'equipmentProfile',
      'fermentableCategoryUsageEdit',
      'fermentableCategoryUsageModified'
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
    },
    isPossible: function() {
      // Check if we can hit the minimum usage % for the category
      let minValues = this.categoryFermentables
        .map(fermentable => {
          return fermentable.styleUsage.min_percent
        })
        .sort((a, b) => b - a)

      let minUsage = minValues
        .slice(0, this.equipmentProfile.maxUniqueFermentables)
        .reduce((sum, usage) => sum + usage)

      if (minUsage >= this.minUsage) {
        return true
      } else {
        return false
      }
    },
    isSaveable: function() {
      if (
        !this.fermentableCategoryUsageModified &&
        this.fermentableChanges.length === 0
      ) {
        return false
      } else {
        if (this.isPossible) {
          return true
        } else {
          return false
        }
      }
    },
    minUsage: {
      get() {
        return this.fermentableCategoryUsageEdit.minUsage
      },
      set(value) {
        this.setFermentableCategoryUsageEdit({
          minUsage: value,
          maxUsage: this.maxUsage,
          uniqueFermentableCount: this.uniqueFermentableCount
        })
      }
    },
    maxUsage: {
      get() {
        return this.fermentableCategoryUsageEdit.maxUsage
      },
      set(value) {
        this.setFermentableCategoryUsageEdit({
          minUsage: this.minUsage,
          maxUsage: value,
          uniqueFermentableCount: this.uniqueFermentableCount
        })
      }
    },
    uniqueFermentableCount: {
      get() {
        return this.fermentableCategoryUsageEdit.uniqueFermentableCount
      },
      set(value) {
        this.setFermentableCategoryUsageEdit({
          minUsage: this.minUsage,
          maxUsage: this.maxUsage,
          uniqueFermentableCount: value
        })
      }
    }
  },
  methods: {
    ...mapActions([
      'fetchFermentableModelValidity',
      'saveFermentableCategoryChanges',
      'setFermentableCategoryUsageEdit'
    ]),
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
      let usage = this.fermentableChanges.find(
        fermentable => fermentable.slug == fermentableSlug
      )

      if (usage) {
        return usage.styleUsage
      } else {
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
    },
    saveChanges: function() {
      // Commit the category changes
      let usage = {
        name: this.editingFermentableCategory,
        min_percent: this.minUsage,
        max_percent: this.maxUsage
      }
      this.saveFermentableCategoryChanges(usage)
      this.fetchFermentableModelValidity()
    }
  }
}
</script>

<style>
</style>