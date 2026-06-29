import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export const useIncidentStore = defineStore('incidents', () => {
  const incidents = ref([])
  const currentIncident = ref(null)
  const metrics = ref(null)
  const loading = ref(false)
  const total = ref(0)

  async function fetchIncidents(params = {}) {
    loading.value = true
    try {
      const { data } = await axios.get('/incidents/', { params })
      incidents.value = data.results
      total.value = data.count
    } finally {
      loading.value = false
    }
  }

  async function fetchIncident(id) {
    loading.value = true
    try {
      const { data } = await axios.get(`/incidents/${id}/`)
      currentIncident.value = data
    } finally {
      loading.value = false
    }
  }

  async function createIncident(payload) {
    const { data } = await axios.post('/incidents/', payload)
    return data
  }

  async function updateIncident(id, payload) {
    const { data } = await axios.patch(`/incidents/${id}/`, payload)
    currentIncident.value = data
    return data
  }

  async function addComment(incidentId, content) {
    const { data } = await axios.post(`/incidents/${incidentId}/comments/`, { content })
    if (currentIncident.value?.id === incidentId) {
      currentIncident.value.comments.push(data)
    }
    return data
  }

  async function fetchMetrics() {
    const { data } = await axios.get('/incidents/dashboard/')
    metrics.value = data
  }

  async function updateActionPlan(planId, steps) {
    const { data } = await axios.patch(`/action-plans/${planId}/`, { steps })
    if (currentIncident.value?.action_plan?.id === planId) {
      currentIncident.value.action_plan = data
    }
    return data
  }

  async function fetchOperationsFeed() {
    const { data } = await axios.get('/ingest/feed/')
    return data
  }

  // SOAR — paso «Revisar/Liberar»: levanta la contención de una IP (analista/admin_ti).
  async function releaseBlock(ip) {
    const { data } = await axios.post(`/ingest/blocklist/${ip}/release/`)
    return data
  }

  // Reinicia la demo: borra eventos, bloqueos e incidentes del sensor (solo admin_ti).
  async function resetDemo() {
    const { data } = await axios.post('/ingest/reset/')
    return data
  }

  return {
    incidents, currentIncident, metrics, loading, total,
    fetchIncidents, fetchIncident, createIncident, updateIncident,
    addComment, fetchMetrics, updateActionPlan, fetchOperationsFeed,
    releaseBlock, resetDemo,
  }
})
