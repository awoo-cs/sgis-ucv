<template>
  <div>
    <div class="d-flex align-center mb-6">
      <v-btn icon variant="text" to="/incidents" class="mr-2">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div>
        <h1 class="text-h5 font-weight-bold">Registrar Incidente</h1>
        <p class="text-body-2 text-medium-emphasis">Complete todos los campos requeridos (RF2)</p>
      </div>
    </div>

    <v-form ref="formRef" @submit.prevent="handleSubmit">
      <v-row>
        <v-col cols="12" md="8">
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1">Información del incidente</v-card-title>
            <v-card-text>
              <v-text-field
                v-model="form.title"
                label="Título del incidente *"
                :rules="[required]"
                variant="outlined"
                class="mb-3"
              />
              <v-textarea
                v-model="form.description"
                label="Descripción detallada *"
                :rules="[required]"
                variant="outlined"
                rows="4"
                class="mb-3"
              />
              <v-row>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="form.incident_type"
                    :items="typeOptions"
                    label="Tipo de incidente *"
                    :rules="[required]"
                    variant="outlined"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="form.criticality"
                    :items="criticalityOptions"
                    label="Criticidad *"
                    :rules="[required]"
                    variant="outlined"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="form.affected_area"
                    label="Área afectada *"
                    :rules="[required]"
                    variant="outlined"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="form.affected_system"
                    label="Equipo/Sistema involucrado"
                    variant="outlined"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="form.detected_at"
                    label="Fecha y hora de detección *"
                    type="datetime-local"
                    :rules="[required]"
                    variant="outlined"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="form.deadline"
                    label="Fecha límite de atención"
                    type="date"
                    variant="outlined"
                  />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="4">
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1">Asignación (RF4)</v-card-title>
            <v-card-text>
              <v-select
                v-model="form.assigned_to"
                :items="analysts"
                item-title="label"
                item-value="value"
                label="Responsable asignado"
                variant="outlined"
                clearable
              />
            </v-card-text>
          </v-card>

          <v-alert type="info" variant="tonal" class="mb-4" density="compact">
            Al registrar, se generará automáticamente un <strong>plan de acción</strong>
            según el tipo y criticidad (RF6).
          </v-alert>

          <v-btn
            type="submit"
            color="primary"
            block
            size="large"
            :loading="loading"
          >
            <v-icon start>mdi-content-save</v-icon>
            Registrar incidente
          </v-btn>
        </v-col>
      </v-row>
    </v-form>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useIncidentStore } from '@/stores/incidents'
import axios from 'axios'

const router = useRouter()
const store = useIncidentStore()

const formRef = ref(null)
const loading = ref(false)
const analysts = ref([])
const snackbar = ref({ show: false, text: '', color: 'success' })

const form = ref({
  title: '', description: '', incident_type: null, criticality: null,
  affected_area: '', affected_system: '', detected_at: '', deadline: '', assigned_to: null,
})

const required = (v) => !!v || 'Campo requerido'

const typeOptions = [
  { title: 'Malware', value: 'malware' },
  { title: 'Acceso no autorizado', value: 'acceso_no_autorizado' },
  { title: 'Phishing', value: 'phishing' },
  { title: 'Fuga de datos', value: 'fuga_datos' },
  { title: 'Fallo de configuración', value: 'fallo_configuracion' },
  { title: 'Otro', value: 'otro' },
]
const criticalityOptions = [
  { title: 'Bajo', value: 'bajo' },
  { title: 'Medio', value: 'medio' },
  { title: 'Alto', value: 'alto' },
  { title: 'Crítico', value: 'critico' },
]

async function handleSubmit() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  loading.value = true
  try {
    const incident = await store.createIncident(form.value)
    router.push(`/incidents/${incident.id}`)
  } catch (e) {
    snackbar.value = { show: true, text: 'Error al registrar el incidente.', color: 'error' }
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const { data } = await axios.get('/auth/users/')
  analysts.value = data.results?.map(u => ({
    label: `${u.first_name} ${u.last_name} (${u.get_role_display || u.role})`,
    value: u.id,
  })) || []
})
</script>
