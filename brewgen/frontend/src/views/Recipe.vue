<template>
  <div>
    <!-- Nav bar -->
    <TheNavbar />
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
          <b-step-item label="Fermentable Setup">
            <div class="columns is-vcentered is-inline-block-mobile">
              <div class="column">
                <h1 class="title is-4">Fermentable Setup</h1>
              </div>
              <div class="column">
                <CurrentStyleCard />
              </div>
            </div>
            <FermentableSetup />
          </b-step-item>
          <!-- Wort Sensory -->
          <b-step-item label="Fermentable Sensory">
            <div class="columns is-vcentered is-inline-block-mobile">
              <div class="column">
                <h1 class="title is-4">Fermentable Sensory</h1>
              </div>
              <div class="column">
                <CurrentStyleCard />
              </div>
            </div>
            <FermentableSensory />
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
            <RecipeOutput />
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
                @click.prevent="previousAction"
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
    <TheFooter />
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'
import TheNavbar from '@/components/TheNavbar.vue'
import TheFooter from '@/components/TheFooter.vue'
import EquipmentField from '@/components/EquipmentField/EquipmentField.vue'
import StyleField from '@/components/StyleField/StyleField.vue'
import FermentableSensory from '@/components/FermentableSensory/FermentableSensory.vue'
import FermentableSetup from '@/components/FermentableSetup/FermentableSetup.vue'
import CurrentStyleCard from '@/components/CurrentStyleCard.vue'
import RecipeOutput from '@/components/RecipeOutput/RecipeOutput.vue'

export default {
  name: 'Recipe',
  components: {
    TheNavbar,
    TheFooter,
    EquipmentField,
    StyleField,
    FermentableSensory,
    FermentableSetup,
    CurrentStyleCard,
    RecipeOutput
  },
  data() {
    return {
      activeStep: 0
    }
  },
  watch: {
    activeStep: function(newStep, oldStep) {
      switch (newStep) {
        case 2:
          if (oldStep === 1) {
            this.fetchSensoryData()
            this.fetchRecipeData({ colorOnly: true })
          }
          break
        case 3:
          this.fetchRecipeData({ colorOnly: false })
          break
      }
    }
  },
  methods: {
    ...mapActions([
      'fetchStyles',
      'fetchAllFermentables',
      'fetchSensoryData',
      'fetchRecipeData'
    ]),
    previousAction: function() {
      // Store activeStep in Vuex, show modal when switching from Wort Sensory to Fermentables
      // Options: Cancel, Continue (Clear Sensory Model)
      // Only show if there is any sensory model data
      this.activeStep -= 1
    }
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
