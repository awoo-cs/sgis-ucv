<template>
  <v-layout>
    <AppNavbar @toggle-drawer="drawer = !drawer" />
    <AppSidebar v-model="drawer" />
    <v-main style="padding-top: 52px;">
      <div class="main-content">
        <router-view />
      </div>
    </v-main>
  </v-layout>
</template>

<script setup>
import { ref } from 'vue'
import AppNavbar from './AppNavbar.vue'
import AppSidebar from './AppSidebar.vue'

const drawer = ref(true)
</script>

<style scoped>
.main-content {
  min-height: calc(100vh - 52px);
  padding: 2rem 2.25rem;
  background-color: var(--bg);
}
</style>
