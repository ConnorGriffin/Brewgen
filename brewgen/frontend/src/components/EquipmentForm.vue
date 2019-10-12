<template>
  <div class="modal-card" style="width: auto">
    <header class="modal-card-head">
      <p class="modal-card-title">Equipment Profile</p>
    </header>
    <section class="modal-card-body">
      <b-field label="Batch Volume (Gallons)" labelPosition="on-border">
        <b-numberinput id="target_volume_gallons" step=".25" v-model="targetVolumeGallons" />
      </b-field>
      <b-field label="Mash Efficiency (%)" labelPosition="on-border">
        <b-numberinput id="mash_efficiency" min="1" max="100" step="1" v-model="mashEfficiency" />
      </b-field>
      <b-field label="Max Unique Grains" labelPosition="on-border">
        <b-numberinput id="maxUniqueGrains" min="1" max="7" step="1" v-model="maxUniqueGrains" />
      </b-field>
    </section>
    <footer class="modal-card-foot">
      <button class="button" type="button" @click="$parent.close()">Cancel</button>
      <button class="button is-primary" @click="updateEquipmentProfileAndClose">Save</button>
    </footer>
  </div>
</template>

<script>
import { mapActions } from 'vuex';
export default {
  name: 'EquipmentForm',
  data() {
    return {
      maxUniqueGrains: 0,
      targetVolumeGallons: 0,
      mashEfficiency: 0
    };
  },
  created() {
    this.maxUniqueGrains = this.$store.state.brewgen.equipmentProfile.maxUniqueGrains;
    this.targetVolumeGallons = this.$store.state.brewgen.equipmentProfile.targetVolumeGallons;
    this.mashEfficiency = this.$store.state.brewgen.equipmentProfile.mashEfficiency;
  },
  methods: {
    ...mapActions(['updateEquipmentProfile']),
    updateEquipmentProfileAndClose: function() {
      this.updateEquipmentProfile({
        maxUniqueGrains: this.maxUniqueGrains,
        targetVolumeGallons: this.targetVolumeGallons,
        mashEfficiency: this.mashEfficiency
      });
      this.$parent.close();
    }
  }
};
</script>,

<style>
</style>