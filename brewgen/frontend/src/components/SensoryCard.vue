<template>
  <!-- Defines a sensory card, containing a descriptor name, typical values, and tags -->
  <div class="card has-background-light">
    <div class="card-content">
      <!-- Control buttons on top right -->
      <span class="is-pulled-right">
        <!-- Show edit and delete buttons if type is 'added' -->
        <b-button size="is-small" style="margin-right: .5rem" v-if="type === 'added'">Edit</b-button>
        <a class="delete is-medium" v-if="type === 'added'"></a>

        <!-- Show an Add button if type is 'picker' -->
        <b-button size="is-small" type="is-primary" v-if="type === 'picker'">Add to model</b-button>
      </span>

      <!-- Descriptor name -->
      <span class="has-text-weight-semibold">{{ sensoryData.name | deslug | titleCase }}</span>

      <!-- Descriptor values -->
      <div>
        <!-- Always show the style baseline -->
        <p class="is-size-7">
          <span class="title is-size-7" style="margin-right: .1rem">Style Range:</span>
          {{ sensoryData.style.min.toFixed(3) }} - {{ sensoryData.style.max.toFixed(3) }}
        </p>
        <!-- Show configured value if provided -->
        <p class="is-size-7" v-if="sensoryData.configured !== undefined">
          <span class="title is-size-7" style="margin-right: .1rem">Configured Range:</span>
          {{ sensoryData.configured.min.toFixed(3) }} - {{ sensoryData.configured.max.toFixed(3) }}
        </p>
        <!-- Show possible values if provided -->
        <p class="is-size-7" v-if="sensoryData.possible !== undefined">
          <span class="title is-size-7" style="margin-right: .1rem">Possible Range:</span>
          {{ sensoryData.possible.min.toFixed(3) }} - {{ sensoryData.possible.max.toFixed(3) }}
        </p>
      </div>

      <b-taglist style="margin-top: .5rem">
        <b-tag
          :type="tag.type"
          :key="index"
          v-for="(tag, index) in sensoryData.tags"
        >{{ tag.value }}</b-tag>
      </b-taglist>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SensoryCard',
  props: {
    editable: Boolean,
    type: String,
    sensoryData: Object
  },
  filters: {
    titleCase: function(value) {
      value = value.toLowerCase().split(' ');
      for (var i = 0; i < value.length; i++) {
        value[i] = value[i].charAt(0).toUpperCase() + value[i].slice(1);
      }
      return value.join(' ');
    },
    deslug: function(value) {
      if (!value) return '';
      value = value.toString();
      value = value.replace('_', ' ');
      return value.charAt(0).toUpperCase() + value.slice(1);
    }
  }
};
</script>

<style>
.card {
  box-shadow: none;
  border: 1px solid #e3e3e3;
}
</style>