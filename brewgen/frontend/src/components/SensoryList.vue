<template>
  <div>
    <b-col class="mt-3">
          <h5 class="mb-3">Sensory Possibilities</h5>
    </b-col>
    <b-col>
    <b-row class="mb-4" v-bind:key="'chunk-'+index" v-for="(sensoryChunk, index) in sensoryChunks()">
      <b-col md="4" v-bind:key="sensory.name" v-for="sensory in sensoryChunk">
        <b-card :title="sensory.name | deslug | titleCase">
          Minimum: {{ sensory.min }}
          <br />
          Maximum: {{ sensory.max }}
        </b-card>
      </b-col>
    </b-row>
    </b-col>
  </div>
</template>

<script>
import _ from "lodash";

export default {
  name: "SensoryList",
  props: ["sensoryData"],
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
    sensoryChunks() {
      return _.chunk(this.sensoryData, 3);
    }
  }
};
</script>

<style>
</style>