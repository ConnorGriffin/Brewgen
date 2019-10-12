<template>
  <div class="modal-card" style="width: auto">
    <header class="modal-card-head">
      <p class="modal-card-title">Styles</p>
    </header>
    <section class="modal-card-body" :key="style.slug" v-for="style in styles">
      <StyleCard :style="style" />
    </section>
    <footer class="modal-card-foot">
      <button class="button" type="button" @click="$parent.close()">Cancel</button>
      <button class="button is-primary" @click="$parent.close()">Save</button>
    </footer>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import StyleCard from '@/components/StyleCard.vue';

export default {
  name: 'StyleList',
  components: {
    StyleCard
  },
  computed: {
    ...mapGetters(['styles'])
  }
};
</script>,

<style>
</style>