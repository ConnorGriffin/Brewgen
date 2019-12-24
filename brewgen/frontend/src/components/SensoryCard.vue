<template>
  <!-- Defines a sensory card, containing a descriptor name, typical values, and tags -->
  <div :class="'card has-background-'+cardBg">
    <div class="card-content">
      <!-- Control buttons on top right -->
      <span class="is-pulled-right">
        <!-- Show edit and delete buttons if type is 'added' -->
        <b-button
          size="is-small"
          style="margin-right: .5rem"
          outlined
          type="is-dark"
          v-if="sensoryData.configured !== undefined"
          @click="editSensory"
        >Edit</b-button>
        <a
          class="delete is-medium"
          v-if="sensoryData.configured !== undefined"
          @click="removeSensory(sensoryData.name)"
        ></a>

        <!-- Show an Add button if not configured -->
        <div class="buttons">
          <b-button
            size="is-small"
            outlined
            @click="addVisibleSensoryDescriptor(sensoryData.name)"
            v-if="sensoryData.configured === undefined && !visibleSensoryDescriptors.includes(sensoryData.name)"
          >Show in constraint builder</b-button>
          <b-button
            size="is-small"
            outlined
            @click="removeVisibleSensoryDescriptor(sensoryData.name)"
            v-if="sensoryData.configured === undefined && visibleSensoryDescriptors.includes(sensoryData.name)"
          >Hide</b-button>
          <b-button
            size="is-small"
            type="is-primary"
            outlined
            @click="showSensoryConfigurator = true"
            v-if="sensoryData.configured === undefined"
          >Add to model</b-button>
        </div>
        <b-modal
          :active.sync="showSensoryConfigurator"
          has-modal-card
          trap-focus
          scroll="keep"
          v-if="possibleSliderRange !== null"
        >
          <SensoryConfigurator
            :styleRange="[sensoryData.style.min, sensoryData.style.max]"
            :possibleRange="possibleSliderRange"
            :name="sensoryData.name | deslug | titleCase"
            :slug="sensoryData.name"
            :tickSpace=".2"
            :sliderMin="sliderMin"
            :sliderMax="sliderMax"
            :startingRange="startingRange()"
            :mode="configuratorMode()"
          />
        </b-modal>
      </span>

      <!-- Descriptor name -->
      <a class="has-text-black" @click="toggleExpanded()">
        <div>
          <div class="descriptor has-text-weight-semibold is-flex">
            <span class="descriptor is-flex" v-if="expandable">
              <b-icon :icon="expanded ? 'chevron-down' : 'chevron-right'" size="is-small"></b-icon>&nbsp;
            </span>
            {{ sensoryData.name | deslug | titleCase }}
          </div>
          <p
            class="content is-size-7 bjcp-sentences"
            v-if="bjcpSentences && (!expandable || (expandable && expanded))"
            v-html="bjcpSentences"
          ></p>
        </div>

        <!-- Descriptor values -->
        <!-- Style Baseline - Show always -->
        <div class="style-sliders" v-if="expanded || !expandable">
          <div class="columns is-gapless is-mobile card-columns">
            <div class="column is-narrow">
              <h1 class="title is-7">Style</h1>
              <h1
                class="title is-7"
                v-if="sensoryData.possible !== undefined && sensoryData.configured === undefined"
              >Possible</h1>
              <h1 class="title is-7" v-if="sensoryData.configured !== undefined">Desired</h1>
            </div>

            <div class="column">
              <!-- Style Range -->
              <b-slider
                :value="styleSliderRange"
                :min="sliderMin"
                :max="sliderMax"
                disabled
                size="is-small"
                type="is-rosewood"
                class="is-style-slider is-slider"
              >
                <b-slider-tick
                  v-for="(tick, index) in sliderTicks(sensoryData.style.min, sensoryData.style.max)"
                  :key="index"
                  :value="tick.value"
                  class="is-tick-hidden"
                >{{ tick.label }}</b-slider-tick>
              </b-slider>

              <!-- Possible Range -->
              <b-slider
                :value="possibleSliderRange"
                :min="sliderMin"
                :max="sliderMax"
                disabled
                size="is-small"
                type="is-info"
                class="is-slider"
                v-if="sensoryData.possible !== undefined && sensoryData.configured === undefined"
              >
                <b-slider-tick
                  v-for="(tick, index) in sliderTicks(possibleSliderRange[0], possibleSliderRange[1])"
                  :key="index"
                  :value="tick.value"
                  class="is-tick-hidden"
                >{{ tick.label }}</b-slider-tick>
              </b-slider>

              <!-- Configured Range -->
              <b-slider
                :value="configuredSliderRange"
                :min="sliderMin"
                :max="sliderMax"
                disabled
                size="is-small"
                type="is-primary"
                class="is-slider"
                v-if="sensoryData.configured !== undefined"
              >
                <b-slider-tick
                  v-for="(tick, index) in sliderTicks(configuredSliderRange[0], configuredSliderRange[1])"
                  :key="index"
                  :value="tick.value"
                  class="is-tick-hidden"
                >{{ tick.label }}</b-slider-tick>
              </b-slider>
            </div>
          </div>
        </div>

        <b-taglist style="margin-top: .5rem">
          <b-tag
            :type="tag.type"
            :key="index"
            v-for="(tag, index) in sensoryData.tags"
          >{{ tag.value }}</b-tag>
        </b-taglist>
      </a>
    </div>

    <b-loading :is-full-page="false" :active.sync="this.isLoading('sensoryData')"></b-loading>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'
import SensoryConfigurator from '@/components/SensoryConfigurator.vue'

export default {
  name: 'SensoryCard',
  props: {
    cardBg: String,
    type: String,
    sensoryData: Object,
    sliderMin: Number,
    sliderMax: Number,
    tickSpace: Number,
    expandable: Boolean
  },
  components: {
    SensoryConfigurator
  },
  data() {
    return {
      showSensoryConfigurator: false,
      styleSliderRange: [
        this.sensoryData.style.min,
        this.sensoryData.style.max
      ],
      expanded: false
    }
  },
  watch: {
    sensoryDescriptorsExpanded: {
      handler(value) {
        if (value === 'expanded') {
          this.expanded = true
        } else if (value === 'collapsed') {
          this.expanded = false
        }
      },
      immediate: true
    }
  },
  filters: {
    titleCase: function(value) {
      value = value.toLowerCase().split(' ')
      for (var i = 0; i < value.length; i++) {
        value[i] = value[i].charAt(0).toUpperCase() + value[i].slice(1)
      }
      return value.join(' ')
    },
    deslug: function(value) {
      if (!value) return ''
      value = value.toString()
      value = value.replace('_', ' ')
      return value.charAt(0).toUpperCase() + value.slice(1)
    }
  },
  computed: {
    ...mapGetters([
      'isLoading',
      'lastSensoryData',
      'lastChangedSensoryDescriptor',
      'visibleSensoryDescriptors'
    ]),
    possibleSliderRange: function() {
      if (this.configuratorData.possible !== undefined) {
        return [
          this.configuratorData.possible.min,
          this.configuratorData.possible.max
        ]
      } else {
        return null
      }
    },
    configuredSliderRange: function() {
      if (this.sensoryData.configured !== undefined) {
        return [
          this.sensoryData.configured.min,
          this.sensoryData.configured.max
        ]
      } else {
        return null
      }
    },
    configuratorData: function() {
      if (
        this.sensoryData.configured !== undefined &&
        this.lastChangedSensoryDescriptor === this.slug
      ) {
        return this.lastSensoryData(this.slug)
      } else {
        return this.sensoryData
      }
    },
    bjcpSentences: function() {
      if (this.sensoryData.name in this.$store.state.brewgen.bjcpSensory) {
        let bjcpSentences = this.$store.state.brewgen.bjcpSensory[
          this.sensoryData.name
        ]

        // Bold the sensory descriptor in the sentences
        let regex = new RegExp(
          '(?<sensory>\\b' +
            this.sensoryData.name.replace('_', ' ') +
            '(y?|ed?)\\b)',
          'gi'
        )
        return bjcpSentences
          .join(' ')
          .replace(regex, '<strong>$<sensory></strong>')
      }
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
    ...mapActions([
      'removeSensoryConstraint',
      'fetchSensoryData',
      'fetchSensoryDataEdit',
      'fetchRecipeData',
      'addVisibleSensoryDescriptor',
      'removeVisibleSensoryDescriptor'
    ]),
    sliderTicks: function(min, max) {
      if (max - min >= this.tickSpace) {
        return [
          {
            value: min,
            label: min
          },
          {
            value: max,
            label: max
          }
        ]
      } else if (min === max) {
        return [
          {
            value: min,
            label: min
          }
        ]
      } else {
        return [
          {
            value: (min + max) / 2,
            label: `${min}\xa0-\xa0${max}`
          }
        ]
      }
    },
    startingRange: function() {
      // Set the starting range to the configured value if one exists
      if (this.sensoryData.configured !== undefined) {
        return [
          this.sensoryData.configured.min,
          this.sensoryData.configured.max
        ]
      } else if (this.sensoryData.possible) {
        return [this.sensoryData.possible.min, this.sensoryData.possible.max]
      } else {
        return null
      }
    },
    removeSensory: function(value) {
      this.removeSensoryConstraint(value)
      this.fetchSensoryData()
      this.fetchRecipeData({ colorOnly: true })
    },
    editSensory: function() {
      // Only fetch sensory data if we aren't editing the last changed value
      if (this.lastChangedSensoryDescriptor !== this.sensoryData.name) {
        this.fetchSensoryDataEdit(this.sensoryData.name)
      }
      this.showSensoryConfigurator = true
    },
    configuratorMode: function() {
      if (this.sensoryData.configured !== undefined) {
        return 'edit'
      } else {
        return null
      }
    },
    toggleExpanded: function() {
      if (this.expandable) {
        this.expanded = !this.expanded
        this.sensoryDescriptorsExpanded = 'mixed'
      }
    }
  }
}
</script>

<style scoped>
.card {
  box-shadow: none;
  border: 1px solid #e3e3e3;
}
/* .b-slider >>> .b-slider-track {
  cursor: default !important;
}
.b-slider >>> .b-slider-fill {
  cursor: default !important;
} */
.b-slider >>> * {
  cursor: default !important;
}
.style-sliders {
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
}
.card-columns {
  margin: 0;
  padding: 0;
}
.card >>> .b-slider-thumb {
  display: none;
}
.is-style-slider {
  margin-bottom: 2rem;
  margin-top: 0.25rem;
}
.is-slider {
  padding-left: 1.5rem;
  padding-right: 1.5rem;
}
.card >>> .column {
  margin-top: 0.5rem;
}
.delete {
  margin-top: 0.1rem;
}
.collapse {
  display: inline;
  margin-left: 0.25rem;
}
.bjcp-sentences {
  margin-top: 0.5rem;
}
.descriptor {
  align-items: center;
}
</style>
