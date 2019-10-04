<template>
  <b-modal :id="id" :title="category.name | capitalize">
    <div class="max-height-viewport">
      <b-row>
        <b-col md="6">
          <h5>Recipe Usage</h5>
        </b-col>
        <b-col md="6" class="mb-3">
          <b-input-group prepend="Min" append="%" class="mb-3">
            <b-form-input
              type="number"
              min="0"
              max="100"
              step="1"
              v-bind:value="category.min_percent"
            ></b-form-input>
          </b-input-group>

          <b-input-group prepend="Max" append="%">
            <b-form-input
              type="number"
              min="0"
              max="100"
              step="1"
              v-bind:value="category.max_percent"
            ></b-form-input>
          </b-input-group>
        </b-col>
      </b-row>
      <b-row>
        <b-col class="mb-3">
          <h5>Grains</h5>
        </b-col>
      </b-row>
      <b-row class="scroll">
        <b-col>
          <b-list-group flush>
            <b-list-group-item
              action
              v-bind:class="grain | isDisabled"
              v-on:click="toggleGrain(grain.slug)"
              v-bind:key="grain.slug"
              v-for="grain in grains"
            >
              <span>
                <strong>{{ grain.name }}</strong>
              </span>
              <span class="float-right">Up to {{ grain.max_percent }}%</span>
            </b-list-group-item>
          </b-list-group>
        </b-col>
      </b-row>
    </div>
  </b-modal>
</template>

<script>
export default {
  name: "GrainModal",
  props: ["grains", "id", "category"],
  filters: {
    capitalize: function(value) {
      if (!value) return "";
      value = value.toString();
      return value.charAt(0).toUpperCase() + value.slice(1);
    },
    isDisabled: function(grain) {
      if (grain["enabled"] == false) {
        return " disabled";
      }
    }
  },
  methods: {
    toggleGrain: function(slug) {
      var index = this.grains.findIndex(grain => grain.slug == slug);
      if (this.grains[index]["enabled"] == true) {
        this.grains[index]["enabled"] = false;
      } else {
        this.grains[index]["enabled"] = true;
      }
    }
  }
};
</script>

<style scoped>
.max-height-viewport {
  max-height: 70vh;
}
.scroll {
  overflow-y: auto;
  max-height: calc(70vh - 200px);
}
</style>