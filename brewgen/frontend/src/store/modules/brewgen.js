import axios from "axios";

const state = {
  grainCategories: [],
  allGrains: [],
  equipmentProfile: {
    maxUniqueGrains: 4,
    targetVolumeGallons: 5.5,
    originalSg: 1.050,
    targetSrm: 6
  },
  sensoryData: []
};

const getters = {
  grainCategories: (state) => state.grainCategories,
  allGrains: (state) => state.allGrains,
  sensoryData: (state) => state.sensoryData,
  getGrainEnabled: (state) => (slug) => {
    return state.allGrains.find(grain => grain.slug == slug).enabled
  }
};

const actions = {
  async fetchGrainCategories({ commit }) {
    return axios.get('http://localhost:5000/api/v1/style-data/grains/categories')
      .then(response => {
        commit('setGrainCategories', response.data)
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  updateGrainCategoryValue({ commit }, grainCategory, key, value) {
    commit('setGrainCategoryValue', grainCategory, key, value)
  },
  async fetchAllGrains({ commit }) {
    return axios.get('http://localhost:5000/api/v1/grains')
      .then(response => {
        commit('setAllGrains', response.data)
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  setEquipmentSetting({ commit }, key, value) {
    commit('setEquipmentSetting', key, value)
  },
  async fetchSensoryData({ commit }) {
    return axios
      .post("http://localhost:5000/api/v1/grains/sensory-profiles", {
        grain_list: state.allGrains.filter(grain => grain.enabled).map(grain => grain.slug),
        category_model: state.grainCategories,
        sensory_model: null,
        max_unique_grains: Number(state.equipmentProfile.maxUniqueGrains)
      })
      .then(response => {
        commit('setSensoryData', response.data)
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  setGrainEnabled({ commit }, slug, value) {

  }
};

const mutations = {
  setGrainCategories: (state, grainCategories) => (state.grainCategories = grainCategories),
  setGrainCategoryValue: (state, { grainCategory, key, value }) => {
    var matchCategory = state.grainCategories.find(category => category.name == grainCategory)
    Object.assign(matchCategory, { [key]: value })
  },
  setAllGrains: (state, allGrains) => {
    allGrains.forEach(grain => (grain["enabled"] = true));
    state.allGrains = allGrains;
  },
  setEquipmentSetting: (state, { key, value }) => (state.equipmentProfile[key] = value),
  setSensoryData: (state, sensoryData) => state.sensoryData = sensoryData,
  setGrainEnabled: (state, { slug, enabled }) => {
    var matchGrain = state.allGrains.find(grain => grain.slug == slug)
    Object.assign(matchGrain, { enabled })
  }
};

export default {
  state,
  getters,
  actions,
  mutations
};