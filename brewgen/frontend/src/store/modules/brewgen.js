import axios from "axios";

const state = {
  grainCategories: [],
  allGrains: [],
  equipmentProfile: {
    maxUniqueGrains: 4,
    targetVolumeGallons: 5.5,
    mashEfficiency: 75,
    originalSg: 1.050,
    minSrm: 3,
    maxSrm: 10
  },
  sensoryData: [],
  sensoryModel: [],
  recipeData: [],
  recipeColorData: []
};

const getters = {
  grainCategories: (state) => state.grainCategories,
  allGrains: (state) => state.allGrains,
  sensoryData: (state) => state.sensoryData,
  sensoryModel: (state) => state.sensoryModel,
  getGrainEnabled: (state) => (slug) => {
    return state.allGrains.find(grain => grain.slug == slug).enabled
  },
  recipeData: (state) => state.recipeData,
  recipeColorData: (state) => state.recipeColorData
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
  async fetchRecipeData({ commit }, { colorOnly }) {
    return axios
      .post("http://localhost:5000/api/v1/grains/recipes?coloronly=" + colorOnly, {
        grain_list: state.allGrains.filter(grain => grain.enabled).map(grain => grain.slug),
        category_model: state.grainCategories,
        sensory_model: state.sensoryModel,
        max_unique_grains: Number(state.equipmentProfile.maxUniqueGrains),
        equipment_profile: {
          target_volume_gallons: Number(state.equipmentProfile.targetVolumeGallons),
          mash_efficiency: Number(state.equipmentProfile.mashEfficiency)
        },
        beer_profile: {
          // min_color_srm: Number(state.equipmentProfile.minSrm),
          // max_color_srm: Number(state.equipmentProfile.maxSrm),
          original_sg: Number(state.equipmentProfile.originalSg)
        }
      })
      .then(response => {
        if (colorOnly === undefined || colorOnly == false) {
          commit('setRecipeData', response.data)
          Promise.resolve()
        } else if (colorOnly == true) {
          commit('setRecipeColorData', response.data)
        } else {
          throw "invalid colorOnly parameter value, must be true or undefined"
        }
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
  setRecipeData: (state, recipeData) => state.recipeData = recipeData,
  setRecipeColorData: (state, recipeColorData) => state.recipeColorData = recipeColorData,
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
  }
};

export default {
  state,
  getters,
  actions,
  mutations
};
