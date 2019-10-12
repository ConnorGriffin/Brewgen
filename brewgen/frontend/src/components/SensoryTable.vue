<template>
  <div>
    <b-col class="mt-3">
      <h5 class="mb-3">Sensory Possibilities</h5>
    </b-col>
    <b-col>
      <b-table
        :items="sensoryData"
        :fields="fields"
        sortBy="min"
        sortDesc="true"
        striped
      ></b-table>
    </b-col>
  </div>
</template>

<script>
import _ from 'lodash'

export default {
  name: 'SensoryTable',
  props: ['sensoryData'],
  data () {
    return {
      fields: [
        {
          key: 'name',
          label: 'Descriptor',
          sortable: true,
          formatter: value => {
            value = value.toString()
            value = value
              .replace('_', ' ')
              .toLowerCase()
              .split(' ')
            for (var i = 0; i < value.length; i++) {
              value[i] = value[i].charAt(0).toUpperCase() + value[i].slice(1)
            }
            return value.join(' ')
          }
        },
        {
          key: 'min',
          sortable: true
        },
        {
          key: 'max',
          sortable: true
        }
      ]
    }
  }
}
</script>

<style>
</style>
