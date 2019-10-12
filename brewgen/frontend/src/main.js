import Vue from 'vue'
import './plugins/fontawesome'
import App from './App.vue'
import router from './router'
import axios from 'axios'
import VueAxios from 'vue-axios'
import VueApexCharts from 'vue-apexcharts'
import Buefy from 'buefy'
// import 'buefy/dist/buefy.css'
import store from './store'
import { library } from '@fortawesome/fontawesome-svg-core';

// internal icons
import {
  faCheck, faCheckCircle, faInfoCircle, faExclamationTriangle, faExclamationCircle,
  faArrowUp, faAngleRight, faAngleLeft, faAngleDown,
  faEye, faEyeSlash, faCaretDown, faCaretUp, faUpload
} from "@fortawesome/free-solid-svg-icons";

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
library.add(faCheck, faCheckCircle, faInfoCircle, faExclamationTriangle, faExclamationCircle,
  faArrowUp, faAngleRight, faAngleLeft, faAngleDown,
  faEye, faEyeSlash, faCaretDown, faCaretUp, faUpload);

Vue.component('vue-fontawesome', FontAwesomeIcon);
Vue.component('apexchart', VueApexCharts)
Vue.config.productionTip = false
Vue.use(VueAxios, axios)
Vue.use(Buefy, {
  defaultIconComponent: 'vue-fontawesome',
  defaultIconPack: 'fas',
})
Vue.use(VueApexCharts)



new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app')
