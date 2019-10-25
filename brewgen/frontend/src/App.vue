<template>
  <div id="app">
    <!-- <div id="nav">
      <router-link to="/">Home</router-link> |
      <router-link to="/about">About</router-link>
    </div>-->
    <router-view />
  </div>
</template>

<script>
</script>

<style lang="scss">
// Import Bulma's core
@import '~bulma/sass/utilities/_all';

$section-padding: 2rem 1.25rem;

// Set your colors
$primary: #e6af2e;
$primary-invert: findColorInvert($primary);
$white: #fbfffe; // White
$black: #212121; // Raisin Black

$rosewood: #6b0504;
$rosewood-invert: findColorInvert($rosewood);
$rufous: #a3320b;
$rufous-invert: findColorInvert($rufous);
$urobilin: #e6af2e;
$urobilin-invert: findColorInvert($urobilin);

$danger: #d63230; // Persian Red
$danger-invert: findColorInvert($danger);

$info: #39a9db; // Maximum Blue
$info-invert: findColorInvert($info);

$link: #1c77c3; // Bright Navy Blue
$link-invert: findColorInvert($link);

$success: #3ec300; // Harlequin Green
$success-invert: findColorInvert($success);

$light: #f7f9f9; // Ghost White
$light-invert: findColorInvert($light);

// Setup $colors to use as bulma classes (e.g. 'is-twitter')
$colors: (
  'white': (
    $white,
    $black
  ),
  'black': (
    $black,
    $white
  ),
  'light': (
    $light,
    $light-invert
  ),
  'dark': (
    $dark,
    $dark-invert
  ),
  'primary': (
    $primary,
    $primary-invert
  ),
  'info': (
    $info,
    $info-invert
  ),
  'success': (
    $success,
    $success-invert
  ),
  'warning': (
    $warning,
    $warning-invert
  ),
  'danger': (
    $danger,
    $danger-invert
  ),
  'rosewood': (
    $rosewood,
    $rosewood-invert
  ),
  'rufous': (
    $rufous,
    $rufous-invert
  ),
  'urobilin': (
    $rufous,
    $rufous-invert
  )
);

// Links
$link: $primary;
$link-invert: $primary-invert;
$link-focus-border: $primary;

// Import Bulma and Buefy styles
@import '~bulma';
@import '~buefy/src/scss/buefy';

// Get rid of the crappy default modal close button
.modal-close {
  display: none;
}
</style>
