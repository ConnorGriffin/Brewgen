<template>
  <div class="keyword-div">
    <!-- Sensory constraint control buttons -->
    <div class="buttons">
      <b-button class="is-primary" @click="showSensoryPicker = true">Add Constraint</b-button>
      <b-dropdown>
        <button class="button" slot="trigger">
          <span>Options</span>
          <b-icon icon="caret-down"></b-icon>
        </button>

        <b-dropdown-item :disabled="clearDisabled" @click="clearSensoryModel">Reset Values</b-dropdown-item>
        <b-dropdown-item
          :disabled="sensoryDescriptorsExpanded === 'expanded'"
          @click="sensoryDescriptorsExpanded = 'expanded'"
        >Expand All</b-dropdown-item>
        <b-dropdown-item
          :disabled="sensoryDescriptorsExpanded === 'collapsed'"
          @click="sensoryDescriptorsExpanded = 'collapsed'"
        >Collapse All</b-dropdown-item>
      </b-dropdown>
    </div>
    <!-- FermentableSensoryDescriptorPicker modal and contents -->
    <b-modal :active.sync="showSensoryPicker" has-modal-card trap-focus scroll="keep">
      <FermentableSensoryDescriptorPicker />
    </b-modal>
    <!-- Box containing sensory constraint cards -->
    <div class="keyword-box">
      <FermentableSensoryDescriptorCard
        v-for="(sensoryData, index) in filteredStyleSensory"
        :key="index"
        :sensoryData="sensoryData"
        :sliderMin="sliderMin"
        :sliderMax="sliderMax"
        cardBg="white"
        :tickSpace="1"
        :expandable="true"
      />
    </div>
  </div>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'
import FermentableSensoryDescriptorCard from '@/components/FermentableSensory/FermentableSensoryDescriptorCard.vue'
import FermentableSensoryDescriptorPicker from '@/components/FermentableSensory/FermentableSensoryDescriptorPicker.vue'

export default {
  name: 'FermentableSensoryDescriptorBox',
  components: {
    FermentableSensoryDescriptorCard,
    FermentableSensoryDescriptorPicker
  },
  data() {
    return {
      showSensoryPicker: false,
      sensoryExpanded: false
    }
  },
  computed: {
    ...mapGetters([
      'currentStyleSensory',
      'isLoading',
      'visibleSensoryDescriptors'
    ]),
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
    },
    filteredStyleSensory: function() {
      return this.currentStyleSensory.filter(sensoryData => {
        // Always show configured values
        if (sensoryData.configured !== undefined) {
          return true
        } else {
          // Return items in visibleSensoryDescriptors
          return this.visibleSensoryDescriptors.includes(sensoryData.name)
        }
      })
    },
    clearDisabled: function() {
      let configuredSensory = this.currentStyleSensory.filter(sensoryData => {
        return sensoryData.configured !== undefined
      })
      return !(configuredSensory.length > 0)
    },
    sensoryDescriptorsExpanded: {
      get() {
        return this.$store.state.brewgen.sensoryDescriptorsExpanded
      },
      set(value) {
        this.$store.commit('setSensoryDescriptorsExpanded', value)
      }
    }
  },
  methods: {
    ...mapActions(['fetchSensoryData', 'fetchRecipeData']),
    clearSensoryModel: function() {
      this.$store.commit('clearSensoryConfiguredValues')
      this.fetchSensoryData()
      this.fetchRecipeData({ colorOnly: true })
    }
  }
}
</script>

<style scoped>
.is-keyword-button {
  width: 100%;
}
.keyword-box {
  padding: 0px;
  height: 100%;
  max-height: 60vh;
  overflow-y: auto;
}
.keyword-div {
  height: 100%;
  max-height: 60vh;
  margin-bottom: 3rem;
}
</style>
