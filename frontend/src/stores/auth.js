import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const accessToken = ref(localStorage.getItem('access_token') || null)

  const isAuthenticated = computed(() => !!accessToken.value)
  const isAdminTI = computed(() => user.value?.role === 'admin_ti')
  const isAnalista = computed(() => user.value?.role === 'analista')
  const isJefeArea = computed(() => user.value?.role === 'jefe_area')
  const canCreateIncident = computed(() => isAdminTI.value || isAnalista.value)

  async function login(username, password) {
    const { data } = await axios.post('/auth/login/', { username, password })
    accessToken.value = data.access
    user.value = data.user
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    localStorage.setItem('user', JSON.stringify(data.user))
  }

  function logout() {
    accessToken.value = null
    user.value = null
    localStorage.clear()
  }

  return { user, accessToken, isAuthenticated, isAdminTI, isAnalista, isJefeArea, canCreateIncident, login, logout }
})
