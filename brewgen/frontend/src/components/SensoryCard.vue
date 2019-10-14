<template>
  <!-- Defines a sensory card, containing a descriptor name, typical values, and tags -->
  <div class="card">
    <div class="card-content">
      <p>
        <span class="has-text-weight-semibold">{{ sensoryData.name }}</span>
        <!-- Don't include edit or delete buttons if not editable -->
        <a class="delete is-pulled-right is-medium" v-if="editable"></a>
        <b-button
          class="is-pulled-right"
          size="is-small"
          style="margin-right: .5rem"
          v-if="editable"
        >Edit</b-button>
      </p>
      <!-- Don't show configured value if not provided -->
      <p
        class="is-size-7"
        v-if="sensoryData.configured !== undefined"
      >Configured: {{ sensoryData.configured.min }} - {{ sensoryData.configured.max }}</p>
      <p class="is-size-7">Style: {{ sensoryData.style.min }} - {{ sensoryData.style.max }}</p>
      <b-taglist style="margin-top: .5rem">
        <b-tag type="is-info" :key="tag" v-for="tag in sensoryData.tags">{{ tag }}</b-tag>
      </b-taglist>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SensoryCard',
  props: {
    editable: Boolean,
    sensoryData: Object
  }
};
</script>

<style>
.card {
  box-shadow: none;
  border: 1px solid #e3e3e3;
}
</style>