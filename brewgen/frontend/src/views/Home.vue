<template>
  <b-container>
    <!-- Modals must be placed outside main content -->
    <b-row id="modals" v-bind:key="category.name" v-for="category in categories">
      <GrainModal
        v-bind:grains="grains | inCategory(category.name)"
        v-bind:id="'modal-'+category.name"
        v-bind:category="category"
      />
    </b-row>

    <b-row>
      <b-col>
        <h2>Brewgen - Beer Recipe Generator</h2>
      </b-col>
    </b-row>
    <b-row>
      <b-col md="6">
        <div class="m-2 mt-3">
          <h5 class="mb-3">Grain Categories</h5>
          <b-list-group flush v-bind:key="category.name" v-for="category in categories">
            <CategoryCard
              v-bind:category="category"
              v-bind:grains="grains | inCategory(category.name)"
            />
          </b-list-group>
        </div>
      </b-col>
      <b-col md="6">
        <EquipmentForm />
      </b-col>
    </b-row>
    <!-- <SensoryList :sensoryData="sensoryData"/> -->
    <SensoryTable :sensoryData="sensoryData"/>
  </b-container>
</template>

<script>
// @ is an alias to /src
import CategoryCard from "@/components/CategoryCard.vue";
import EquipmentForm from "@/components/EquipmentForm.vue";
import GrainModal from "@/components/GrainModal.vue";
import SensoryList from "@/components/SensoryList.vue";
import SensoryTable from "@/components/SensoryTable.vue";

export default {
  name: "Home",
  components: {
    CategoryCard,
    EquipmentForm,
    GrainModal,
    SensoryList,
    SensoryTable
  },
  data() {
    return {
      categories: [],
      grains: [],
      sensoryData: []
    };
  },
  created() {
    this.axios
      .get("http://localhost:5000/api/v1/style-data/grains/categories")
      .then(response => (this.categories = response.data));
    this.axios.get("http://localhost:5000/api/v1/grains").then(response => {
      response.data.forEach(grain => (grain["enabled"] = true));
      this.grains = response.data;
    });
    this.axios
      .post("http://localhost:5000/api/v1/grains/sensory-profiles", {
        grain_list: this.grains.map(grain => grain.slug),
        category_model: [
          {
            name: "base",
            min_percent: 60,
            max_percent: 100
          },
          {
            name: "crystal",
            min_percent: 0,
            max_percent: 25
          },
          {
            name: "roasted",
            min_percent: 0,
            max_percent: 15
          },
          {
            name: "specialty",
            min_percent: 0,
            max_percent: 15
          }
        ],
        sensory_model: null,
        max_unique_grains: 4
      })
      .then(response => (this.sensoryData = response.data));
  },
  filters: {
    inCategory: function(value, categoryName) {
      return value.filter(object => object.category == categoryName);
    }
  }
};
</script>
