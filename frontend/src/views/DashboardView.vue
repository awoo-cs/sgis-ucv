<template>
  <div class="dashboard">
    <!-- Fondo 3D sutil (solo en tema oscuro) -->
    <div v-if="isDark" class="dash-bg">
      <CyberBackground :density="0.45" :shape="false" :speed="0.6" />
    </div>

    <div class="dash-content">
      <div class="page-head">
        <div>
          <h1 class="page-title">Dashboard</h1>
          <p class="page-sub">{{ today }}</p>
        </div>
        <button class="refresh-btn" @click="load" :class="{ spinning: loading }">
          <v-icon size="14">mdi-refresh</v-icon>
        </button>
      </div>

      <!-- KPI row -->
      <div v-if="loading" class="kpi-row">
        <div v-for="n in 4" :key="n" class="kpi-skel" />
      </div>
      <div v-else class="kpi-row">
        <div
          v-for="kpi in kpis"
          :key="kpi.key"
          class="kpi-card tilt"
          :class="{ 'kpi-card--accent': kpi.accent }"
          @pointermove="tilt"
          @pointerleave="untilt"
        >
          <div class="kpi-spot" aria-hidden="true" />
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value" :class="{ 'kpi-value--muted': !kpi.accent }">{{ shown[kpi.key] }}</div>
          <div class="kpi-sub">{{ kpi.sub }}</div>
        </div>
      </div>

      <!-- Charts row -->
      <div class="charts-row">
        <div class="panel">
          <div class="section-label">Por tipo de incidente</div>
          <template v-if="!loading && metrics?.by_type?.length">
            <div v-for="item in metrics.by_type" :key="item.incident_type" class="bar-row">
              <div class="bar-row__label">{{ TYPE_LABELS[item.incident_type] || item.incident_type }}</div>
              <div class="bar-row__track">
                <div class="bar-row__fill" :style="{ width: (barsReady ? pct(item.count, metrics.total) : 0) + '%' }" />
              </div>
              <div class="bar-row__count">{{ item.count }}</div>
            </div>
          </template>
          <div v-else-if="!loading" class="no-data">
            <v-icon size="24" color="#8F87B8">mdi-chart-bar</v-icon>
            <span>Sin registros</span>
          </div>
          <div v-else v-for="n in 4" :key="n" class="bar-skel" />
        </div>

        <div class="panel">
          <div class="section-label">Por criticidad</div>
          <template v-if="!loading && metrics?.by_criticality?.length">
            <div v-for="item in metrics.by_criticality" :key="item.criticality" class="bar-row">
              <div class="bar-row__label">{{ CRIT_LABELS[item.criticality] || item.criticality }}</div>
              <div class="bar-row__track">
                <div
                  class="bar-row__fill"
                  :style="{
                    width: (barsReady ? pct(item.count, metrics.total) : 0) + '%',
                    background: critColors[item.criticality],
                    boxShadow: isDark ? `0 0 10px ${critColors[item.criticality]}88` : 'none',
                  }"
                />
              </div>
              <div class="bar-row__count">{{ item.count }}</div>
            </div>
          </template>
          <div v-else-if="!loading" class="no-data">
            <v-icon size="24" color="#8F87B8">mdi-gauge</v-icon>
            <span>Sin registros</span>
          </div>
          <div v-else v-for="n in 4" :key="n" class="bar-skel" />
        </div>

        <div class="panel">
          <div class="section-label">Por estado</div>
          <div class="status-grid">
            <template v-if="!loading && metrics">
              <div v-for="s in STATUS_DEF" :key="s.key" class="status-block">
                <div class="status-block__count">{{ countByStatus(s.key) }}</div>
                <div class="status-block__label">{{ s.label }}</div>
              </div>
            </template>
            <div v-else v-for="n in 4" :key="n" class="skel-sm" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useIncidentStore } from '@/stores/incidents'
import { useThemeStore } from '@/stores/theme'
import CyberBackground from '@/components/three/CyberBackground.vue'

const store = useIncidentStore()
const themeStore = useThemeStore()
const isDark = computed(() => themeStore.mode === 'dark')

const loading = ref(true)
const metrics = ref(null)
const barsReady = ref(false)

const today = new Date().toLocaleDateString('es-PE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

const TYPE_LABELS = {
  malware: 'Malware', acceso_no_autorizado: 'Acceso no autorizado',
  phishing: 'Phishing', fuga_datos: 'Fuga de datos',
  fallo_configuracion: 'Fallo de configuración', otro: 'Otro',
}
const CRIT_LABELS = { bajo: 'Bajo', medio: 'Medio', alto: 'Alto', critico: 'Crítico' }
const critColors = computed(() =>
  isDark.value
    ? { bajo: '#38BDF8', medio: '#8B5CF6', alto: '#F472B6', critico: '#F87171' }
    : { bajo: '#9E9E9E', medio: '#6B6B6B', alto: '#3A3A3A', critico: '#0A0A0A' },
)
const STATUS_DEF = [
  { key: 'abierto',          label: 'ABIERTO' },
  { key: 'en_investigacion', label: 'INVESTIGACIÓN' },
  { key: 'resuelto',         label: 'RESUELTO' },
  { key: 'cerrado',          label: 'CERRADO' },
]

const kpis = [
  { key: 'total',    label: 'Total incidentes',  sub: 'registros en el sistema',            accent: true },
  { key: 'critical', label: 'Críticos activos',  sub: 'requieren respuesta inmediata',      accent: false },
  { key: 'open',     label: 'Abiertos',          sub: 'pendientes de asignación',           accent: false },
  { key: 'resolved', label: 'Resueltos',         sub: 'cierre pendiente de validación',     accent: false },
]

const pct = (n, total) => (total ? Math.round((n / total) * 100) : 0)
const countByStatus = (s) => metrics.value?.by_status?.find((x) => x.status === s)?.count ?? 0

/* ── Contador animado para los KPI ── */
const shown = reactive({ total: 0, critical: 0, open: 0, resolved: 0 })
function countUp(key, target, dur = 900) {
  const start = performance.now()
  const from = 0
  const step = (now) => {
    const p = Math.min((now - start) / dur, 1)
    shown[key] = Math.round(from + (target - from) * (1 - Math.pow(1 - p, 3)))
    if (p < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

/* ── Tilt 3D en las tarjetas KPI ── */
function tilt(e) {
  const el = e.currentTarget
  const r = el.getBoundingClientRect()
  const x = (e.clientX - r.left) / r.width - 0.5
  const y = (e.clientY - r.top) / r.height - 0.5
  el.style.transform = `perspective(700px) rotateY(${x * 7}deg) rotateX(${-y * 7}deg) translateY(-2px)`
  el.style.setProperty('--mx', `${(x + 0.5) * 100}%`)
  el.style.setProperty('--my', `${(y + 0.5) * 100}%`)
}
function untilt(e) {
  e.currentTarget.style.transform = ''
}

async function load() {
  loading.value = true
  barsReady.value = false
  try {
    await store.fetchMetrics()
    metrics.value = store.metrics
    countUp('total', metrics.value?.total ?? 0)
    countUp('critical', metrics.value?.active_critical ?? 0)
    countUp('open', countByStatus('abierto'))
    countUp('resolved', countByStatus('resuelto'))
    await nextTick()
    requestAnimationFrame(() => { barsReady.value = true })
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<style scoped>
.dashboard {
  position: relative;
  animation: fadeUp 0.3s ease both;
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Fondo 3D fijo, detrás del contenido */
.dash-bg {
  position: fixed;
  inset: 52px 0 0 0;
  z-index: 0;
  opacity: 0.5;
  pointer-events: none;
}
.dash-content {
  position: relative;
  z-index: 1;
  max-width: 1180px;
  margin: 0 auto;
}

.page-head {
  display: flex; align-items: flex-end; justify-content: space-between;
  margin-bottom: 1.5rem;
}
.page-title {
  font-size: 1.5rem; font-weight: 700;
  color: var(--ink); letter-spacing: -0.02em;
  line-height: 1; margin-bottom: 0.3rem;
}
[data-theme="dark"] .page-title {
  background: linear-gradient(120deg, #f0edfa 40%, #c4b5fd);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.page-sub {
  font-size: 0.72rem; font-weight: 400;
  color: var(--ink-4); text-transform: capitalize;
}

.refresh-btn {
  width: 30px; height: 30px;
  border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--white); cursor: pointer;
  color: var(--ink-3);
  display: flex; align-items: center; justify-content: center;
  transition: border-color var(--t), box-shadow var(--t);
}
.refresh-btn :deep(.v-icon) { color: inherit !important; }
.refresh-btn:hover { border-color: var(--border-hi); box-shadow: var(--glow); }
.refresh-btn.spinning :deep(.v-icon) { animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.875rem;
  margin-bottom: 0.875rem;
}
.kpi-skel {
  height: 130px;
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  animation: pulse 1.5s ease-in-out infinite;
}

/* Tilt 3D + spotlight que sigue al cursor */
.tilt {
  transform-style: preserve-3d;
  will-change: transform;
  transition: transform 0.18s ease, border-color var(--t), box-shadow 0.25s ease;
}
.kpi-spot {
  position: absolute; inset: 0;
  border-radius: inherit;
  opacity: 0;
  transition: opacity 0.25s ease;
  background: radial-gradient(220px circle at var(--mx, 50%) var(--my, 50%), rgba(139, 92, 246, 0.16), transparent 65%);
  pointer-events: none;
}
.tilt:hover .kpi-spot { opacity: 1; }

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0.875rem;
}
.status-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 0.6rem;
}
.bar-skel {
  height: 10px; background: var(--bg-2);
  border-radius: 2px; margin-bottom: 1rem;
  animation: pulse 1.5s ease-in-out infinite;
}
.skel-sm {
  height: 78px; background: var(--bg-2);
  border-radius: var(--radius);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.6; }
  50%       { opacity: 1; }
}

@media (max-width: 1024px) {
  .kpi-row     { grid-template-columns: repeat(2, 1fr); }
  .charts-row  { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .kpi-row { grid-template-columns: 1fr; }
}
</style>
