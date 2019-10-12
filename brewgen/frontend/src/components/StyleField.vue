<template>
  <div class="container">
    <h1 class="title is-size-5">Beer Style</h1>

    <b-modal :active.sync="showStyleListModal" has-modal-card trap-focus>
      <StyleList />
    </b-modal>

    <p>
      <span class="has-text-weight-semibold">Style:</span>
      <span>&nbsp;{{currentStyleName}}</span>

      <b-button
        type="is-primary is-small is-pulled-right"
        @click="showStyleListModal = true"
      >Select Style</b-button>
    </p>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import StyleList from '@/components/StyleList.vue';

export default {
  name: 'StyleField',
  components: {
    StyleList
  },
  data() {
    return {
      showStyleListModal: false
    };
  },
  computed: {
    ...mapGetters(['currentStyleName'])
  }
};
</script>

<style>
</style>