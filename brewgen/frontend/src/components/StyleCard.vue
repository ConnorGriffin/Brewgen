<template>
  <div class="card">
    <div class="card-content">
      <div class="columns">
        <div class="column">
          <span>{{ styleData.name }}</span>
        </div>
        <div class="column">
          <span class="is-pulled-right">Other Data</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'StyleCard',
  props: ['styleData']
};
</script>

<style>
</style>