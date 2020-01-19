<template>
  <!-- Fermentable Category List -->
  <div class="list is-hoverable is-unselectable">
    <a
      :class="'list-item has-background-' + itemBg(category.name)"
      :key="index"
      v-for="(category, index) in fermentableCategories"
      @click="changeCategory(category.name)"
    >
      <span class="title is-6">{{category.name | titleCase }}</span>
      <p :class="textColor(category.name)">
        Usage: {{ category.min_percent }} - {{ category.max_percent }}%
        <span
          class="is-pulled-right"
        >{{ enabledFermentables | inCategory(category.name) | length }}/{{ allFermentables | inCategory(category.name) | length }}</span>
      </p>
    </a>
    <b-modal :active.sync="showUnsavedChanges" has-modal-card trap-focus>
      <FermentableSetupCategoryUnsaved :nextCategory="nextCategory" />
    </b-modal>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'
import FermentableSetupCategoryUnsaved from '@/components/FermentableSetup/FermentableSetupCategoryUnsaved.vue'

export default {
  name: 'FermentableSetupCategoryList',
  components: {
    FermentableSetupCategoryUnsaved
  },
  data() {
    return {
      showUnsavedChanges: false,
      nextCategory: null
    }
  },
  computed: {
    ...mapGetters([
      'fermentableCategories',
      'allFermentables',
      'currentStyleFermentables',
      'fermentableChanges',
      'editingFermentableCategory',
      'fermentableCategoryUsageModified'
    ]),
    enabledFermentables: function() {
      return this.currentStyleFermentables.filter(fermentable => {
        return fermentable.max_percent > 0
      })
    }
  },
  methods: {
    ...mapActions([
      'setEditingFermentableCategory',
      'clearEditingFermentableCategory'
    ]),
    changeCategory(categoryName) {
      // Prompt if there are unsaved changes
      if (
        (this.fermentableChanges.length > 0 ||
          this.fermentableCategoryUsageModified) &&
        this.editingFermentableCategory
      ) {
        // Set next category to null if the current category is clicked
        if (categoryName === this.editingFermentableCategory) {
          this.nextCategory = null
        } else {
          this.nextCategory = categoryName
        }
        // Show the modal
        this.showUnsavedChanges = true
      } else {
        if (this.editingFermentableCategory === categoryName) {
          this.clearEditingFermentableCategory()
        } else {
          this.setEditingFermentableCategory(categoryName)
        }
      }
    },
    itemBg(categoryName) {
      if (categoryName === this.editingFermentableCategory) {
        return 'primary'
      } else {
        return 'white'
      }
    },
    textColor(categoryName) {
      if (categoryName === this.editingFermentableCategory) {
        return 'has-text-black'
      } else {
        return 'has-text-primary'
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
    },
    inCategory(value, category) {
      return value.filter(fermentable => fermentable.category === category)
    },
    length(value) {
      return value.length
    }
  }
}
</script>

<style>
</style>