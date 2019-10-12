<template>
  <b-row class="mt-3">
    <b-col md="8">
      <span class="h5 ml-2">Style: {{ currentStyleName }}</span>
    </b-col>
    <b-col md="4">
      <b-dropdown id="style-dropdown" text="Styles" class="float-right">
        <b-dropdown-item
          :key="style.name"
          v-for="style in styles"
          @click="setCurrentStyleName(style)"
        >{{ style.name }}</b-dropdown-item>
      </b-dropdown>
    </b-col>
  </b-row>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'
export default {
  name: 'StyleDropdown',
  props: ['styles'],
  methods: {
    ...mapActions(['setDataFromStyle', 'setCurrentStyleStats']),
    setCurrentStyleName: function (style) {
      this.$store.commit('setCurrentStyleName', style.name)
      this.setDataFromStyle(style.slug)
    }
  },
  computed: {
    ...mapGetters(['currentStyleName'])
  }
}
</script>

<style>
</style>
