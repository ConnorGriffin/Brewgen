<template>
  <div class="columns">
    <div class="column is-4">
      <FermentableCategoryList />
    </div>
    <div class="column is-8">
      <FermentableCategoryEditor v-if="editingFermentableCategory" />
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
    ...mapGetters(['editingFermentableCategory'])
  }
}
</script>

<style scoped>
</style>