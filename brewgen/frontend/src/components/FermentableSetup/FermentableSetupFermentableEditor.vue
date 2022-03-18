<template>
  <!-- Defines the contents of a Fermentable Configurator modal -->
  <div class="modal-card">
    <header class="modal-card-head">
      <p class="modal-card-title">{{ fermentable.name }}</p>
      <a class="delete is-medium is-pulled-right" @click="$parent.close()"></a>
    </header>
    <section class="modal-card-body">
      <div class="columns">
        <!-- Stats -->
        <div class="column is-6">
          <b-field grouped>
            <b-field label="Minimum Usage">
              <b-field>
                <b-input type="number" v-model.number="minUsage" min="0" max="100"></b-input>
                <b-button class="is-static">%</b-button>
              </b-field>
            </b-field>

            <b-field label="Maximum Usage">
              <b-field>
                <b-input type="number" v-model.number="maxUsage" min="0" max="100"></b-input>
                <b-button class="is-static">%</b-button>
              </b-field>
            </b-field>
          </b-field>

          <p>
            <span class="has-text-weight-semibold">Category:</span>
            &nbsp;{{ fermentable.category | titleCase }}
          </p>
          <p>
            <span class="has-text-weight-semibold">Brand:</span>
            &nbsp;{{ fermentable.brand }}
          </p>
          <p>
            <span class="has-text-weight-semibold">Potential:</span>
            &nbsp;{{ fermentable.potential }}
          </p>
          <p>
            <span class="has-text-weight-semibold">Color:</span>
            &nbsp;{{ fermentable.color }} L
          </p>
          <p>
            <span class="has-text-weight-semibold">Recommended Usage:</span>
            &nbsp;{{ fermentable.min_percent }} - {{ fermentable.max_percent }} %
          </p>
        </div>
        <div class="column">
          <b-table :data="sensoryData" :columns="columns" :mobile-cards="false"></b-table>
        </div>
      </div>
    </section>
    <footer class="modal-card-foot">
      <button class="button" type="button" @click="$parent.close()">Cancel</button>
      <b-button type="is-primary" @click="saveChanges">Save</b-button>
      <b-button type="is-danger" outlined @click="disableFermentable">Disable</b-button>
    </footer>
  </div>
</template>

<script>
import { debounce } from 'lodash'

export default {
  name: 'FermentableSetupFermentableEditor',
  props: ['fermentable'],
  data() {
    return {
      minUsage: null,
      maxUsage: null,
      sensoryData: {
        keys: null,
        values: null
      },
      columns: [
        {
          field: 'key',
          label: 'Descriptor'
        },
        {
          field: 'value',
          label: 'Value'
        }
      ]
    }
  },
  created() {
    // Convert sensory_data key/value into an array of formatted key/value pairs
    this.sensoryData = Object.entries(this.fermentable.sensory_data).map(
      ([key, value]) => {
        key = key.toString()
        key = key.replace('_', ' ')
        key = key.toLowerCase().split(' ')
        for (var i = 0; i < key.length; i++) {
          key[i] = key[i].charAt(0).toUpperCase() + key[i].slice(1)
        }
        return {
          key: key.join(' '),
          value
        }
      }
    )
    this.minUsage = this.fermentable.styleUsage.min_percent
    this.maxUsage = this.fermentable.styleUsage.max_percent
  },
  watch: {
    // Increment min and max usage together if they conflict
    minUsage: _.debounce(
      function(value) {
        this.fixUsage('minUsage')
      },
      600,
      { trailing: true }
    ),
    maxUsage: _.debounce(
      function(value) {
        this.fixUsage('maxUsage')
      },
      600,
      { trailing: true }
    )
  },
  filters: {
    titleCase: function(value) {
      var ignore = ['and']
      value = value.toLowerCase().split(' ')
      for (var i = 0; i < value.length; i++) {
        if (!ignore.includes(value[i])) {
          value[i] = value[i].charAt(0).toUpperCase() + value[i].slice(1)
        }
      }
      return value.join(' ')
    }
  },
  methods: {
    fixUsage: function(changedInput) {
      if (changedInput === 'minUsage') {
        if (this.minUsage > this.maxUsage) {
          this.maxUsage = this.minUsage
        }
      } else if (changedInput === 'maxUsage') {
        if (this.minUsage > this.maxUsage) {
          this.minUsage = this.maxUsage
        }
      }
    },
    saveChanges: function() {
      let storeChange = {}
      Object.assign(storeChange, this.fermentable)
      Object.assign(storeChange, {
        styleUsage: {
          min_percent: this.minUsage,
          max_percent: this.maxUsage
        }
      })
      this.$store.commit('addFermentableChange', storeChange)
      this.$parent.close()
    },
    disableFermentable: function() {
      let storeChange = {}
      Object.assign(storeChange, this.fermentable)
      Object.assign(storeChange, {
        styleUsage: {
          min_percent: 0,
          max_percent: 0
        }
      })
      this.$store.commit('addFermentableChange', storeChange)
      this.$parent.close()
    }
  }
}
</script>
