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
        <b-modal
          :active.sync="showSensoryConfigurator"
          has-modal-card
          trap-focus
          scroll="keep"
          v-if="possibleSliderRange !== ''"
        >
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
          <div class="columns is-gapless is-vcentered is-multiline is-vcentered card-columns">
            <!-- Style Range -->
            <div class="column is-one-third">
              <h1 class="title is-7">Style</h1>
            </div>
            <div class="column is-two-thirds">
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
            </div>

            <!-- Possible Range -->
            <div class="column is-one-third" v-if="possibleSliderRange !== '' && type==='picker'">
              <h1 class="title is-7">Possible</h1>
            </div>
            <div class="column is-two-thirds" v-if="possibleSliderRange !== '' && type==='picker'">
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
            </div>

            <!-- Configured Range -->
            <div class="column is-one-third" v-if="configuredSliderRange !== ''">
              <h1 class="title is-7">Desired</h1>
            </div>
            <div class="column is-two-thirds" v-if="configuredSliderRange !== ''">
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
      </div>
    </div>
    <b-loading :is-full-page="false" :active.sync="this.isLoading('sensoryData')"></b-loading>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
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
      if (value !== undefined) {
        this.configuredSliderRange = [value.min, value.max];
      }
    },
    'sensoryData.possible': function(value) {
      if (value !== undefined) {
        this.possibleSliderRange = [value.min, value.max];
      }
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
  computed: {
    ...mapGetters(['isLoading'])
  },
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
.card-columns {
  margin: 0;
  padding: 0;
}
</style>