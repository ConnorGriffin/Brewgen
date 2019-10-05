<template>
  <b-card>
    <b-card-title>
      {{ sensoryData.name | deslug | titleCase }}
      <span class="float-right">
        <b-button variant="outline" @click="toggleSensoryCardLock">
          <font-awesome-icon icon="lock-open"></font-awesome-icon>
        </b-button>
      </span>
    </b-card-title>
    <b-row>
      <b-col cols="6">
        <span>Min: {{ sensoryData.min }}</span>
        <span class="float-right">{{ minValue }}</span>
        <br />
        <span>Max: {{ sensoryData.max }}</span>
        <span class="float-right">{{ maxValue }}</span>
      </b-col>
      <b-col cols="6">
        <b-form-input
          id="range-1"
          v-model="minValue"
          type="range"
          :min="sensoryData.min"
          :max="sensoryData.max"
          step=".01"
        ></b-form-input>
        <b-form-input
          id="range-1"
          v-model="maxValue"
          type="range"
          :min="sensoryData.min"
          :max="sensoryData.max"
          step=".01"
        ></b-form-input>
      </b-col>
    </b-row>
  </b-card>
</template>

<script>
import { mapActions, mapGetters } from "vuex";
export default {
  name: "SensoryCard",
  props: ["sensoryData"],
  data() {
    return {
      minValue: "",
      maxValue: ""
    };
  },
  created() {
    this.minValue = this.sensoryData.min;
    this.maxValue = this.sensoryData.max;
  },
  filters: {
    titleCase: function(value) {
      value = value.toLowerCase().split(" ");
      for (var i = 0; i < value.length; i++) {
        value[i] = value[i].charAt(0).toUpperCase() + value[i].slice(1);
      }
      return value.join(" ");
    },
    deslug: function(value) {
      if (!value) return "";
      value = value.toString();
      value = value.replace("_", " ");
      return value.charAt(0).toUpperCase() + value.slice(1);
    }
  },
  methods: {
    ...mapActions([
      "fetchSensoryData",
      "removeSensoryFromModel",
      "addSensoryToModel"
    ]),
    toggleSensoryCardLock: function() {
      // Remove if already in model, otherwise add
      this.removeSensoryFromModel(this.sensoryData.name);
      this.addSensoryToModel({
        name: this.sensoryData.name,
        min: this.minValue,
        max: this.maxValue
      });
      this.fetchSensoryData();
    }
  },
  computed: {
    ...mapGetters(["sensoryModel"])
  }
};
</script>

<style>
</style>