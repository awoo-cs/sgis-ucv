<template>
  <div class="dashboard">
    <div class="page-head">
      <div>
        <h1 class="page-title">Dashboard</h1>
        <p class="page-sub">{{ today }}</p>
      </div>
      <button class="refresh-btn" @click="load" :class="{ spinning: loading }">
        <v-icon size="14" color="#6B6B6B">mdi-refresh</v-icon>
      </button>
    </div>

    <!-- KPI row -->
    <div v-if="loading" class="kpi-row">
      <div v-for="n in 4" :key="n" class="kpi-skel" />
    </div>
    <div v-else class="kpi-row">
      <div class="kpi-card kpi-card--accent">
        <div class="kpi-label">Total incidentes</div>
        <div class="kpi-value">{{ metrics?.total ?? 0 }}</div>
        <div class="kpi-sub">registros en el sistema</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Críticos activos</div>
        <div class="kpi-value kpi-value--muted">{{ metrics?.active_critical ?? 0 }}</div>
        <div class="kpi-sub">requieren respuesta inmediata</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Abiertos</div>
        <div class="kpi-value kpi-value--muted">{{ countByStatus('abierto') }}</div>
        <div class="kpi-sub">pendientes de asignación</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Resueltos</div>
        <div class="kpi-value kpi-value--muted">{{ countByStatus('resuelto') }}</div>
        <div class="kpi-sub">cierre pendiente de validación</div>
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
              <div class="bar-row__fill" :style="{ width: pct(item.count, metrics.total) + '%' }" />
            </div>
            <div class="bar-row__count">{{ item.count }}</div>
          </div>
        </template>
        <div v-else-if="!loading" class="no-data">
          <v-icon size="24" color="#E2E2E2">mdi-chart-bar</v-icon>
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
              <div class="bar-row__fill" :style="{ width: pct(item.count, metrics.total) + '%', background: CRIT_COLORS[item.criticality] }" />
            </div>
            <div class="bar-row__count">{{ item.count }}</div>
          </div>
        </template>
        <div v-else-if="!loading" class="no-data">
          <v-icon size="24" color="#E2E2E2">mdi-gauge</v-icon>
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
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useIncidentStore } from '@/stores/incidents'

const store = useIncidentStore()
const loading = ref(true)
const metrics = ref(null)

const today = new Date().toLocaleDateString('es-PE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

const TYPE_LABELS = {
  malware: 'Malware', acceso_no_autorizado: 'Acceso no autorizado',
  phishing: 'Phishing', fuga_datos: 'Fuga de datos',
  fallo_configuracion: 'Fallo de configuración', otro: 'Otro',
}
const CRIT_LABELS  = { bajo: 'Bajo', medio: 'Medio', alto: 'Alto', critico: 'Crítico' }
const CRIT_COLORS  = { bajo: '#9E9E9E', medio: '#6B6B6B', alto: '#3A3A3A', critico: '#0A0A0A' }
const STATUS_DEF   = [
  { key: 'abierto',          label: 'ABIERTO' },
  { key: 'en_investigacion', label: 'INVESTIGACIÓN' },
  { key: 'resuelto',         label: 'RESUELTO' },
  { key: 'cerrado',          label: 'CERRADO' },
]

const pct = (n, total) => total ? Math.round((n / total) * 100) : 0
const countByStatus = (s) => metrics.value?.by_status?.find(x => x.status === s)?.count ?? 0

async function load() {
  loading.value = true
  try {
    await store.fetchMetrics()
    metrics.value = store.metrics
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<style scoped>
.dashboard {
  max-width: 1180px;
  margin: 0 auto;
  animation: fadeUp 0.3s ease both;
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
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
.page-sub {
  font-size: 0.72rem; font-weight: 400;
  color: var(--ink-4); text-transform: capitalize;
}

.refresh-btn {
  width: 30px; height: 30px;
  border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--white); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: border-color var(--t);
}
.refresh-btn:hover { border-color: var(--ink); }
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
