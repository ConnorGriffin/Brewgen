<template>
  <div>
    <b-message
      title="Invalid Fermentable Model"
      type="is-danger"
      :closable="false"
      has-icon
      v-if="fermentableModelValidity === false"
    >Please adjust your category/fermentable usage numbers, or your Max Unique Fermentables to ensure the fermentable model is mathematically possible.</b-message>

    <div class="columns">
      <div class="column is-4">
        <FermentableCategoryList />
      </div>
      <div class="column is-8">
        <FermentableCategoryEditor v-if="editingFermentableCategory" />
        <b-message type="is-primary" v-else>
          <p>
            Recipes will be generated using a mix of different fermentables. A fermentable's min/max usage amounts will be considered only if the fermentable is included in the recipe, so multiple fermentables in a category
            can have minimum usage amounts totaling more than 100% without causing an issue.
          </p>
          <br />
          <p>Category usage amounts will be followed no matter what, meaning if a category has a minimum usage greater than 0%, at least one fermentable from that category will end up in every recipe.</p>
          <br />
          <p>Category and fermentable usage amounts are automatically configured to remain within the style guidelines, but you can modify them to your liking. Select a fermentable category to modify the usage amounts of that category and the fermentables within it.</p>
        </b-message>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import FermentableCategoryList from '@/components/FermentableCategoryList.vue'
import FermentableCategoryEditor from '@/components/FermentableCategoryEditor.vue'

export default {
  name: 'StyleFermentables',
  components: {
    FermentableCategoryList,
    FermentableCategoryEditor
  },
  data() {
    return {}
  },
  computed: {
    ...mapGetters(['editingFermentableCategory', 'fermentableModelValidity'])
  }
}
</script>

<style scoped>
</style>