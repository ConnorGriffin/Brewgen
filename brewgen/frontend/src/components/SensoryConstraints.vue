<template>
  <div>
    <b-col class="mt-3">
      <h5 class="mb-3">Sensory Possibilities</h5>
    </b-col>
    <b-col>
      <b-row
        class="mb-4"
        v-bind:key="'chunk-'+index"
        v-for="(sensoryChunk, index) in sensoryChunks()"
      >
        <b-col md="4" v-bind:key="sensory.name" v-for="sensory in sensoryChunk">
          <SensoryCard :sensoryData="sensory" />
        </b-col>
      </b-row>
    </b-col>
  </div>
</template>

<script>
import _ from "lodash";
import SensoryCard from "@/components/SensoryCard.vue";

export default {
  name: "SensoryList",
  props: ["sensoryData"],
  components: { SensoryCard },
  methods: {
    sensoryChunks() {
      return _.chunk(this.sensoryData, 3);
    }
  }
};
</script>

<style>
</style>