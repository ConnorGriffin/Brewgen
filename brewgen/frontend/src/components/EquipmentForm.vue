<template>
  <div class="container">
    <h1 class="is-size-5">Equipment Profile</h1>
    <section class="section">
      <b-field label="Max Unique Grains" labelPosition="on-border">
        <b-numberinput id="maxUniqueGrains" min="1" max="7" step="1" v-model="maxUniqueGrains" />
      </b-field>
      <b-field label="Batch Volume (Gallons)" labelPosition="on-border">
        <b-numberinput id="target_volume_gallons" step=".25" v-model="targetVolumeGallons" />
      </b-field>
      <b-field label="Mash Efficiency (%)" labelPosition="on-border">
        <b-numberinput id="mash_efficiency" min="1" max="100" step="1" v-model="mashEfficiency" />
      </b-field>
    </section>
  </div>
</template>

<script>
export default {
  name: 'EquipmentForm'
};
</script>

<style>
</style>