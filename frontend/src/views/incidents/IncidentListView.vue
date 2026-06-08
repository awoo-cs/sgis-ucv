<template>
  <div>
    <div class="d-flex align-center mb-4">
      <div>
        <h1 class="text-h5 font-weight-bold">Incidentes</h1>
        <p class="text-body-2 text-medium-emphasis">{{ store.total }} incidentes registrados</p>
      </div>
      <v-spacer />
      <v-btn v-if="auth.canCreateIncident" color="primary" prepend-icon="mdi-plus" to="/incidents/create">
        Registrar incidente
      </v-btn>
    </div>

    <!-- Filtros (RF10) -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row dense>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="filters.search"
              label="Buscar"
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              density="compact"
              clearable
              @update:model-value="debouncedFetch"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-select
              v-model="filters.status"
              :items="statusOptions"
              label="Estado"
              variant="outlined"
              density="compact"
              clearable
              @update:model-value="fetchData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-select
              v-model="filters.criticality"
              :items="criticalityOptions"
              label="Criticidad"
              variant="outlined"
              density="compact"
              clearable
              @update:model-value="fetchData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-select
              v-model="filters.incident_type"
              :items="typeOptions"
              label="Tipo"
              variant="outlined"
              density="compact"
              clearable
              @update:model-value="fetchData"
            />
          </v-col>
          <v-col cols="6" md="3">
            <v-text-field
              v-model="filters.affected_area__icontains"
              label="Área afectada"
              variant="outlined"
              density="compact"
              clearable
              @update:model-value="debouncedFetch"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Tabla -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="store.incidents"
        :loading="store.loading"
        :items-per-page="20"
        @click:row="(_, { item }) => router.push(`/incidents/${item.id}`)"
        hover
      >
        <template #item.criticality="{ item }">
          <CriticalityChip :criticality="item.criticality" />
        </template>
        <template #item.status="{ item }">
          <StatusChip :status="item.status" />
        </template>
        <template #item.detected_at="{ item }">
          {{ formatDate(item.detected_at) }}
        </template>
        <template #item.assigned_to="{ item }">
          {{ item.assigned_to?.first_name || '—' }}
        </template>
        <template #item.actions="{ item }">
          <v-btn icon size="small" variant="text" :to="`/incidents/${item.id}`">
            <v-icon>mdi-eye</v-icon>
          </v-btn>
        </template>
      </v-data-table>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useIncidentStore } from '@/stores/incidents'
import { useAuthStore } from '@/stores/auth'
import StatusChip from '@/components/incidents/StatusChip.vue'
import CriticalityChip from '@/components/incidents/CriticalityChip.vue'

const store = useIncidentStore()
const auth = useAuthStore()
const router = useRouter()

const filters = ref({
  search: '', status: null, criticality: null,
  incident_type: null, affected_area__icontains: '',
})

const statusOptions = [
  { title: 'Abierto', value: 'abierto' },
  { title: 'En Investigación', value: 'en_investigacion' },
  { title: 'Resuelto', value: 'resuelto' },
  { title: 'Cerrado', value: 'cerrado' },
]
const criticalityOptions = [
  { title: 'Bajo', value: 'bajo' },
  { title: 'Medio', value: 'medio' },
  { title: 'Alto', value: 'alto' },
  { title: 'Crítico', value: 'critico' },
]
const typeOptions = [
  { title: 'Malware', value: 'malware' },
  { title: 'Acceso no autorizado', value: 'acceso_no_autorizado' },
  { title: 'Phishing', value: 'phishing' },
  { title: 'Fuga de datos', value: 'fuga_datos' },
  { title: 'Fallo de configuración', value: 'fallo_configuracion' },
  { title: 'Otro', value: 'otro' },
]

const headers = [
  { title: '#', key: 'id', width: 60 },
  { title: 'Título', key: 'title' },
  { title: 'Tipo', key: 'incident_type_display' },
  { title: 'Criticidad', key: 'criticality' },
  { title: 'Estado', key: 'status' },
  { title: 'Área', key: 'affected_area' },
  { title: 'Detectado', key: 'detected_at' },
  { title: 'Responsable', key: 'assigned_to' },
  { title: '', key: 'actions', sortable: false, width: 60 },
]

const formatDate = (d) => d ? new Date(d).toLocaleDateString('es-PE') : '—'

let debounceTimer = null
function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchData, 400)
}

function fetchData() {
  const params = Object.fromEntries(
    Object.entries(filters.value).filter(([, v]) => v !== null && v !== '')
  )
  store.fetchIncidents(params)
}

onMounted(fetchData)
</script>
