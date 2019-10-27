<template>
  <!-- Fermentable Category List -->
  <div class="list is-hoverable">
    <a
      :class="'list-item has-background-' + itemBg(category.name)"
      :key="index"
      v-for="(category, index) in fermentableCategories"
      @click="setEditingFermentableCategory(category.name)"
    >
      <span class="title is-6">{{category.name | titleCase }}</span>
      <p :class="textColor(category.name)">
        Usage: {{ category.min_percent }} - {{ category.max_percent }}%
        <span
          class="is-pulled-right"
        >{{ currentStyleFermentables | inCategory(category.name) | length }}/{{ allFermentables | inCategory(category.name) | length }}</span>
      </p>
    </a>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'FermentableCategoryList',
  computed: {
    ...mapGetters([
      'fermentableCategories',
      'allFermentables',
      'currentStyleFermentables'
    ]),
    editingFermentableCategory: {
      get() {
        return this.$store.state.brewgen.editingFermentableCategory
      },
      set(value) {
        this.$store.commit('setEditingFermentableCategory', value)
      }
    }
  },
  methods: {
    setEditingFermentableCategory(categoryName) {
      if (this.editingFermentableCategory === categoryName) {
        this.editingFermentableCategory = null
      } else {
        this.editingFermentableCategory = categoryName
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
        return 'has-text-white'
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