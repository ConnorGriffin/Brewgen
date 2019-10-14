<template>
  <div class="container">
    <h1 class="title is-size-5">Beer Style</h1>

    <!-- Style list and selection modal -->
    <b-modal :active.sync="showStyleListModal" has-modal-card trap-focus scroll="keep">
      <StyleList />
    </b-modal>

    <!-- Style name and selector button -->
    <p>
      <span class="has-text-weight-semibold">Style:</span>
      <span>&nbsp;{{ currentStyleName }}</span>
      <b-button
        type="is-primary is-small is-pulled-right"
        @click="showStyleListModal = true"
      >Select Style</b-button>
    </p>

    <!-- Selected style stats, only shows if style is selected -->
    <div v-if="currentStyleStats !== ''">
      <p>
        <b-field label="Target Original Gravity">
          <b-slider
            v-model="originalSg"
            :min="currentStyleStats.og.low"
            :max="currentStyleStats.og.high"
            :step="0.001"
            ticks
            lazy
            style="padding-left: 1rem; padding-right: 1rem"
          >
            <b-slider-tick
              :value="currentStyleStats.og.low"
            >{{ currentStyleStats.og.low.toFixed(3) }}</b-slider-tick>
            <b-slider-tick
              :value="currentStyleStats.og.high"
            >{{ currentStyleStats.og.high.toFixed(3) }}</b-slider-tick>
          </b-slider>
        </b-field>
        <b-field label="Target Color (SRM)">
          <b-slider
            v-model="targetSrm"
            :min="currentStyleStats.srm.low"
            :max="currentStyleStats.srm.high"
            :step="1"
            ticks
            lazy
            style="padding-left: 1rem; padding-right: 1rem"
          >
            <b-slider-tick :value="currentStyleStats.srm.low">{{ currentStyleStats.srm.low }}</b-slider-tick>
            <b-slider-tick :value="currentStyleStats.srm.high">{{ currentStyleStats.srm.high }}</b-slider-tick>
          </b-slider>
        </b-field>
      </p>
    </div>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import StyleList from '@/components/StyleList.vue';

export default {
  name: 'StyleField',
  components: {
    StyleList
  },
  data() {
    return {
      showStyleListModal: false
    };
  },
  computed: {
    ...mapGetters(['currentStyleName', 'currentStyleStats']),
    originalSg: {
      get() {
        return this.$store.state.brewgen.beerProfile.originalSg;
      },
      set(value) {
        this.$store.commit('setBeerProfileKey', {
          key: 'originalSg',
          value
        });
      }
    },
    targetSrm: {
      get() {
        return [
          this.$store.state.brewgen.beerProfile.minSrm,
          this.$store.state.brewgen.beerProfile.maxSrm
        ];
      },
      set(value) {
        this.$store.commit('setBeerProfileKey', {
          key: 'minSrm',
          value: value[0]
        });
        this.$store.commit('setBeerProfileKey', {
          key: 'maxSrm',
          value: value[1]
        });
      }
    }
  },
  methods: {
    ...mapActions(['fetchRecipeData'])
  },
  watch: {
    originalSg: function() {
      this.fetchRecipeData({
        colorOnly: true,
        chartMin: this.$store.state.brewgen.currentStyleStats.srm.low,
        chartMax: this.$store.state.brewgen.currentStyleStats.srm.high
      });
    }
  }
};
</script>

<style>
</style>