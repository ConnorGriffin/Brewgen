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
        <h1>Brewgen - Beer Recipe Generator</h1>
      </b-col>
    </b-row>
    <b-row>
      <b-col md="6">
        <div class="ml-2 mr-2 mb-2">
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
  </b-container>
</template>

<script>
// @ is an alias to /src
import CategoryCard from "@/components/CategoryCard.vue";
import EquipmentForm from "@/components/EquipmentForm.vue";
import GrainModal from "@/components/GrainModal.vue";

export default {
  name: "Home",
  components: {
    CategoryCard,
    EquipmentForm,
    GrainModal
  },
  data() {
    return {
      categories: [],
      grains: [],
      enabledGrains: []
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
  },
  filters: {
    inCategory: function(value, categoryName) {
      return value.filter(object => object.category == categoryName);
    }
  }
};
</script>
