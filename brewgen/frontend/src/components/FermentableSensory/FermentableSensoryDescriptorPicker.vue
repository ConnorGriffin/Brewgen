<template>
  <!-- Defines the sensory picker modal -->
  <div class="modal-card" style="height: calc(100vh - 40px)">
    <header class="modal-card-head">
      <p class="modal-card-title">Fermentable Descriptors</p>
      <a class="delete is-medium is-pulled-right" @click="$parent.close()"></a>
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
        <FermentableSensoryDescriptorCard
          v-for="(sensoryData, index) in currentStyleSensory"
          :key="index"
          :sensoryData="sensoryData"
          :sliderMin="sliderMin"
          :sliderMax="sliderMax"
          cardBg="light"
          :tickSpace="0.2"
        />
      </div>
    </section>
    <footer class="modal-card-foot">
      <button class="button" type="button" @click="$parent.close()">Close</button>
    </footer>
  </div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'
import FermentableSensoryDescriptorCard from '@/components/FermentableSensory/FermentableSensoryDescriptorCard'

export default {
  name: 'FermentableSensoryDescriptorPicker',
  components: {
    FermentableSensoryDescriptorCard
  },
  computed: {
    ...mapGetters(['currentStyleSensory']),
    sliderMin: function() {
      // Returns lowest possible min sensory value in sensory array
      let values = []
      this.currentStyleSensory.forEach(sensoryData => {
        values.push(sensoryData.style.min)
        if (sensoryData.possible !== undefined) {
          values.push(sensoryData.possible.min)
        }
        if (sensoryData.configured !== undefined) {
          values.push(sensoryData.configured.min)
        }
      })
      values.sort()
      return values[0]
    },
    sliderMax: function() {
      // Returns highest possible max sensory value in sensory array
      let values = []
      this.currentStyleSensory.forEach(sensoryData => {
        values.push(sensoryData.style.max)
        if (sensoryData.possible !== undefined) {
          values.push(sensoryData.possible.max)
        }
        if (sensoryData.configured !== undefined) {
          values.push(sensoryData.configured.max)
        }
      })
      values.sort(function(a, b) {
        return b - a
      })
      return values[0]
    }
  }
}
</script>

<style>
</style>
