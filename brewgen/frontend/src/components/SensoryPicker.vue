<template>
  <!-- Defines the sensory picker modal -->
  <div class="modal-card" style="height: calc(100vh - 40px)">
    <header class="modal-card-head">
      <p class="modal-card-title">Styles</p>
    </header>
    <section class="modal-card-body" style="height:100%">
      <!-- <b-input
          icon="search"
          placeholder="Filter"
          type="search"
          style="margin-bottom: .5rem"
          v-model="styleListFilter"
          ref="styleFilter"
          autofocus
      ></b-input>-->
      <div class="list">
        <SensoryCard
          :sensoryData="sensoryData"
          :key="index"
          v-for="(sensoryData, index) in currentStyleSensory"
          type="picker"
        />
      </div>
    </section>
    <footer class="modal-card-foot">
      <button class="button" type="button" @click="$parent.close()">Cancel</button>
    </footer>
  </div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import SensoryCard from '@/components/SensoryCard';

export default {
  name: 'SensoryPicker',
  components: {
    SensoryCard
  },
  computed: {
    ...mapGetters(['currentStyleSensory'])
  }
};
</script>

<style>
</style>