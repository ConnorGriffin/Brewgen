import Vuex from 'vuex'
import Vue from 'vue'
import brewgen from './modules/brewgen'

Vue.use(Vuex)
export default new Vuex.Store({
  modules: {
    brewgen
  }
})
