<template>
  <b-navbar type="is-primary" wrapper-class="container" shadow>
    <template slot="brand">
      <b-navbar-item
        tag="a"
        class="is-size-5 has-text-weight-bold"
        href="http://localhost:8080"
      >Brewgen</b-navbar-item>
    </template>
    <template slot="start">
      <b-navbar-item href="#">Home</b-navbar-item>
      <b-navbar-item href="#">Documentation</b-navbar-item>
      <b-navbar-dropdown label="Info">
        <b-navbar-item href="#">About</b-navbar-item>
        <b-navbar-item href="#">Contact</b-navbar-item>
      </b-navbar-dropdown>
    </template>

    <template slot="end">
      <b-navbar-item tag="div">
        <div class="buttons">
          <a class="button is-primary">
            <strong>Sign up</strong>
          </a>
          <a class="button is-light">Log in</a>
        </div>
      </b-navbar-item>
    </template>
  </b-navbar>
</template>

<script>
export default {
  name: 'Navbar'
};
</script>

<style>
</style>