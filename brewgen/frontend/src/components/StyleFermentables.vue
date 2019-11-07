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