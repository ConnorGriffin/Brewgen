<template>
  <div class="container">
    <nav class="level">
      <div class="level-left">
        <h1 class="title is-size-5">Equipment Profile</h1>
      </div>
      <div class="level-right">
        <div class="buttons">
          <b-button size="is-small" @click="clickMe">Change</b-button>
          <b-button size="is-small" @click="clickMe">Edit</b-button>
        </div>
      </div>
    </nav>
    <p>
      <span class="has-text-weight-semibold">Batch Volume:</span>
      <span>&nbsp;{{ targetVolumeGallons }} gal</span>
    </p>
    <p>
      <span class="has-text-weight-semibold">Mash Efficiency:</span>
      <span>&nbsp;{{ mashEfficiency }} %</span>
    </p>
    <p>
      <span class="has-text-weight-semibold">Max Unique Grains:</span>
      <span>&nbsp;{{ maxUniqueGrains }}</span>
    </p>
  </div>
</template>

<script>
export default {
  name: 'EquipmentField',
  computed: {
    maxUniqueGrains: {
      get() {
        return this.$store.state.brewgen.equipmentProfile.maxUniqueGrains;
      }
    },
    targetVolumeGallons: {
      get() {
        return this.$store.state.brewgen.equipmentProfile.targetVolumeGallons;
      }
    },
    mashEfficiency: {
      get() {
        return this.$store.state.brewgen.equipmentProfile.mashEfficiency;
      }
    }
  }
};
</script>

<style>
</style>