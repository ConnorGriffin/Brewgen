<template>
  <!-- Defines the Sensory Configurator modal -->
  <div class="modal-card">
    <header class="modal-card-head">
      <p class="modal-card-title">Unsaved Changes</p>
      <a class="delete is-medium is-pulled-right" @click="$parent.close()"></a>
    </header>
    <div class="modal-card-body">There are unsaved changes to the current category.</div>
    <footer class="modal-card-foot">
      <b-button @click="$parent.close()">Cancel</b-button>
      <b-button type="is-primary" @click="save">Save</b-button>
      <b-button type="is-danger" outlined @click="discard">Discard</b-button>
    </footer>
  </div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'FermentableSetupCategoryUnsaved',
  props: ['nextCategory'],
  methods: {
    ...mapActions([
      'setEditingFermentableCategory',
      'saveFermentableCategoryChanges',
      'discardFermentableCategoryChanges'
    ]),
    save: function() {
      this.saveFermentableCategoryChanges()
      this.setEditingFermentableCategory(this.nextCategory)
      this.$parent.close()
    },
    discard: function() {
      this.discardFermentableCategoryChanges()
      this.setEditingFermentableCategory(this.nextCategory)
      this.$parent.close()
    }
  }
}
</script>

<style scoped>
</style>
