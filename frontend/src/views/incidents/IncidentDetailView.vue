<template>
  <div v-if="incident">
    <div class="d-flex align-center mb-4">
      <v-btn icon variant="text" to="/incidents" class="mr-2">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div class="flex-grow-1">
        <h1 class="text-h5 font-weight-bold">{{ incident.title }}</h1>
        <div class="d-flex gap-2 mt-1 flex-wrap">
          <CriticalityChip :criticality="incident.criticality" />
          <StatusChip :status="incident.status" />
          <v-chip size="small" label>{{ incident.incident_type_display }}</v-chip>
        </div>
      </div>
    </div>

    <v-row>
      <!-- Columna principal -->
      <v-col cols="12" md="8">
        <!-- Info general -->
        <v-card class="mb-4">
          <v-card-title class="text-subtitle-1">Descripción</v-card-title>
          <v-card-text>
            <p>{{ incident.description }}</p>
            <v-divider class="my-3" />
            <v-row dense>
              <v-col cols="6"><strong>Área afectada:</strong> {{ incident.affected_area }}</v-col>
              <v-col cols="6"><strong>Sistema/Equipo:</strong> {{ incident.affected_system || '—' }}</v-col>
              <v-col cols="6"><strong>Detectado:</strong> {{ formatDate(incident.detected_at) }}</v-col>
              <v-col cols="6"><strong>Registrado por:</strong> {{ incident.created_by?.first_name }} {{ incident.created_by?.last_name }}</v-col>
              <v-col cols="6"><strong>Responsable:</strong> {{ incident.assigned_to ? `${incident.assigned_to.first_name} ${incident.assigned_to.last_name}` : '—' }}</v-col>
              <v-col cols="6"><strong>Fecha límite:</strong> {{ incident.deadline || '—' }}</v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- Plan de acción (RF6) -->
        <v-card class="mb-4" v-if="incident.action_plan">
          <v-card-title class="text-subtitle-1 d-flex align-center">
            Plan de Acción
            <v-chip v-if="incident.action_plan.is_customized" size="small" color="warning" class="ml-2">Personalizado</v-chip>
            <v-spacer />
            <v-btn v-if="auth.canCreateIncident && !incident.is_closed" size="small" variant="text" @click="editingPlan = !editingPlan">
              <v-icon>{{ editingPlan ? 'mdi-close' : 'mdi-pencil' }}</v-icon>
            </v-btn>
          </v-card-title>
          <v-card-text>
            <template v-if="!editingPlan">
              <v-list density="compact">
                <v-list-item
                  v-for="(step, i) in incident.action_plan.steps"
                  :key="i"
                  :prepend-avatar="null"
                >
                  <template #prepend>
                    <v-avatar color="primary" size="24" class="mr-2 text-caption">{{ i + 1 }}</v-avatar>
                  </template>
                  {{ step }}
                </v-list-item>
              </v-list>
            </template>
            <template v-else>
              <v-textarea
                v-model="planText"
                label="Pasos (uno por línea)"
                rows="8"
                variant="outlined"
                hint="Un paso por línea"
              />
              <v-btn color="primary" class="mt-2" :loading="savingPlan" @click="savePlan">
                Guardar plan
              </v-btn>
            </template>
          </v-card-text>
        </v-card>

        <!-- Historial de estados (RF5, RF8) -->
        <v-card class="mb-4">
          <v-card-title class="text-subtitle-1">Historial del incidente</v-card-title>
          <v-card-text>
            <v-timeline density="compact" side="end">
              <v-timeline-item
                v-for="entry in incident.status_history"
                :key="entry.id"
                :dot-color="statusColor(entry.new_status)"
                size="small"
              >
                <div class="text-caption text-medium-emphasis">{{ formatDate(entry.changed_at) }}</div>
                <div>
                  <strong>{{ entry.changed_by?.first_name }}</strong>
                  cambió a <StatusChip :status="entry.new_status" />
                </div>
                <div v-if="entry.comment" class="text-body-2 mt-1 text-medium-emphasis">{{ entry.comment }}</div>
              </v-timeline-item>
            </v-timeline>
          </v-card-text>
        </v-card>

        <!-- Comentarios (RF8) -->
        <v-card>
          <v-card-title class="text-subtitle-1">Comentarios</v-card-title>
          <v-card-text>
            <div v-for="c in incident.comments" :key="c.id" class="mb-3">
              <div class="d-flex align-center mb-1">
                <v-icon size="small" class="mr-1">mdi-account-circle</v-icon>
                <strong class="text-body-2">{{ c.author?.first_name }} {{ c.author?.last_name }}</strong>
                <span class="text-caption text-medium-emphasis ml-2">{{ formatDate(c.created_at) }}</span>
              </div>
              <p class="text-body-2 pl-5">{{ c.content }}</p>
              <v-divider />
            </div>
            <v-textarea
              v-model="newComment"
              label="Agregar comentario"
              variant="outlined"
              rows="3"
              class="mt-3"
            />
            <v-btn color="primary" :loading="addingComment" @click="submitComment">
              Agregar comentario
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Columna lateral: cambio de estado -->
      <v-col cols="12" md="4" v-if="auth.canCreateIncident && !incident.is_closed">
        <v-card>
          <v-card-title class="text-subtitle-1">Cambiar estado (RF5)</v-card-title>
          <v-card-text>
            <v-select
              v-model="newStatus"
              :items="nextStatusOptions"
              label="Nuevo estado"
              variant="outlined"
              class="mb-3"
            />
            <v-textarea
              v-model="statusComment"
              label="Comentario del cambio"
              variant="outlined"
              rows="3"
              class="mb-3"
            />
            <v-btn
              color="primary"
              block
              :loading="changingStatus"
              :disabled="!newStatus"
              @click="changeStatus"
            >
              Actualizar estado
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </div>

  <div v-else-if="loading" class="d-flex justify-center mt-12">
    <v-progress-circular indeterminate color="primary" size="64" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useIncidentStore } from '@/stores/incidents'
import { useAuthStore } from '@/stores/auth'
import StatusChip from '@/components/incidents/StatusChip.vue'
import CriticalityChip from '@/components/incidents/CriticalityChip.vue'

const props = defineProps({ id: String })
const store = useIncidentStore()
const auth = useAuthStore()

const loading = ref(true)
const incident = computed(() => store.currentIncident)
const editingPlan = ref(false)
const planText = ref('')
const savingPlan = ref(false)
const newComment = ref('')
const addingComment = ref(false)
const newStatus = ref(null)
const statusComment = ref('')
const changingStatus = ref(false)
const snackbar = ref({ show: false, text: '', color: 'success' })

const STATUS_FLOW = {
  abierto: ['en_investigacion'],
  en_investigacion: ['resuelto'],
  resuelto: ['cerrado'],
  cerrado: [],
}
const STATUS_LABELS = { abierto: 'Abierto', en_investigacion: 'En Investigación', resuelto: 'Resuelto', cerrado: 'Cerrado' }
const STATUS_COLORS = { abierto: 'info', en_investigacion: 'warning', resuelto: 'success', cerrado: 'grey' }

const nextStatusOptions = computed(() => {
  if (!incident.value) return []
  return (STATUS_FLOW[incident.value.status] || []).map(s => ({ title: STATUS_LABELS[s], value: s }))
})

const formatDate = (d) => d ? new Date(d).toLocaleString('es-PE') : '—'
const statusColor = (s) => STATUS_COLORS[s] || 'grey'

async function changeStatus() {
  if (!newStatus.value) return
  changingStatus.value = true
  try {
    await store.updateIncident(props.id, { new_status: newStatus.value, status_comment: statusComment.value })
    await store.fetchIncident(props.id)
    newStatus.value = null
    statusComment.value = ''
    snackbar.value = { show: true, text: 'Estado actualizado.', color: 'success' }
  } finally {
    changingStatus.value = false
  }
}

async function submitComment() {
  if (!newComment.value.trim()) return
  addingComment.value = true
  try {
    await store.addComment(props.id, newComment.value)
    newComment.value = ''
  } finally {
    addingComment.value = false
  }
}

async function savePlan() {
  savingPlan.value = true
  try {
    const steps = planText.value.split('\n').map(s => s.trim()).filter(Boolean)
    await store.updateActionPlan(incident.value.action_plan.id, steps)
    editingPlan.value = false
    snackbar.value = { show: true, text: 'Plan actualizado.', color: 'success' }
  } finally {
    savingPlan.value = false
  }
}

onMounted(async () => {
  try {
    await store.fetchIncident(props.id)
    if (incident.value?.action_plan) {
      planText.value = incident.value.action_plan.steps.join('\n')
    }
  } finally {
    loading.value = false
  }
})
</script>
