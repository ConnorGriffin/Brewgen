<template>
  <b-row class="mt-3">
    <b-col md="8">
      <span class="h5 ml-2">Style: {{ currentStyle }}</span>
    </b-col>
    <b-col md="4">
      <b-dropdown id="style-dropdown" text="Styles" class="float-right">
        <b-dropdown-item
          :key="style.name"
          v-for="style in styles"
          @click="setCurrentStyle(style)"
        >{{ style.name }}</b-dropdown-item>
      </b-dropdown>
    </b-col>
  </b-row>
</template>

<script>
import { mapActions, mapGetters } from "vuex";
export default {
  name: "StyleDropdown",
  props: ["styles"],
  methods: {
    ...mapActions(["setGrainDataFromStyle"]),
    setCurrentStyle: function(style) {
      this.$store.commit("setCurrentStyle", style.name);
      this.setGrainDataFromStyle(style.slug);
    }
  },
  computed: {
    ...mapGetters(["currentStyle"])
  }
};
</script>

<style>
</style>



