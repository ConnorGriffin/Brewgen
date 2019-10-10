<template>
  <!-- Locked cards - locked by user-->
  <b-card v-if="inModel()" bg-variant="primary" text-variant="white">
    <b-card-title>
      {{ sensoryData.name | deslug | titleCase }}
      <span class="float-right">
        <b-button variant="outline" @click="toggleSensoryCardLock">
          <font-awesome-icon icon="lock" class="white"></font-awesome-icon>
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
          disabled
        ></b-form-input>
        <b-form-input
          id="range-1"
          v-model="maxValue"
          type="range"
          :min="sensoryData.min"
          :max="sensoryData.max"
          step=".01"
          disabled
        ></b-form-input>
      </b-col>
    </b-row>
  </b-card>
  <!-- Unlocked cards -->
  <b-card v-else-if="sensoryData.min != sensoryData.max">
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
  <!-- Locked cards due to being unmodifiable cards -->
  <b-card
    v-else-if="sensoryData.min == sensoryData.max && !inModel()"
    bg-variant="light"
    class="card-disabled"
  >
    <b-card-title>
      {{ sensoryData.name | deslug | titleCase }}
      <span class="float-right">
        <b-button variant="outline" disabled>
          <font-awesome-icon icon="lock" class="card-disabled"></font-awesome-icon>
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
          disabled
        ></b-form-input>
        <b-form-input
          id="range-1"
          v-model="maxValue"
          type="range"
          :min="sensoryData.min"
          :max="sensoryData.max"
          step=".01"
          disabled
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
    this.updateSliders();
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
      // toasted_marshmallow -> toasted marshmallow
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
      "addSensoryToModel",
      "fetchRecipeData"
    ]),
    updateSliders: function() {
      // Set the slider initial values to the min and max possible
      this.minValue = this.sensoryData.min;
      this.maxValue = this.sensoryData.max;
    },
    toggleSensoryCardLock: function() {
      // Remove if already in model, otherwise add
      if (this.inModel()) {
        this.removeSensoryFromModel(this.sensoryData.name);
      } else {
        this.addSensoryToModel({
          name: this.sensoryData.name,
          min: this.minValue,
          max: this.maxValue
        });
      }
      this.fetchSensoryData();
      this.fetchRecipeData({ colorOnly: true });
    },
    inModel: function() {
      // Return true if value is in the model, false if not
      var inModel = this.sensoryModel.find(
        sensory => sensory.name == this.sensoryData.name
      );
      if (inModel !== undefined) {
        return true;
      } else {
        return false;
      }
    }
  },
  computed: {
    ...mapGetters(["sensoryModel"])
  },
  watch: {
    sensoryData: function(value) {
      // Update the sensory sliders positions if the dat changes
      this.updateSliders();
    }
  }
};
</script>

<style>
.white {
  color: #ffffff;
}
.card-disabled {
  color: gray;
}
</style>