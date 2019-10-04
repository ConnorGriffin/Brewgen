<template>
  <div class="ml-2 mr-2 mb-2">
    <h5 class="mb-3">Settings</h5>
    <b-input-group prepend="Max Unique Grains" class="mb-3">
      <b-form-input type="number" id="max_unique_grains" min="1" max="7" step="1" value="4" />
    </b-input-group>
    <b-input-group prepend="Batch Volume" append="gallons" class="mb-3">
      <b-form-input type="number" id="target_volume_gallons" step=".25" value="5.5" />
    </b-input-group>
    <b-input-group prepend="Original Gravity" append="SG (1.xxx)" class="mb-3">
      <b-form-input type="number" id="original_sg" min="1" max="1.200" step=".001" value="1.050" />
    </b-input-group>
    <b-input-group prepend="Target Color" append="SRM">
      <b-form-input type="number" id="target_srm" min="1" max="255" step="1" value="6" />
    </b-input-group>
  </div>
</template>

<script>
export default {
  name: "EquipmentForm"
};
</script>

<style>
</style>