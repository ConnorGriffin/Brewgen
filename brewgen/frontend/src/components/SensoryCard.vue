<template>
  <!-- Defines a sensory card, containing a descriptor name, typical values, and tags -->
  <div :class="'card has-background-'+cardBg">
    <div class="card-content">
      <!-- Control buttons on top right -->
      <span class="is-pulled-right">
        <!-- Show edit and delete buttons if type is 'added' -->
        <b-button size="is-small" style="margin-right: .5rem" v-if="type === 'added'">Edit</b-button>
        <a class="delete is-medium" v-if="type === 'added'"></a>

        <!-- Show an Add button if type is 'picker' -->
        <b-button
          size="is-small"
          type="is-primary"
          v-if="type === 'picker'"
          @click="showSensoryConfigurator = true"
        >Add to model</b-button>
        <b-modal :active.sync="showSensoryConfigurator" has-modal-card trap-focus scroll="keep">
          <SensoryConfigurator
            :styleRange="[sensoryData.style.min, sensoryData.style.max]"
            :possibleRange="[sensoryData.possible.min, sensoryData.possible.max]"
            :name="sensoryData.name | deslug | titleCase"
            :tickSpace="tickSpace"
            :sliderMin="sliderMin"
            :sliderMax="sliderMax"
          />
        </b-modal>
      </span>

      <!-- Descriptor name -->
      <span class="has-text-weight-semibold">{{ sensoryData.name | deslug | titleCase }}</span>

      <!-- Descriptor values -->
      <div>
        <!-- Style Baseline - Show always -->
        <div class="style-sliders">
          <b-field label="Style Range" custom-class="is-size-7">
            <b-slider
              v-model="styleSliderRange"
              :min="sliderMin"
              :max="sliderMax"
              disabled
              size="is-small"
              type="is-rosewood"
              style="padding-left: 1rem; padding-right: 1rem"
            >
              <b-slider-tick
                v-for="(tick, index) in sliderTicks(sensoryData.style.min, sensoryData.style.max)"
                :key="index"
                :value="tick.value"
                class="is-tick-hidden"
              >{{ tick.label }}</b-slider-tick>
            </b-slider>
          </b-field>

          <!-- Possible Range - Show if available-->
          <b-field
            label="Possible Range"
            custom-class="is-size-7"
            style="padding-top: .25rem"
            v-if="possibleSliderRange !== ''"
          >
            <b-slider
              v-model="possibleSliderRange"
              :min="sliderMin"
              :max="sliderMax"
              disabled
              size="is-small"
              type="is-info"
              style="padding-left: 1rem; padding-right: 1rem"
            >
              <b-slider-tick
                v-for="(tick, index) in sliderTicks(sensoryData.possible.min, sensoryData.possible.max)"
                :key="index"
                :value="tick.value"
                class="is-tick-hidden"
              >{{ tick.label }}</b-slider-tick>
            </b-slider>
          </b-field>

          <!-- Configured Range - Show if available-->
          <b-field
            label="Configured Range"
            custom-class="is-size-7"
            style="padding-top: .25rem"
            v-if="configuredSliderRange !== ''"
          >
            <b-slider
              v-model="configuredSliderRange"
              :min="sliderMin"
              :max="sliderMax"
              disabled
              size="is-small"
              type="is-primary"
              style="padding-left: 1rem; padding-right: 1rem"
            >
              <b-slider-tick
                v-for="(tick, index) in sliderTicks(sensoryData.configured.min, sensoryData.configured.max)"
                :key="index"
                :value="tick.value"
                class="is-tick-hidden"
              >{{ tick.label }}</b-slider-tick>
            </b-slider>
          </b-field>
        </div>

        <b-taglist style="margin-top: .5rem">
          <b-tag
            :type="tag.type"
            :key="index"
            v-for="(tag, index) in sensoryData.tags"
          >{{ tag.value }}</b-tag>
        </b-taglist>
      </div>
    </div>
  </div>
</template>

<script>
import SensoryConfigurator from '@/components/SensoryConfigurator.vue';

export default {
  name: 'SensoryCard',
  props: {
    cardBg: String,
    type: String,
    sensoryData: Object,
    sliderMin: Number,
    sliderMax: Number,
    tickSpace: Number
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
      possibleSliderRange: '',
      configuredSliderRange: ''
    };
  },
  created() {
    if (this.sensoryData.possible !== undefined) {
      this.possibleSliderRange = [
        this.sensoryData.possible.min,
        this.sensoryData.possible.max
      ];
    }
    if (this.sensoryData.configured !== undefined) {
      this.configuredSliderRange = [
        this.sensoryData.configured.min,
        this.sensoryData.configured.max
      ];
    }
  },
  watch: {
    'sensoryData.configured': function(value) {
      this.configuredSliderRange = [value.min, value.max];
    },
    'sensoryData.possible': function(value) {
      this.possibleSliderRange = [value.min, value.max];
    }
  },
  filters: {
    titleCase: function(value) {
      value = value.toLowerCase().split(' ');
      for (var i = 0; i < value.length; i++) {
        value[i] = value[i].charAt(0).toUpperCase() + value[i].slice(1);
      }
      return value.join(' ');
    },
    deslug: function(value) {
      if (!value) return '';
      value = value.toString();
      value = value.replace('_', ' ');
      return value.charAt(0).toUpperCase() + value.slice(1);
    }
  },
  computed: {},
  methods: {
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
        ];
      } else if (min === max) {
        return [
          {
            value: min,
            label: min
          }
        ];
      } else {
        return [
          {
            value: (min + max) / 2,
            label: `${min}\xa0-\xa0${max}`
          }
        ];
      }
    }
  }
};
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
</style>