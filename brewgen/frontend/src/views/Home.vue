<template>
  <b-container>
    <b-row>
      <b-col>
        <h2>Brewgen - Beer Recipe Generator</h2>
      </b-col>
    </b-row>
    <b-row>
      <b-col md="6">
        <div class="m-2 mt-3">
          <h5 class="mb-3">Grain Categories</h5>
          <b-list-group flush v-bind:key="category.name" v-for="category in grainCategories">
            <CategoryCard
              v-bind:category="category"
              v-bind:grains="allGrains | inCategory(category.name)"
            />
            <GrainModal
              v-bind:grains="allGrains | inCategory(category.name)"
              v-bind:id="'modal-'+category.name"
              v-bind:category="category"
            />
          </b-list-group>
        </div>
      </b-col>
      <b-col md="6">
        <StyleDropdown :styles="sortedStyles" />
        <EquipmentForm />
        <b-button @click="fetchSensoryData" class="mr-3 ml-2">Update Sensory Info</b-button>
        <b-button @click="updateRecipeData" variant="success">Update Recipe Data</b-button>
        <div class="mt-3">
          <RecipeChart :chartData="recipeChartData" />
        </div>
      </b-col>
    </b-row>
    <b-row>
      <b-col>
        <SensoryRadar :sensoryChartData="sensoryChartData" />
      </b-col>
    </b-row>
    <b-row>
      <b-col>
        <SensoryConstraints :sensoryData="sensoryData" />
      </b-col>
    </b-row>
    <b-row>
      <b-col class="ml-3 mr-3">
        <h5 class="mb-3">Recipes</h5>
        <b-button @click="fetchRecipeData">Get Recipes!</b-button>
        <!-- TODO:
          Create a component that returns a recipe or list of recipes and its details
          Modify the recipe generation API call to limit total recipes returned, maybe return a closest/ideal and then some randoms
        -->
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapGetters, mapActions } from "vuex";

// @ is an alias to /src
import CategoryCard from "@/components/CategoryCard.vue";
import EquipmentForm from "@/components/EquipmentForm.vue";
import GrainModal from "@/components/GrainModal.vue";
import SensoryRadar from "@/components/SensoryRadar.vue";
import SensoryConstraints from "@/components/SensoryConstraints.vue";
import RecipeChart from "@/components/RecipeChart.vue";
import StyleDropdown from "@/components/StyleDropdown.vue";

export default {
  name: "Home",
  components: {
    CategoryCard,
    EquipmentForm,
    GrainModal,
    SensoryRadar,
    SensoryConstraints,
    RecipeChart,
    StyleDropdown
  },
  filters: {
    inCategory: function(value, categoryName) {
      return value.filter(object => object.category == categoryName);
    }
  },
  methods: {
    ...mapActions([
      "fetchGrainCategories",
      "fetchAllGrains",
      "fetchSensoryData",
      "fetchRecipeData",
      "fetchStyles"
    ]),
    updateRecipeData: function() {
      var params = {
        colorOnly: true
      };
      if (this.currentStyleStats != "") {
        params["chartMin"] = this.currentStyleStats.srm.low;
        params["chartMax"] = this.currentStyleStats.srm.high;
      }
      this.fetchRecipeData(params);
    }
  },
  computed: {
    ...mapGetters([
      "grainCategories",
      "allGrains",
      "sensoryData",
      "recipeData",
      "recipeColorData",
      "styles",
      "currentStyleStats"
    ]),
    sensoryChartData: function() {
      // Get the labels in deslugged title-case
      var chartLabels = this.sensoryData.map(element => {
        var value = element.name;
        value = value
          .replace("_", " ")
          .toLowerCase()
          .split(" ");
        for (var i = 0; i < value.length; i++) {
          value[i] = value[i].charAt(0).toUpperCase() + value[i].slice(1);
        }
        return value.join(" ");
      });

      // Set Radar chart series data
      var minData = this.sensoryData.map(element => {
        return element.min;
      });
      var maxData = this.sensoryData.map(element => {
        return element.max;
      });

      // Return the data formatted for ApexCharts
      return {
        options: {
          chart: {
            id: "sensory-min-max"
          },
          labels: chartLabels
        },
        series: [
          {
            name: "Minimum",
            data: minData
          },
          {
            name: "Maximum",
            data: maxData
          }
        ]
      };
    },
    recipeChartData: function() {
      if (this.currentStyleStats != "") {
        var annotations = {
          xaxis: [
            {
              x: this.currentStyleStats.srm.low,
              x2: this.currentStyleStats.srm.high,
              fillColor: "#98C9A3",
              opacity: 0.4,
              label: {
                text: "Style Range"
              }
            }
          ]
        };
      } else {
        var annotations = {};
      }
      // Return the data formatted for ApexCharts
      return {
        options: {
          chart: {
            id: "recipe-srm-distribution"
          },
          xaxis: {
            title: {
              text: "SRM",
              style: {
                fontSize: "1.25rem"
              }
            },
            categories: this.recipeColorData.map(recipe => recipe.srm)
          },
          yaxis: {
            title: {
              text: "Recipe Count",
              style: {
                fontSize: "1.25rem"
              }
            }
          },
          annotations
        },
        series: [
          {
            name: "SRM",
            data: this.recipeColorData.map(recipe => recipe.count)
          }
        ]
      };
    },
    sortedStyles: function() {
      return this.styles.sort((a, b) => (a.name > b.name ? 1 : -1));
    }
  },
  created() {
    this.fetchStyles();
    var prom1 = this.$store.dispatch("fetchGrainCategories");
    var prom2 = this.$store.dispatch("fetchAllGrains");
    Promise.all([prom1, prom2]).then(() => {
      this.fetchSensoryData();
      this.fetchRecipeData({ colorOnly: true });
    });
  }
};
</script>
