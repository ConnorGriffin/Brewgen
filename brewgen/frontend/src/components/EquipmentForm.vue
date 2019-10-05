<template>
  <div class="m-2 mt-3">
    <h5 class="mb-3">Settings</h5>
    <b-input-group prepend="Max Unique Grains" class="mb-3">
      <b-form-input
        type="number"
        id="maxUniqueGrains"
        min="1"
        max="7"
        step="1"
        v-model="maxUniqueGrains"
      />
    </b-input-group>
    <b-input-group prepend="Batch Volume" append="gallons" class="mb-3">
      <b-form-input
        type="number"
        id="target_volume_gallons"
        step=".25"
        v-model="targetVolumeGallons"
      />
    </b-input-group>
    <b-input-group prepend="Original Gravity" append="SG (1.xxx)" class="mb-3">
      <b-form-input
        type="number"
        id="original_sg"
        min="1"
        max="1.200"
        step=".001"
        v-model="originalSg"
      />
    </b-input-group>
    <b-input-group prepend="Target Color" append="SRM" class="mb-3">
      <b-form-input type="number" id="target_srm" min="1" max="255" step="1" v-model="targetSrm" />
    </b-input-group>
    <b-button @click="fetchSensoryData">Update Sensory Info</b-button>
  </div>
</template>

<script>
import { mapGetters, mapActions } from "vuex";

export default {
  name: "EquipmentForm",
  // data() {
  //   return {
  //     maxUniqueGrains:
  //   };
  // },
  methods: {
    ...mapActions(["fetchSensoryData"])
  },
  computed: {
    maxUniqueGrains: {
      get() {
        return this.$store.state.brewgen.equipmentProfile.maxUniqueGrains;
      },
      set(value) {
        this.$store.commit("setEquipmentSetting", {
          key: "maxUniqueGrains",
          value
        });
      }
    },
    targetVolumeGallons: {
      get() {
        return this.$store.state.brewgen.equipmentProfile.targetVolumeGallons;
      },
      set(value) {
        this.$store.commit("setEquipmentSetting", {
          key: "targetVolumeGallons",
          value
        });
      }
    },
    originalSg: {
      get() {
        return this.$store.state.brewgen.equipmentProfile.originalSg;
      },
      set(value) {
        this.$store.commit("setEquipmentSetting", {
          key: "originalSg",
          value
        });
      }
    },
    targetSrm: {
      get() {
        return this.$store.state.brewgen.equipmentProfile.targetSrm;
      },
      set(value) {
        this.$store.commit("setEquipmentSetting", {
          key: "targetSrm",
          value
        });
      }
    }
  },
  created() {}
};
</script>

<style>
</style>