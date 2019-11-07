<template>
  <div>
    <!-- Nav bar -->
    <Navbar />
    <!-- Main Body-->
    <div class="container">
      <section class="section">
        <!-- Style and Equipment -->
        <b-steps v-model="activeStep" :animated="true" :has-navigation="true" size="is-small">
          <b-step-item label="Beer Style">
            <div class="columns">
              <!-- Style Setup -->
              <div class="column">
                <StyleField />
              </div>
              <!-- Equipment Profile -->
              <div class="column">
                <EquipmentField />
              </div>
            </div>
          </b-step-item>
          <!-- Fermentables -->
          <b-step-item label="Fermentables">
            <div class="columns is-vcentered is-inline-block-mobile">
              <div class="column">
                <h1 class="title is-4">Fermentables</h1>
              </div>
              <div class="column">
                <CurrentStyleCard />
              </div>
            </div>
            <StyleFermentables />
          </b-step-item>
          <!-- Wort Sensory -->
          <b-step-item label="Wort Sensory">
            <div class="columns is-vcentered is-inline-block-mobile">
              <div class="column">
                <h1 class="title is-4">Wort Sensory</h1>
              </div>
              <div class="column">
                <CurrentStyleCard />
              </div>
            </div>
            <WortSensory />
          </b-step-item>
          <!-- Recipes -->
          <b-step-item label="Recipes">
            <div class="columns is-vcentered is-inline-block-mobile">
              <div class="column">
                <h1 class="title is-4">Recipes</h1>
              </div>
              <div class="column">
                <CurrentStyleCard />
              </div>
            </div>
          </b-step-item>
          <!-- Custom Nav -->
          <template slot="navigation" slot-scope="{previous, next}">
            <div class="buttons">
              <b-button
                outlined
                type="is-danger"
                icon-pack="fas"
                icon-left="backward"
                :disabled="previous.disabled"
                @click.prevent="previous.action"
              >Previous</b-button>
              <b-button
                outlined
                type="is-success"
                icon-pack="fas"
                icon-right="forward"
                :disabled="nextDisabled"
                @click.prevent="next.action"
              >Next</b-button>
            </div>
          </template>
        </b-steps>
      </section>
    </div>
    <!-- Footer -->
    <Footer />
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'
import Navbar from '@/components/Navbar.vue'
import Footer from '@/components/Footer.vue'
import EquipmentField from '@/components/EquipmentField.vue'
import StyleField from '@/components/StyleField.vue'
import WortSensory from '@/components/WortSensory.vue'
import StyleFermentables from '@/components/StyleFermentables.vue'
import CurrentStyleCard from '@/components/CurrentStyleCard.vue'

export default {
  name: 'Recipe',
  components: {
    Navbar,
    Footer,
    EquipmentField,
    StyleField,
    WortSensory,
    StyleFermentables,
    CurrentStyleCard
  },
  data() {
    return {
      activeStep: 1
    }
  },
  watch: {
    activeStep: function(activeStep) {
      // Wort Sensory
      if (activeStep === 2) {
        this.fetchSensoryData()
        this.fetchRecipeData({ colorOnly: true })
      }
    }
  },
  methods: {
    ...mapActions([
      'fetchStyles',
      'fetchAllFermentables',
      'fetchSensoryData',
      'fetchRecipeData'
    ])
  },
  computed: {
    ...mapGetters(['currentStyleName']),
    nextDisabled: function() {
      switch (this.activeStep) {
        case 0: // style
          if (this.currentStyleName === 'None Selected') {
            return true
          }
          return false
          break
        case 1: // fermentables
          break
      }
    }
  },
  created() {
    document.title = 'Brewgen'
    this.fetchStyles()
    this.fetchAllFermentables()
  }
}
</script>

<style>
</style>
