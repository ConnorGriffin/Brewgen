<template>
  <b-list-group-item action @click="$bvModal.show('modal-'+category.name)">
    <h5>{{ category.name | capitalize }}</h5>
    <span>Usage: {{ category.min_percent }} - {{ category.max_percent }}%</span>
    <span class="float-right">Grains: {{ grains.length }}</span>
  </b-list-group-item>
</template>

<script>
import GrainModal from "./GrainModal";

export default {
  name: "CategoryCard",
  props: ["category", "grains"],
  filters: {
    capitalize: function(value) {
      if (!value) return "";
      value = value.toString();
      return value.charAt(0).toUpperCase() + value.slice(1);
    }
  }
};
</script>

<style>
</style>