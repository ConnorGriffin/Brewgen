<template>
  <div class="container">
    <h1 class="title is-4">
      Equipment Profile
      <div class="buttons is-pulled-right">
        <b-button size="is-small" @click="showEditEquipmentModal = true">Edit</b-button>
        <b-modal :active.sync="showEditEquipmentModal" has-modal-card trap-focus>
          <EquipmentForm />
        </b-modal>
      </div>
    </h1>
    <p>
      <span class="has-text-weight-semibold">Batch Volume:</span>
      <span>&nbsp;{{ targetVolumeGallons }} gal</span>
    </p>
    <p>
      <span class="has-text-weight-semibold">Mash Efficiency:</span>
      <span>&nbsp;{{ mashEfficiency }} %</span>
    </p>
    <p>
      <span class="has-text-weight-semibold">Max Unique Fermentables:</span>
      <span>&nbsp;{{ maxUniqueFermentables }}</span>
    </p>
  </div>
</template>

<script>
import EquipmentForm from '@/components/EquipmentForm.vue'

export default {
  name: 'EquipmentField',
  components: {
    EquipmentForm
  },
  data() {
    return {
      showEditEquipmentModal: false
    }
  },
  computed: {
    maxUniqueFermentables: {
      get() {
        return this.$store.state.brewgen.equipmentProfile.maxUniqueFermentables
      }
    },
    targetVolumeGallons: {
      get() {
        return this.$store.state.brewgen.equipmentProfile.targetVolumeGallons
      }
    },
    mashEfficiency: {
      get() {
        return this.$store.state.brewgen.equipmentProfile.mashEfficiency
      }
    }
  }
}
</script>

<style>
</style>
