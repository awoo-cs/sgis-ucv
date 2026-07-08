import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'sgis_theme'

export const useThemeStore = defineStore('theme', () => {
  const mode = ref(localStorage.getItem(STORAGE_KEY) === 'light' ? 'light' : 'dark')

  watch(
    mode,
    (v) => {
      localStorage.setItem(STORAGE_KEY, v)
      document.documentElement.setAttribute('data-theme', v)
    },
    { immediate: true },
  )

  function toggle() {
    mode.value = mode.value === 'dark' ? 'light' : 'dark'
  }

  return { mode, toggle }
})
