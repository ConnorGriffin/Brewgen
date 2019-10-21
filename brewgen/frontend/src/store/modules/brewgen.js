import axios from 'axios'

const state = {
  grainCategories: [],
  allGrains: [],
  equipmentProfile: {
    maxUniqueGrains: 4,
    targetVolumeGallons: 5.5,
    mashEfficiency: 75
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
  // Need to work on saving the previous state so editing is faster in two scenerios:
  // 1. When editing the most recently set descriptor
  // 2. When re-editing a value that we clicked edit on but did not save changes, no need to recalc
  // Current style sensory stats including style, possible, and configured min/max values
  currentStyleSensory: '',
  // Current style sensory stats with a single descriptor's configured values nulled
  currentStyleSensoryEdit: null,
  // Current style sensory previous to the most recent change
  lastSensoryData: null,
  // Slug of the sensory keyword that was most most recently changed
  lastChangedSensoryDescriptor: null,
  styleListFilter: '',
  ogWatcherEnabled: false,
  // State of application API calls, used to set spinners and progress bars
  loaders: []
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
  currentStyleSensory: state => state.currentStyleSensory,
  currentStyleSensoryEdit: state => sensoryName => {
    return state.currentStyleSensoryEdit.find(sensoryData => sensoryData.name == sensoryName)
  },
  isLoading: state => loader => {
    // Get the state of a loader by name, returns false if loader doesn't exist
    let loaderObject = state.loaders.find(obj => obj.name === loader)
    if (loaderObject !== undefined) {
      return loaderObject.loading
    } else {
      return false
    }
  },
  lastSensoryData: state => sensoryName => {
    return state.lastSensoryData.find(sensoryData => sensoryData.name === sensoryName)
  },
  lastChangedSensoryDescriptor: state => state.lastChangedSensoryDescriptor
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
    commit('setLoader', {
      name: 'sensoryData',
      loading: true
    })

    // build the sensory model from the currentStyleSensory.configured values
    let sensoryModel = state.currentStyleSensory
      .filter(sensoryData => {
        return sensoryData.configured !== undefined
      })
      .map(sensoryData => {
        return {
          name: sensoryData.name,
          min: sensoryData.configured.min,
          max: sensoryData.configured.max
        }
      })

    return axios
      .post('http://10.31.36.49:5000/api/v1/grains/sensory-profiles', {
        grain_list: state.allGrains,
        category_model: state.grainCategories,
        sensory_model: sensoryModel,
        max_unique_grains: Number(state.equipmentProfile.maxUniqueGrains)
      })
      .then(response => {
        commit('setSensoryData', response.data)
        commit('setPossibleSensory', response.data)
        commit('setLoader', {
          name: 'sensoryData',
          loading: false
        })
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  async fetchSensoryDataEdit({ commit }, name) {
    // Fetches current style sensory data but excludes configured values for a single descriptor
    commit('setLoader', {
      name: 'sensoryDataEdit',
      loading: true
    })

    // build the sensory model from the currentStyleSensory.configured values
    let sensoryModel = state.currentStyleSensory
      .filter(sensoryData => {
        return (sensoryData.configured !== undefined &&
          sensoryData.name !== name)
      })
      .map(sensoryData => {
        return {
          name: sensoryData.name,
          min: sensoryData.configured.min,
          max: sensoryData.configured.max
        }
      })

    return axios
      .post('http://10.31.36.49:5000/api/v1/grains/sensory-profiles', {
        grain_list: state.allGrains,
        category_model: state.grainCategories,
        sensory_model: sensoryModel,
        max_unique_grains: Number(state.equipmentProfile.maxUniqueGrains)
      })
      .then(response => {
        commit('setPossibleSensoryEdit', response.data)
        commit('setLoader', {
          name: 'sensoryDataEdit',
          loading: false
        })
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  async fetchRecipeData({ commit }, { colorOnly }) {
    commit('setLoader', {
      name: 'recipeData',
      loading: true
    })
    if (colorOnly == true) {
      let chartMin = state.beerProfile.minSrm
      let chartMax = state.beerProfile.maxSrm
      let params = '&chartrange=' + chartMin + ',' + chartMax

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

    // build the sensory model from the currentStyleSensory.configured values
    let sensoryModel = state.currentStyleSensory
      .filter(sensoryData => {
        return sensoryData.configured !== undefined
      })
      .map(sensoryData => {
        return {
          name: sensoryData.name,
          min: sensoryData.configured.min,
          max: sensoryData.configured.max
        }
      })

    return axios
      .post(uri, {
        grain_list: state.allGrains,
        category_model: state.grainCategories,
        sensory_model: sensoryModel,
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
        commit('setLoader', {
          name: 'recipeData',
          loading: false
        })
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  async fetchStyles({ commit }) {
    commit('setLoader', {
      name: 'styles',
      loading: true
    })
    return axios
      .get('http://10.31.36.49:5000/api/v1/styles')
      .then(response => {
        commit('setStyles', response.data)
        commit('setLoader', {
          name: 'styles',
          loading: false
        })
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  async setDataFromStyle({ commit }, styleSlug) {
    commit('resetData')
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
        if (sensoryValue.max <= 0.25) {
          sensoryReturn.tags.push({
            value: 'minimal use',
            type: 'is-danger'
          })
        }
        if (sensoryValue.max - sensoryValue.min <= 0.25) {
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
  setPossibleSensoryEdit: (state, sensoryData) => {
    // Set the possible sensory values from the sensory profile query, used while editing a descriptor
    // Work off a copy of the current sensory data
    state.currentStyleSensoryEdit = JSON.parse(JSON.stringify(state.currentStyleSensory))
    sensoryData.forEach(sensoryValue => {
      // Find the matching sensory object in the currentStyleSensoryEdit data so we can update it
      let matchedSensory = state.currentStyleSensoryEdit.find(csSensory => csSensory.name == sensoryValue.name)
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
  removeSensoryConstraint(state, name) {
    let sensoryObj = state.currentStyleSensory.find(object => object.name == name)
    if (sensoryObj.configured !== undefined) {
      delete sensoryObj.configured
    }
    state.lastChangedSensoryDescriptor = null
    state.lastSensoryData = null
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
  },
  setLoader(state, { name, loading }) {
    // Creates or updates a loader's status
    let loader = state.loaders.find(loader => loader.name === name)
    if (loader !== undefined) {
      Object.assign(loader, { name, loading })
    } else {
      state.loaders.push({
        name, loading
      })
    }
  },
  setLastSensoryData(state) {
    state.lastSensoryData = JSON.parse(JSON.stringify(state.currentStyleSensory))
  },
  setLastChangedSensoryDescriptor(state, value) {
    state.lastChangedSensoryDescriptor = value
  },
  clearSensoryConfiguredValues(state) {
    // Remove all configured sensory values
    state.currentStyleSensory.forEach(sensoryData => {
      delete sensoryData.configured
    })
  },
  resetData(state) {
    state.allGrains = []
    state.sensoryData = []
    state.recipeData = []
    state.grainCategories = []
    state.currentStyleSensory = ''
    state.currentStyleStats = ''
    state.lastChangedSensoryDescriptor = null
    state.lastSensoryData = null
  }
}

export default {
  state,
  getters,
  actions,
  mutations
}
