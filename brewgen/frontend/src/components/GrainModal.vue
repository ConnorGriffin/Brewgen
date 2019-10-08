<template>
  <b-modal :id="id" :title="category.name | capitalize">
    <div class="max-height-viewport">
      <b-row>
        <b-col md="6">
          <h5>Recipe Usage</h5>
        </b-col>
        <b-col md="6" class="mb-3">
          <b-input-group prepend="Min" append="%" class="mb-3">
            <b-form-input type="number" min="0" max="100" step="1" v-model="minPercent"></b-form-input>
          </b-input-group>

          <b-input-group prepend="Max" append="%">
            <b-form-input type="number" min="0" max="100" step="1" v-model="maxPercent"></b-form-input>
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
              v-on:click="toggleGrain(grain)"
              v-bind:key="grain.slug"
              v-for="grain in grains"
            >
              <span>
                <strong>{{ grain.name }}</strong>
              </span>
              <span class="ml-1 brand">&ndash; {{ grain.brand | capitalize }}</span>
              <span class="float-right">{{ grain.min_percent }} - {{ grain.max_percent }}%</span>
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
  props: ["grains", "id", "category", "index"],
  filters: {
    capitalize: function(value) {
      if (!value) return "";
      value = value.toString();
      return value.charAt(0).toUpperCase() + value.slice(1);
    },
    isDisabled: function(grain) {
      if (grain["enabled"] == false) {
        return " disabled-grain";
      }
    }
  },
  methods: {
    toggleGrain: function(grain) {
      if (grain.enabled == true) {
        this.$store.commit("setGrainEnabled", {
          slug: grain.slug,
          enabled: false
        });
      } else {
        this.$store.commit("setGrainEnabled", {
          slug: grain.slug,
          enabled: true
        });
      }
    }
  },
  computed: {
    minPercent: {
      get() {
        return this.$store.state.brewgen.grainCategories.find(
          category => category.name == this.category.name
        ).min_percent;
      },
      set(value) {
        this.$store.commit("setGrainCategoryValue", {
          grainCategory: this.category.name,
          key: "min_percent",
          value
        });
      }
    },
    maxPercent: {
      get() {
        return this.$store.state.brewgen.grainCategories.find(
          category => category.name == this.category.name
        ).max_percent;
      },
      set(value) {
        this.$store.commit("setGrainCategoryValue", {
          grainCategory: this.category.name,
          key: "max_percent",
          value
        });
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
.disabled-grain {
  text-decoration: line-through;
  pointer-events: auto;
  color: #6c757d;
}
.disabled-grain:hover {
  text-decoration: line-through;
  pointer-events: auto;
  color: #6c757d;
}
.list-group-item {
  cursor: pointer;
}
.brand {
  color: #6c757d;
}
</style>