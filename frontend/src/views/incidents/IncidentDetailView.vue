<template>
  <div v-if="incident">
    <div class="d-flex align-center mb-4">
      <v-btn icon variant="text" to="/incidents" class="mr-2">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div class="flex-grow-1">
        <h1 class="text-h5 font-weight-bold">{{ incident.title }}</h1>
        <div class="d-flex gap-2 mt-1 flex-wrap align-center">
          <CriticalityChip :criticality="incident.criticality" />
          <StatusChip :status="incident.status" />
          <v-chip size="small" label>{{ incident.incident_type_display }}</v-chip>
          <!-- SLA automático (RNF / V1.1) -->
          <v-chip v-if="sla" size="small" label :style="{ borderColor: sla.color, color: sla.color }" variant="outlined">
            <v-icon start size="14">mdi-timer-outline</v-icon>{{ sla.text }}
          </v-chip>
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
              <v-col cols="6"><strong>Límite SLA:</strong> {{ sla ? formatDate(sla.due_at) : '—' }}</v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- Plan de acción: checklist con evidencia (RF6 / V1.1) -->
        <v-card class="mb-4" v-if="incident.action_plan">
          <v-card-title class="text-subtitle-1 d-flex align-center">
            Plan de Acción
            <v-chip v-if="incident.action_plan.is_customized" size="small" color="warning" class="ml-2">Personalizado</v-chip>
            <v-spacer />
            <span class="text-caption text-medium-emphasis">{{ planDone }}/{{ planSteps.length }} pasos</span>
          </v-card-title>
          <v-progress-linear :model-value="planPct" color="primary" height="4" />
          <v-card-text>
            <div v-for="(step, i) in planSteps" :key="i" class="step-row">
              <v-checkbox
                v-model="step.done"
                :disabled="!canWorkPlan"
                density="compact"
                hide-details
                class="step-check"
              />
              <div class="step-body">
                <div :class="{ 'step-done': step.done }">{{ i + 1 }}. {{ step.text }}</div>
                <div v-if="step.done && step.done_by" class="text-caption text-medium-emphasis">
                  <v-icon size="12">mdi-check-decagram</v-icon>
                  {{ step.done_by }} · {{ formatDate(step.done_at) }}
                </div>
                <v-textarea
                  v-if="step.done || step.evidence"
                  v-model="step.evidence"
                  :readonly="!canWorkPlan"
                  label="Evidencia"
                  variant="outlined"
                  rows="1"
                  auto-grow
                  hide-details
                  density="compact"
                  class="step-evidence mt-1"
                />
              </div>
            </div>
            <v-btn
              v-if="canWorkPlan"
              color="primary"
              size="small"
              class="mt-3"
              :loading="savingPlan"
              :disabled="!planDirty"
              @click="savePlan"
            >
              Guardar avance del plan
            </v-btn>
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

      <!-- Columna lateral: cambio de estado según rol (RF5 / V1.1) -->
      <v-col cols="12" md="4" v-if="showStatusPanel">
        <v-card>
          <v-card-title class="text-subtitle-1">{{ auth.isJefeArea ? 'Validar cierre' : 'Cambiar estado' }} (RF5)</v-card-title>
          <v-card-text>
            <v-alert v-if="auth.isJefeArea" type="info" variant="tonal" density="compact" class="mb-3 text-caption">
              Como Jefe de Área, validas el cierre de incidentes resueltos.
            </v-alert>
            <v-select
              v-model="newStatus"
              :items="nextStatusOptions"
              label="Nuevo estado"
              variant="outlined"
              class="mb-3"
            />
            <v-textarea
              v-model="statusComment"
              :label="auth.isJefeArea ? 'Comentario de validación' : 'Comentario del cambio'"
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
              {{ auth.isJefeArea ? 'Validar y cerrar' : 'Actualizar estado' }}
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
const newComment = ref('')
const addingComment = ref(false)
const newStatus = ref(null)
const statusComment = ref('')
const changingStatus = ref(false)
const savingPlan = ref(false)
const snackbar = ref({ show: false, text: '', color: 'success' })

// ── Plan de acción (checklist local) ──────────────────────────────
const planSteps = ref([])
const planOriginal = ref('[]')
function syncPlan() {
  const steps = incident.value?.action_plan?.steps || []
  planSteps.value = JSON.parse(JSON.stringify(steps))
  planOriginal.value = JSON.stringify(steps)
}
const planDone = computed(() => planSteps.value.filter(s => s.done).length)
const planPct = computed(() => planSteps.value.length ? Math.round(100 * planDone.value / planSteps.value.length) : 0)
const planDirty = computed(() => JSON.stringify(planSteps.value) !== planOriginal.value)
const canWorkPlan = computed(() => auth.canCreateIncident && !incident.value?.is_closed)

// ── SLA ───────────────────────────────────────────────────────────
const SLA_META = {
  en_plazo:   { label: 'En plazo',       color: '#2D9A46' },
  en_riesgo:  { label: 'En riesgo',      color: '#C97A0A' },
  vencido:    { label: 'SLA vencido',    color: '#C0392B' },
  cumplido:   { label: 'SLA cumplido',   color: '#2D9A46' },
  incumplido: { label: 'SLA incumplido', color: '#C0392B' },
}
const sla = computed(() => {
  const s = incident.value?.sla
  if (!s) return null
  const meta = SLA_META[s.status] || { label: s.status, color: '#6B6B6B' }
  let text = meta.label
  if (s.remaining_seconds != null) {
    const abs = Math.abs(s.remaining_seconds)
    const h = Math.floor(abs / 3600), m = Math.floor((abs % 3600) / 60)
    text += s.remaining_seconds < 0 ? ` · ${h}h ${m}m de retraso` : ` · ${h}h ${m}m restantes`
  }
  return { ...meta, text, due_at: s.due_at }
})

// ── Workflow de estados por rol ───────────────────────────────────
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
  let flow = STATUS_FLOW[incident.value.status] || []
  if (auth.isJefeArea) flow = flow.filter(s => s === 'cerrado')   // jefe: solo validar cierre
  else if (auth.isAnalista) flow = flow.filter(s => s !== 'cerrado') // analista: no puede cerrar
  return flow.map(s => ({ title: STATUS_LABELS[s], value: s }))
})
const showStatusPanel = computed(() =>
  incident.value && !incident.value.is_closed && nextStatusOptions.value.length > 0
)

const formatDate = (d) => d ? new Date(d).toLocaleString('es-PE') : '—'
const statusColor = (s) => STATUS_COLORS[s] || 'grey'

async function changeStatus() {
  if (!newStatus.value) return
  changingStatus.value = true
  try {
    await store.updateIncident(props.id, { new_status: newStatus.value, status_comment: statusComment.value })
    await store.fetchIncident(props.id)
    syncPlan()
    newStatus.value = null
    statusComment.value = ''
    snackbar.value = { show: true, text: 'Estado actualizado.', color: 'success' }
  } catch (e) {
    snackbar.value = { show: true, text: e.response?.data?.[0] || e.response?.data?.detail || 'No se pudo actualizar.', color: 'error' }
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
    await store.updateActionPlan(incident.value.action_plan.id, planSteps.value)
    await store.fetchIncident(props.id)
    syncPlan()
    snackbar.value = { show: true, text: 'Avance del plan guardado.', color: 'success' }
  } catch {
    snackbar.value = { show: true, text: 'No se pudo guardar el plan.', color: 'error' }
  } finally {
    savingPlan.value = false
  }
}

onMounted(async () => {
  try {
    await store.fetchIncident(props.id)
    syncPlan()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.step-row { display: flex; align-items: flex-start; gap: 0.25rem; padding: 0.35rem 0; }
.step-check { flex: 0 0 auto; margin-top: -0.35rem; }
.step-body { flex: 1; min-width: 0; }
.step-done { text-decoration: line-through; color: rgba(0, 0, 0, 0.45); }
.step-evidence :deep(textarea) { font-size: 0.82rem; }
</style>
