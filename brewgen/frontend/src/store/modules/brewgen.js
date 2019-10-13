import axios from 'axios'

const state = {
  grainCategories: [],
  allGrains: [],
  equipmentProfile: {
    maxUniqueGrains: 4,
    targetVolumeGallons: 5.5,
    mashEfficiency: 75,
    originalSg: 1.05,
    minSrm: 3,
    maxSrm: 10
  },
  sensoryData: [],
  sensoryModel: [],
  recipeData: [],
  recipeColorData: [],
  styles: [],
  currentStyleName: 'None Selected',
  currentStyleStats: '',
  styleListFilter: ''
}

const getters = {
  grainCategories: state => state.grainCategories,
  allGrains: state => state.allGrains,
  sensoryData: state => state.sensoryData,
  sensoryModel: state => state.sensoryModel,
  getGrainEnabled: state => slug => {
    return state.allGrains.find(grain => grain.slug == slug).enabled
  },
  recipeData: state => state.recipeData,
  recipeColorData: state => state.recipeColorData,
  styles: state => state.styles,
  currentStyleName: state => state.currentStyleName,
  currentStyleStats: state => state.currentStyleStats
}

const actions = {
  async fetchGrainCategories({ commit }) {
    return axios
      .get('http://localhost:5000/api/v1/style-data/grains/categories')
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
    return axios
      .get('http://localhost:5000/api/v1/grains')
      .then(response => {
        commit('setAllGrains', response.data)
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  updateEquipmentProfile({ commit }, maxUniqueGrains, targetVolumeGallons, mashEfficiency) {
    commit('updateEquipmentProfile', maxUniqueGrains, targetVolumeGallons, mashEfficiency)
  },
  async fetchSensoryData({ commit }) {
    return axios
      .post('http://localhost:5000/api/v1/grains/sensory-profiles', {
        grain_list: state.allGrains
          .filter(grain => grain.enabled)
          .map(grain => grain.slug),
        category_model: state.grainCategories,
        sensory_model: state.sensoryModel,
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
  async fetchRecipeData({ commit }, { colorOnly, chartMin, chartMax }) {
    if (colorOnly == true) {
      if (chartMin !== undefined && chartMax !== undefined) {
        var params = '&chartrange=' + chartMin + ',' + chartMax
      } else {
        var params = ''
      }
      var uri = 'http://localhost:5000/api/v1/grains/recipes?coloronly=true' + params
      var commitAction = 'setRecipeColorData'
      var beerProfile = {
        original_sg: Number(state.equipmentProfile.originalSg)
      }
    } else {
      var uri = 'http://localhost:5000/api/v1/grains/recipes'
      var commitAction = 'setRecipeData'
      var beerProfile = {
        min_color_srm: Number(state.equipmentProfile.minSrm),
        max_color_srm: Number(state.equipmentProfile.maxSrm),
        original_sg: Number(state.equipmentProfile.originalSg)
      }
    }
    return axios
      .post(uri, {
        grain_list: state.allGrains
          .filter(grain => grain.enabled)
          .map(grain => grain.slug),
        category_model: state.grainCategories,
        sensory_model: state.sensoryModel,
        max_unique_grains: Number(state.equipmentProfile.maxUniqueGrains),
        equipment_profile: {
          target_volume_gallons: Number(
            state.equipmentProfile.targetVolumeGallons
          ),
          mash_efficiency: Number(state.equipmentProfile.mashEfficiency)
        },
        beer_profile: beerProfile
      })
      .then(response => {
        commit(commitAction, response.data)
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  async fetchStyles({ commit }) {
    return axios
      .get('http://localhost:5000/api/v1/styles')
      .then(response => {
        commit('setStyles', response.data)
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  async setDataFromStyle({ commit }, styleSlug) {
    return axios
      .get('http://localhost:5000/api/v1/styles/' + styleSlug)
      .then(response => {
        commit('setAllGrainsFromStyle', response.data.grain_usage)
        commit('setGrainCategories', response.data.category_usage)
        commit('setCurrentStyleStats', response.data.stats)
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  removeSensoryFromModel({ commit }, name) {
    commit('removeSensoryFromModel', name)
  },
  addSensoryToModel({ commit }, name, min, max) {
    commit('addSensoryToModel', name), min, max
  }
  // ,
  // setStyleListFilter({ commit }, value) {
  //   commit('setStyleListFilter', value)
  // }
}

const mutations = {
  setGrainCategories: (state, grainCategories) =>
    (state.grainCategories = grainCategories),
  setGrainCategoryValue: (state, { grainCategory, key, value }) => {
    var matchCategory = state.grainCategories.find(
      category => category.name == grainCategory
    )
    Object.assign(matchCategory, { [key]: value })
  },
  setAllGrains: (state, allGrains) => {
    allGrains.forEach(grain => (grain['enabled'] = true))
    state.allGrains = allGrains
  },
  setAllGrainsFromStyle: (state, styleGrains) => {
    // Iterate over every grain in allGrains, set the grain properties from the provided style data
    state.allGrains.forEach(stateGrain => {
      var styleGrain = styleGrains.find(g => g.slug == stateGrain.slug)
      // If the grain isn't in the style data at all, set to disabled and set min and max to 0
      if (styleGrain === undefined) {
        Object.assign(stateGrain, { enabled: false, min_percent: 0, max_percent: 0 })
      } else {
        Object.assign(stateGrain, { enabled: true, min_percent: styleGrain.min_percent, max_percent: styleGrain.max_percent })
      }
    })
  },
  updateEquipmentProfile: (state, { maxUniqueGrains, targetVolumeGallons, mashEfficiency }) => {
    Object.assign(state.equipmentProfile, { maxUniqueGrains, targetVolumeGallons, mashEfficiency })
  },
  setSensoryData: (state, sensoryData) => (state.sensoryData = sensoryData),
  setRecipeData: (state, recipeData) => (state.recipeData = recipeData),
  setRecipeColorData: (state, recipeColorData) =>
    (state.recipeColorData = recipeColorData),
  setGrainEnabled: (state, { slug, enabled }) => {
    var matchGrain = state.allGrains.find(grain => grain.slug == slug)
    Object.assign(matchGrain, { enabled })
  },
  removeSensoryFromModel(state, name) {
    var modelObject = state.sensoryModel.find(object => object.name == name)
    if (modelObject !== undefined) {
      var index = state.sensoryModel.indexOf(modelObject)
      state.sensoryModel.splice(index)
    }
  },
  addSensoryToModel(state, { name, min, max }) {
    // Remove if already exists, just to be safe
    var modelObject = state.sensoryModel.find(object => object.name == name)
    if (modelObject !== undefined) {
      var index = state.sensoryModel.indexOf(modelObject)
      state.sensoryModel.splice(index)
    }
    // Add to the model
    state.sensoryModel.push({
      name,
      min: parseFloat(min),
      max: parseFloat(max)
    })
  },
  setStyles(state, value) {
    state.styles = value
  },
  setCurrentStyleName(state, value) {
    state.currentStyleName = value
  },
  setCurrentStyleStats(state, value) {
    state.currentStyleStats = value
  },
  setStyleListFilter(state, value) {
    state.styleListFilter = value
  }
}

export default {
  state,
  getters,
  actions,
  mutations
}
