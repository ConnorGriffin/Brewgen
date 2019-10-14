<template>
  <!-- Defines the style picker modal -->
  <div class="modal-card" style="height: calc(100vh - 40px)">
    <header class="modal-card-head">
      <p class="modal-card-title">Styles</p>
    </header>
    <section class="modal-card-body" style="height:100%">
      <b-input
        icon="search"
        placeholder="Filter"
        type="search"
        style="margin-bottom: .5rem"
        v-model="styleListFilter"
      ></b-input>
      <div class="list is-hoverable">
        <StyleCard :key="style.slug" v-for="style in filteredStyles" :styleData="style" />
      </div>
    </section>
    <footer class="modal-card-foot">
      <button class="button" type="button" @click="$parent.close()">Cancel</button>
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
    ...mapGetters(['styles']),
    sortedStyles: function() {
      return this.styles.sort((a, b) => (a.name > b.name ? 1 : -1));
    },
    styleListFilter: {
      get() {
        return this.$store.state.brewgen.styleListFilter;
      },
      set(value) {
        this.$store.commit('setStyleListFilter', value);
      }
    },
    //
    filteredStyles: function() {
      let filterWords = this.styleListFilter.trim().split(' ');

      // Search for each filter word in each name or category
      let filterArray = filterWords.map(word => {
        let matchedStyles = this.sortedStyles.filter(styleData => {
          return (
            styleData.name.toLowerCase().match(word.toLowerCase()) ||
            styleData.category.toLowerCase().match(word.toLowerCase())
          );
        });
        if (matchedStyles !== undefined) {
          return matchedStyles.map(style => style.slug);
        }
      });

      // Find items that are common among results for all filter words
      let styleIntersect = this.intersection(filterArray);

      // Return style objects for each common item
      return this.sortedStyles.filter(styleData => {
        return styleIntersect.includes(styleData.slug);
      });
    }
  },
  methods: {
    intersection: function() {
      var result = [];
      var lists;

      if (arguments.length === 1) {
        lists = arguments[0];
      } else {
        lists = arguments;
      }

      for (var i = 0; i < lists.length; i++) {
        var currentList = lists[i];
        for (var y = 0; y < currentList.length; y++) {
          var currentValue = currentList[y];
          if (result.indexOf(currentValue) === -1) {
            if (
              lists.filter(function(obj) {
                return obj.indexOf(currentValue) == -1;
              }).length == 0
            ) {
              result.push(currentValue);
            }
          }
        }
      }
      return result;
    }
  }
};
</script>,

<style>
</style>