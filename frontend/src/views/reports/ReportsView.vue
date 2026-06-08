<template>
  <div>
    <h1 class="text-h5 font-weight-bold mb-1">Reportes PDF</h1>
    <p class="text-body-2 text-medium-emphasis mb-6">Exportar historial de incidentes para auditorías (RF9)</p>

    <v-card max-width="600">
      <v-card-title class="text-subtitle-1">Configurar reporte</v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="6">
            <v-select
              v-model="filters.status"
              :items="statusOptions"
              label="Estado"
              variant="outlined"
              clearable
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-select
              v-model="filters.criticality"
              :items="criticalityOptions"
              label="Criticidad"
              variant="outlined"
              clearable
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-select
              v-model="filters.incident_type"
              :items="typeOptions"
              label="Tipo de incidente"
              variant="outlined"
              clearable
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="filters.affected_area__icontains"
              label="Área afectada"
              variant="outlined"
              clearable
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="filters.detected_from"
              label="Detectado desde"
              type="date"
              variant="outlined"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="filters.detected_to"
              label="Detectado hasta"
              type="date"
              variant="outlined"
            />
          </v-col>
        </v-row>

        <v-btn
          color="error"
          size="large"
          block
          class="mt-2"
          :loading="loading"
          prepend-icon="mdi-file-pdf-box"
          @click="downloadPdf"
        >
          Descargar Reporte PDF
        </v-btn>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const loading = ref(false)
const filters = ref({
  status: null, criticality: null, incident_type: null,
  affected_area__icontains: '', detected_from: '', detected_to: '',
})

const statusOptions = [
  { title: 'Abierto', value: 'abierto' },
  { title: 'En Investigación', value: 'en_investigacion' },
  { title: 'Resuelto', value: 'resuelto' },
  { title: 'Cerrado', value: 'cerrado' },
]
const criticalityOptions = [
  { title: 'Bajo', value: 'bajo' }, { title: 'Medio', value: 'medio' },
  { title: 'Alto', value: 'alto' }, { title: 'Crítico', value: 'critico' },
]
const typeOptions = [
  { title: 'Malware', value: 'malware' },
  { title: 'Acceso no autorizado', value: 'acceso_no_autorizado' },
  { title: 'Phishing', value: 'phishing' },
  { title: 'Fuga de datos', value: 'fuga_datos' },
  { title: 'Fallo de configuración', value: 'fallo_configuracion' },
  { title: 'Otro', value: 'otro' },
]

async function downloadPdf() {
  loading.value = true
  try {
    const params = Object.fromEntries(
      Object.entries(filters.value).filter(([, v]) => v !== null && v !== '')
    )
    const response = await axios.get('/reports/pdf/', {
      params,
      responseType: 'blob',
    })
    const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `sgis_reporte_${new Date().toISOString().slice(0, 10)}.pdf`
    link.click()
    URL.revokeObjectURL(url)
  } finally {
    loading.value = false
  }
}
</script>
