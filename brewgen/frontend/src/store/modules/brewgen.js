import axios from 'axios'

const state = {
  fermentableCategories: [],
  // Details of all fermentables
  allFermentables: [],
  equipmentProfile: {
    maxUniqueFermentables: 4,
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
  styleListFilter: '',
  // Whether or not the current model is valid
  fermentableModelValidity: null,
  // Fermentable Category that is currently being edited
  editingFermentableCategory: null,
  // Unsaved changes to fermentables in a fermentable category
  fermentableChanges: [],
  // Unsaved category usage amounts (min, max)
  fermentableCategoryUsageEdit: [],
  // Sensory descriptors that are mentioned in the BJCP style guide
  bjcpSensory: null,
  // Need to work on saving the previous state so editing is faster in two scenerios:
  // 1. When editing the most recently set descriptor
  // 2. When re-editing a value that we clicked edit on but did not save changes, no need to recalc
  // Current style sensory stats including style, possible, and configured min/max values
  currentStyleSensory: [],
  // Current style fermentable data (usage, slugs, and enabled/disabled only)
  currentStyleFermentables: null,
  // Current style sensory stats with a single descriptor's configured values nulled
  currentStyleSensoryEdit: null,
  // Current style sensory previous to the most recent change
  lastSensoryData: null,
  // Slug of the sensory keyword that was most most recently changed
  lastChangedSensoryDescriptor: null,
  // State of application API calls, used to set spinners and progress bars
  loaders: [],
  // Sensory descriptors that show up in the main Wort Sensory page
  visibleSensoryDescriptors: [],
  // Whether the sensory descriptor cards are expanded, collapsed, or mixed
  sensoryDescriptorsExpanded: 'collapsed'
}

const getters = {
  fermentableCategories: state => state.fermentableCategories,
  allFermentables: state => state.allFermentables,
  currentStyleFermentables: state => state.currentStyleFermentables,
  sensoryData: state => state.sensoryData,
  sensoryModel: state => state.sensoryModel,
  recipeData: state => state.recipeData,
  recipeColorData: state => state.recipeColorData,
  styles: state => state.styles,
  currentStyleName: state => state.currentStyleName,
  currentStyleStats: state => state.currentStyleStats,
  currentStyleSensory: state => state.currentStyleSensory,
  currentStyleSensoryEdit: state => sensoryName => {
    return state.currentStyleSensoryEdit.find(sensoryData => sensoryData.name === sensoryName)
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
  lastChangedSensoryDescriptor: state => state.lastChangedSensoryDescriptor,
  equipmentProfile: state => state.equipmentProfile,
  beerProfile: state => state.beerProfile,
  editingFermentableCategory: state => state.editingFermentableCategory,
  fermentableChanges: state => state.fermentableChanges,
  fermentableModelValidity: state => state.fermentableModelValidity,
  fermentableCategoryUsageEdit: state => state.fermentableCategoryUsageEdit,
  fermentableCategoryUsageModified: state => {
    // Return true/false if category values differ from unsaved
    let matchCategory = state.fermentableCategories.find(
      category => category.name === state.editingFermentableCategory
    )
    if (matchCategory) {
      if (
        matchCategory.min_percent !== state.fermentableCategoryUsageEdit.minUsage ||
        matchCategory.max_percent !== state.fermentableCategoryUsageEdit.maxUsage ||
        matchCategory.unique_fermentable_count !== state.fermentableCategoryUsageEdit.uniqueFermentableCount
      ) {
        return true
      } else {
        return false
      }
    }
  },
  visibleSensoryDescriptors: state => state.visibleSensoryDescriptors
}

const actions = {
  async fetchFermentableCategories({
    commit
  }) {
    return axios
      .get('http://10.31.36.49:5000/api/v1/style-data/grains/categories')
      .then(response => {
        commit('setFermentableCategories', response.data)
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  updateFermentableCategoryValue({
    commit
  }, fermentableCategory, key, value) {
    commit('setFermentableCategoryValue', fermentableCategory, key, value)
  },
  async fetchAllFermentables({
    commit
  }) {
    return axios
      .get('http://10.31.36.49:5000/api/v1/grains')
      .then(response => {
        commit('setAllFermentables', response.data)
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  updateEquipmentProfile({
    commit
  }, maxUniqueFermentables, targetVolumeGallons, mashEfficiency) {
    commit('updateEquipmentProfile', maxUniqueFermentables, targetVolumeGallons, mashEfficiency)
  },
  async fetchSensoryData({
    commit
  }) {
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

    // Build the fermentable list
    let fermentable_list = state.currentStyleFermentables.map(fermentable => {
      return {
        slug: fermentable.slug,
        min_percent: fermentable.min_percent,
        max_percent: fermentable.max_percent
      }
    })

    return axios
      .post('http://10.31.36.49:5000/api/v1/grains/sensory-profiles', {
        fermentable_list: fermentable_list,
        category_model: state.fermentableCategories,
        sensory_model: sensoryModel,
        max_unique_fermentables: Number(state.equipmentProfile.maxUniqueFermentables)
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
  async fetchSensoryDataEdit({
    commit
  }, name) {
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
        fermentable_list: state.allFermentables,
        category_model: state.fermentableCategories,
        sensory_model: sensoryModel,
        max_unique_fermentables: Number(state.equipmentProfile.maxUniqueFermentables)
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
  async fetchRecipeData({
    commit
  }, {
    colorOnly
  }) {
    commit('setLoader', {
      name: 'recipeData',
      loading: true
    })
    if (colorOnly === true) {
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

    // Build the fermentable list
    let fermentable_list = state.currentStyleFermentables.map(fermentable => {
      return {
        slug: fermentable.slug,
        min_percent: fermentable.min_percent,
        max_percent: fermentable.max_percent
      }
    })

    return axios
      .post(uri, {
        fermentable_list: fermentable_list,
        category_model: state.fermentableCategories,
        sensory_model: sensoryModel,
        max_unique_fermentables: Number(state.equipmentProfile.maxUniqueFermentables),
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
  async fetchStyles({
    commit
  }) {
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
  async setDataFromStyle({
    commit
  }, styleSlug) {
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
        commit('setFermentablesFromStyle', response.data.grain_usage)
        commit('setFermentableCategories', response.data.category_usage)
        commit('setBjcpSensory', response.data.bjcp_sensory)
        commit('setCurrentStyleSensory', response.data.sensory_data)
        // commit('setSensoryModel', response.data.sensory_data)
        commit('setMaxUniqueFermentables', response.data.unique_fermentable_count)
        commit('setCurrentStyleStats', stats)
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  async fetchFermentableModelValidity({
    commit
  }) {
    return axios
      .post('http://10.31.36.49:5000/api/v1/helpers/grain-model-valid', {
        fermentable_list: state.currentStyleFermentables,
        category_model: state.fermentableCategories,
        max_unique_fermentables: Number(state.equipmentProfile.maxUniqueFermentables)
      })
      .then(response => {
        commit('setFermentableModelValidity', response.data)
        Promise.resolve()
      })
      .catch(err => {
        throw err
      })
  },
  addSensoryToModel({
    commit
  }, name, min, max) {
    commit('addSensoryToModel', name, min, max)
  },
  setSensoryConstraint({
    commit
  }, name, min, max) {
    commit('setSensoryConstraint', name, min, max)
  },
  removeSensoryConstraint({
    commit
  }, name) {
    commit('removeSensoryConstraint', name)
  },
  saveFermentableCategoryChanges({
    commit
  }) {
    let usage = {
      name: state.editingFermentableCategory,
      min_percent: state.fermentableCategoryUsageEdit.minUsage,
      max_percent: state.fermentableCategoryUsageEdit.maxUsage,
      unique_fermentable_count: state.fermentableCategoryUsageEdit.uniqueFermentableCount
    }
    commit('saveFermentableChanges')
    commit('setCategoryUsage', usage)
  },
  setEditingFermentableCategory({
    commit
  }, payload) {
    commit('setEditingFermentableCategory', payload)
  },
  clearEditingFermentableCategory({
    commit
  }) {
    commit('setEditingFermentableCategory', null)
    commit('clearFermentableChanges')
    commit('setFermentableCategoryUsageEdit', [])
  },
  discardFermentableCategoryChanges({
    commit
  }) {
    commit('clearFermentableChanges')
    commit('setFermentableCategoryUsageEdit', [])
  },
  setFermentableCategoryUsageEdit({
    commit
  }, payload) {
    commit('setFermentableCategoryUsageEdit', payload)
  },
  addVisibleSensoryDescriptor({
    commit
  }, name) {
    commit('addVisibleSensoryDescriptor', name)
  },
  removeVisibleSensoryDescriptor({
    commit
  }, name) {
    commit('removeVisibleSensoryDescriptor', name)
  }
}

const mutations = {
  setFermentableCategories: (state, fermentableCategories) =>
    (state.fermentableCategories = fermentableCategories),
  setFermentableCategoryValue: (state, {
    fermentableCategory,
    key,
    value
  }) => {
    var matchCategory = state.fermentableCategories.find(
      category => category.name === fermentableCategory
    )
    Object.assign(matchCategory, {
      [key]: value
    })
  },
  setAllFermentables: (state, allFermentables) => {
    state.allFermentables = allFermentables
  },
  setFermentablesFromStyle: (state, value) => {
    // Store the fermentable data for the style in allFermentables
    state.currentStyleFermentables = value
  },
  setSensoryConstraint: (state, {
    name,
    min,
    max
  }) => {
    // Add a sensory constraint to the model, or modify an existing constraint
    let matchSensory = state.currentStyleSensory.find(
      sensoryObject => sensoryObject.name === name
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
    state.visibleSensoryDescriptors = []
    state.currentStyleSensory = sensoryData.filter(sensoryValue => {
        return (sensoryValue.max > 0.25 && sensoryValue.max - sensoryValue.min > 0.25)
      })
      .map(sensoryValue => {
        let sensoryReturn = {
          name: sensoryValue.name,
          style: {
            min: sensoryValue.min,
            max: sensoryValue.max,
            mean: sensoryValue.mean
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
        if (Object.keys(state.bjcpSensory).includes(sensoryValue.name)) {
          sensoryReturn.tags.push({
            value: 'mentioned in style',
            type: 'is-primary'
          })
        }

        let tagValues = sensoryReturn.tags.map(tag => tag.value)
        if (tagValues.includes('mentioned in style') || tagValues.includes('wide range')) {
          state.visibleSensoryDescriptors.push(sensoryReturn.name)
        }

        return sensoryReturn
      })
  },
  setPossibleSensory: (state, sensoryData) => {
    // Set the possible sensory values from the sensory profile query
    // Used by sliders in the recipe designer and eventually the chart data as well
    sensoryData.forEach(sensoryValue => {
      // Find the matching sensory object in the currentStyleSensory data so we can update it
      let matchedSensory = state.currentStyleSensory.find(csSensory => csSensory.name === sensoryValue.name)
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
      let matchedSensory = state.currentStyleSensoryEdit.find(csSensory => csSensory.name === sensoryValue.name)
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
  addVisibleSensoryDescriptor: (state, name) => {
    if (!state.visibleSensoryDescriptors.includes(name)) {
      state.visibleSensoryDescriptors.push(name)
    }
  },
  removeVisibleSensoryDescriptor: (state, name) => {
    if (state.visibleSensoryDescriptors.includes(name)) {
      state.visibleSensoryDescriptors.splice(state.visibleSensoryDescriptors.indexOf(name), 1)
    }
  },
  updateEquipmentProfile: (state, {
    maxUniqueFermentables,
    targetVolumeGallons,
    mashEfficiency
  }) => {
    Object.assign(state.equipmentProfile, {
      maxUniqueFermentables,
      targetVolumeGallons,
      mashEfficiency
    })
  },
  setBeerProfileKey: (state, {
      key,
      value
    }) =>
    (state.beerProfile[key] = value),
  setSensoryData: (state, sensoryData) => {
    // TODO: Charts are using this data still, want to move it to the Possible data instead
    state.sensoryData = sensoryData
  },
  setRecipeData: (state, recipeData) => (state.recipeData = recipeData),
  setRecipeColorData: (state, recipeColorData) =>
    (state.recipeColorData = recipeColorData),
  setFermentableEnabled: (state, {
    slug,
    enabled
  }) => {
    var matchFermentable = state.allFermentables.find(fermentable => fermentable.slug === slug)
    Object.assign(matchFermentable, {
      enabled
    })
  },
  removeSensoryConstraint(state, name) {
    let sensoryObj = state.currentStyleSensory.find(object => object.name === name)
    if (sensoryObj.configured !== undefined) {
      delete sensoryObj.configured
    }
    state.lastChangedSensoryDescriptor = null
    state.lastSensoryData = null
  },
  addSensoryToModel(state, {
    name,
    min,
    max
  }) {
    // Remove if already exists, just to be safe
    var modelObject = state.sensoryModel.find(object => object.name === name)
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
  setMaxUniqueFermentables(state, value) {
    state.equipmentProfile.maxUniqueFermentables = value
  },
  setLoader(state, {
    name,
    loading
  }) {
    // Creates or updates a loader's status
    let loader = state.loaders.find(loader => loader.name === name)
    if (loader !== undefined) {
      Object.assign(loader, {
        name,
        loading
      })
    } else {
      state.loaders.push({
        name,
        loading
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
  setBjcpSensory(state, value) {
    state.bjcpSensory = value
  },
  resetData(state) {
    state.sensoryData = []
    state.recipeData = []
    state.fermentableCategories = []
    state.currentStyleFermentables = []
    state.currentStyleSensory = ''
    state.currentStyleStats = ''
    state.lastChangedSensoryDescriptor = null
    state.lastSensoryData = null
    state.editingFermentableCategory = null
    state.visibleSensoryDescriptors = []
  },
  setEditingFermentableCategory(state, value) {
    state.editingFermentableCategory = value
  },
  addFermentableChange(state, payload) {
    // Add an unsaved fermentable change to fermentableChanges
    let matchFermentable = state.fermentableChanges.find(fermentable => {
      return fermentable.slug === payload.slug
    })
    if (matchFermentable) {
      Object.assign(matchFermentable, payload)
    } else {
      state.fermentableChanges.push(payload)
    }
  },
  saveFermentableChanges(state) {
    // Commit the unsaved fermentable changes to currentStyleFermentables
    state.fermentableChanges.forEach(change => {
      let matchFermentable = state.currentStyleFermentables.find(current => {
        return current.slug === change.slug
      })

      if (matchFermentable) {
        Object.assign(matchFermentable, change.styleUsage)
      } else {
        state.currentStyleFermentables.push({
          slug: change.slug,
          name: change.name,
          category: change.category,
          min_percent: change.styleUsage.min_percent,
          max_percent: change.styleUsage.max_percent
        })
      }
    })
    state.fermentableChanges = []
  },
  clearFermentableChanges(state) {
    state.fermentableChanges = []
  },
  setCategoryUsage(state, payload) {
    let matchCategory = state.fermentableCategories.find(
      category => category.name === payload.name
    )
    Object.assign(matchCategory, payload)
  },
  setFermentableModelValidity(state, payload) {
    state.fermentableModelValidity = payload
  },
  setFermentableCategoryUsageEdit(state, payload) {
    state.fermentableCategoryUsageEdit = payload
  },
  setSensoryDescriptorsExpanded(state, payload) {
    state.sensoryDescriptorsExpanded = payload
  }
}

export default {
  state,
  getters,
  actions,
  mutations
}
