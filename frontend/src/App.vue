<template>
  <v-app>
    <router-view />
  </v-app>
</template>

<script setup>
import { watch } from 'vue'
import { useTheme } from 'vuetify'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
const vuetifyTheme = useTheme()

watch(
  () => themeStore.mode,
  (m) => { vuetifyTheme.global.name.value = m === 'dark' ? 'sgisDark' : 'sgis' },
  { immediate: true },
)
</script>
