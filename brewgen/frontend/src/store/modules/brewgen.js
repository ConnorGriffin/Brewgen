import axios from 'axios'

const state = {
  grainCategories: [],
  allGrains: [],
  equipmentProfile: {
    maxUniqueGrains: 4,
    targetVolumeGallons: 5.5,
    mashEfficiency: 75,
  },
  beerProfile: {
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
  currentStyleSensory: '',
  styleListFilter: '',
  ogWatcherEnabled: false
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
  currentStyleStats: state => state.currentStyleStats,
  currentStyleSensory: state => state.currentStyleSensory
}

const actions = {
  async fetchGrainCategories({ commit }) {
    return axios
      .get('http://10.31.36.49:5000/api/v1/style-data/grains/categories')
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
      .get('http://10.31.36.49:5000/api/v1/grains')
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
      .post('http://10.31.36.49:5000/api/v1/grains/sensory-profiles', {
        grain_list: state.allGrains,
        category_model: state.grainCategories,
        sensory_model: state.sensoryModel,
        max_unique_grains: Number(state.equipmentProfile.maxUniqueGrains)
      })
      .then(response => {
        commit('setSensoryData', response.data)
        commit('setPossibleSensory', response.data)
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
      var uri = 'http://10.31.36.49:5000/api/v1/grains/recipes?coloronly=true' + params
      var commitAction = 'setRecipeColorData'
      var beerProfile = {
        original_sg: Number(state.beerProfile.originalSg)
      }
    } else {
      var uri = 'http://10.31.36.49:5000/api/v1/grains/recipes'
      var commitAction = 'setRecipeData'
      var beerProfile = {
        min_color_srm: Number(state.beerProfile.minSrm),
        max_color_srm: Number(state.beerProfile.maxSrm),
        original_sg: Number(state.beerProfile.originalSg)
      }
    }
    return axios
      .post(uri, {
        grain_list: state.allGrains,
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
      .get('http://10.31.36.49:5000/api/v1/styles')
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
      .get('http://10.31.36.49:5000/api/v1/styles/' + styleSlug)
      .then(response => {
        // Set some default values for og/fg if none provided
        let stats = response.data.stats
        if (stats === null) {
          stats = {
            og: {
              high: 1.150,
              low: 1.020
            },
            fg: {
              high: 1.040,
              low: 0.990
            },
            srm: {
              high: 100,
              low: 0
            },
            ibu: {
              high: 120,
              low: 0
            }
          }
        }
        commit('setAllGrainsFromStyle', response.data.grain_usage)
        commit('setGrainCategories', response.data.category_usage)
        commit('setCurrentStyleSensory', response.data.sensory_data)
        // commit('setSensoryModel', response.data.sensory_data)
        commit('setCurrentStyleStats', stats)
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
    commit('addSensoryToModel', name, min, max)
  },
  setSensoryConstraint({ commit }, name, min, max) {
    commit('setSensoryConstraint', name, min, max)
  }
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
    // Store the grain data for the style in allGrains
    state.allGrains = styleGrains
  },
  setSensoryConstraint: (state, { name, min, max }) => {
    // Add a sensory constraint to the model, or modify an existing constraint
    let matchSensory = state.currentStyleSensory.find(
      sensoryObject => sensoryObject.name == name
    )
    Object.assign(matchSensory, {
      configured: {
        min,
        max
      }
    })
  },
  setCurrentStyleSensory: (state, sensoryData) => {
    // Format the sensory data for use in the recipe designer
    state.currentStyleSensory = sensoryData.filter(sensoryValue => {
      return sensoryValue.max > 0
    })
      .map(sensoryValue => {
        let sensoryReturn = {
          name: sensoryValue.name,
          style: {
            min: sensoryValue.min,
            max: sensoryValue.max
          },
          possible: undefined,
          configured: undefined,
          tags: []
        }
        if (sensoryValue.max - sensoryValue.min >= 1) {
          sensoryReturn.tags.push({
            value: 'wide range',
            type: 'is-info'
          })
        }
        if (sensoryValue.max <= .25) {
          sensoryReturn.tags.push({
            value: 'minimal use',
            type: 'is-danger'
          })
        }
        if (sensoryValue.max - sensoryValue.min <= .25) {
          sensoryReturn.tags.push({
            value: 'narrow range',
            type: 'is-warning'
          })
        }
        return sensoryReturn
      })
  },
  setPossibleSensory: (state, sensoryData) => {
    // Set the possible sensory values from the sensory profile query
    // Used by sliders in the recipe designer and eventually the chart data as well
    sensoryData.forEach(sensoryValue => {
      // Find the matching sensory object in the currentStyleSensory data so we can update it
      let matchedSensory = state.currentStyleSensory.find(csSensory => csSensory.name == sensoryValue.name)
      if (matchedSensory !== undefined) {
        Object.assign(matchedSensory, {
          possible: {
            min: sensoryValue.min,
            max: sensoryValue.max
          }
        })
      }
    })
  },
  updateEquipmentProfile: (state, { maxUniqueGrains, targetVolumeGallons, mashEfficiency }) => {
    Object.assign(state.equipmentProfile, { maxUniqueGrains, targetVolumeGallons, mashEfficiency })
  },
  setBeerProfileKey: (state, { key, value }) =>
    (state.beerProfile[key] = value),
  setSensoryData: (state, sensoryData) => {
    // TODO: Charts are using this data still, want to move it to the Possible data instead
    state.sensoryData = sensoryData
  },
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
  },
  setOgWatcherEnabled(state, value) {
    state.ogWatcherEnabled = value
  }
}

export default {
  state,
  getters,
  actions,
  mutations
}
