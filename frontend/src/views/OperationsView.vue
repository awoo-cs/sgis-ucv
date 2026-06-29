<template>
  <div class="ops">
    <div class="page-head">
      <div>
        <h1 class="page-title">Centro de Operaciones</h1>
        <p class="page-sub">Monitoreo de eventos y detección automática en tiempo real</p>
      </div>
      <div class="head-actions">
        <button v-if="auth.isAdminTI" class="reset-btn" @click="reiniciar">
          <v-icon size="13">mdi-restart</v-icon>Reiniciar demo
        </button>
        <span class="live" :class="{ 'live--paused': !live }">
          <span class="live-dot" />{{ live ? 'EN VIVO' : 'PAUSADO' }}
        </span>
        <button class="pause-btn" @click="live = !live">
          <v-icon size="14" color="#6B6B6B">{{ live ? 'mdi-pause' : 'mdi-play' }}</v-icon>
        </button>
      </div>
    </div>

    <!-- KPIs -->
    <div class="kpi-row">
      <div class="kpi-card kpi-card--accent">
        <div class="kpi-label">Eventos ingeridos</div>
        <div class="kpi-value">{{ counts.events }}</div>
        <div class="kpi-sub">reportados por los sensores</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Alertas disparadas</div>
        <div class="kpi-value kpi-value--muted">{{ counts.alerts }}</div>
        <div class="kpi-sub">eventos que cruzaron una regla</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Incidentes automáticos</div>
        <div class="kpi-value kpi-value--muted">{{ counts.incidents }}</div>
        <div class="kpi-sub">creados por el motor de reglas</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">IPs contenidas</div>
        <div class="kpi-value" :class="counts.blocked ? 'kpi-value--block' : 'kpi-value--muted'">{{ counts.blocked }}</div>
        <div class="kpi-sub">bloqueadas automáticamente (SOAR)</div>
      </div>
    </div>

    <div class="ops-grid">
      <!-- Stream de eventos (consola oscura) -->
      <div class="console">
        <div class="console-head">
          <span class="section-label section-label--light">Flujo de eventos</span>
          <span class="console-meta">{{ events.length }} recientes</span>
        </div>
        <div class="stream">
          <TransitionGroup name="ev">
            <div v-for="ev in events" :key="ev.id" class="ev" :class="{ 'ev--alert': ev.is_alert }">
              <span class="ev-time">{{ time(ev.received_at) }}</span>
              <span class="ev-ip">{{ ev.source_ip }}</span>
              <span class="ev-type" :class="`ev-type--${ev.event_type}`">{{ typeLabel(ev) }}</span>
              <span class="ev-detail">{{ ev.detail || '—' }}</span>
              <span v-if="ev.is_alert" class="ev-rule">{{ RULE_LABELS[ev.rule] || ev.rule }}</span>
            </div>
          </TransitionGroup>
          <div v-if="!events.length" class="stream-empty">
            Esperando eventos…&nbsp; Lanza el sensor o el atacante.
          </div>
        </div>
      </div>

      <div class="side-col">
      <!-- Contención automática (SOAR) -->
      <div class="panel">
        <div class="section-label">Contención automática (SOAR)</div>
        <div v-if="blockedIps.length" class="block-list">
          <div v-for="b in blockedIps" :key="b.id" class="block">
            <div class="block-head">
              <v-icon size="14" color="#C0392B">mdi-cancel</v-icon>
              <span class="block-ip">{{ b.source_ip }}</span>
              <span class="block-rule">{{ RULE_LABELS[b.rule] || b.rule }}</span>
            </div>
            <!-- Playbook SOAR: el recorrido de la respuesta automática paso a paso -->
            <div class="pb-steps">
              <span class="pb on">Detectar</span>
              <span class="pb on">Contener</span>
              <span class="pb" :class="{ on: b.alerted_at }">Notificar</span>
              <span class="pb on">Documentar</span>
              <button v-if="auth.canCreateIncident" class="pb-release" @click="liberar(b.source_ip)">
                Liberar
              </button>
            </div>
          </div>
        </div>
        <div v-else class="no-data">
          <v-icon size="24" color="#E2E2E2">mdi-shield-outline</v-icon>
          <span>Ninguna IP contenida</span>
        </div>
      </div>

      <!-- Incidentes auto-generados -->
      <div class="panel">
        <div class="section-label">Incidentes automáticos</div>
        <div v-if="incidents.length" class="inc-list">
          <RouterLink
            v-for="inc in incidents" :key="inc.id"
            :to="`/incidents/${inc.id}`" class="inc"
          >
            <span class="inc-crit" :style="{ background: CRIT_COLORS[inc.criticality] }" />
            <div class="inc-body">
              <div class="inc-title">{{ inc.title }}</div>
              <div class="inc-meta">
                {{ STATUS_LABELS[inc.status] }} · {{ time(inc.created_at) }}
              </div>
            </div>
          </RouterLink>
        </div>
        <div v-else class="no-data">
          <v-icon size="24" color="#E2E2E2">mdi-shield-check-outline</v-icon>
          <span>Sin incidentes</span>
        </div>
      </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useIncidentStore } from '@/stores/incidents'
import { useAuthStore } from '@/stores/auth'

const store = useIncidentStore()
const auth = useAuthStore()

const counts = reactive({ events: 0, alerts: 0, incidents: 0, sensors: 0, blocked: 0 })
const events = ref([])
const incidents = ref([])
const blockedIps = ref([])
const live = ref(true)
let timer = null

const RULE_LABELS = { port_scan: 'ESCANEO', brute_force: 'FUERZA BRUTA', blacklist_ip: 'IP LISTA NEGRA' }
const STATUS_LABELS = { abierto: 'Abierto', en_investigacion: 'En investigación', resuelto: 'Resuelto', cerrado: 'Cerrado' }
const CRIT_COLORS = { bajo: '#9E9E9E', medio: '#6B6B6B', alto: '#C0392B', critico: '#7B241C' }

const time = (iso) => new Date(iso).toLocaleTimeString('es-PE', { hour12: false })
const typeLabel = (ev) => ({
  connection: 'CONEXIÓN', auth_failure: 'LOGIN✗', auth_success: 'LOGIN✓', other: 'EVENTO',
}[ev.event_type] || ev.event_type)

async function poll() {
  if (!live.value) return
  try {
    const data = await store.fetchOperationsFeed()
    Object.assign(counts, data.counts)
    events.value = data.events
    incidents.value = data.incidents
    blockedIps.value = data.blocked_ips || []
  } catch {
    /* silencioso: si una lectura falla, reintenta en el próximo ciclo */
  }
}

// SOAR — «Revisar/Liberar»: el operador levanta la contención de una IP.
async function liberar(ip) {
  try {
    await store.releaseBlock(ip)
    blockedIps.value = blockedIps.value.filter((b) => b.source_ip !== ip) // optimista
    poll()
  } catch {
    /* si falla, el próximo poll vuelve a mostrar la IP */
  }
}

// Reinicia el tablero para repetir la demo (borra solo lo generado por el sensor).
async function reiniciar() {
  if (!confirm('¿Reiniciar la demo? Se borrarán los eventos, las IPs contenidas y los '
    + 'incidentes generados por el sensor. Los incidentes registrados a mano se conservan.')) return
  try {
    await store.resetDemo()
    poll()
  } catch {
    /* noop */
  }
}

// ponytail: polling cada 2s — suficiente para una demo. Si hace falta tiempo real
// fino, migrar a Server-Sent Events (sin dependencias) o WebSockets (channels).
watch(live, (on) => { if (on) poll() })
onMounted(() => {
  poll()
  timer = setInterval(poll, 2000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.ops { max-width: 1180px; margin: 0 auto; animation: fadeUp 0.3s ease both; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.page-head { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 1.5rem; }
.page-title { font-size: 1.5rem; font-weight: 700; color: var(--ink); letter-spacing: -0.02em; line-height: 1; margin-bottom: 0.3rem; }
.page-sub { font-size: 0.72rem; font-weight: 400; color: var(--ink-4); }

.head-actions { display: flex; align-items: center; gap: 0.6rem; }
.live {
  display: inline-flex; align-items: center; gap: 0.45rem;
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.12em;
  color: #C0392B; padding: 0.3rem 0.55rem;
  border: 1px solid #E8C5C0; border-radius: 99px; background: #FCF3F2;
}
.live--paused { color: var(--ink-4); border-color: var(--border); background: var(--bg); }
.live-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; animation: blink 1.1s ease-in-out infinite; }
.live--paused .live-dot { animation: none; }
@keyframes blink { 50% { opacity: 0.25; } }
.pause-btn {
  width: 30px; height: 30px; border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--white); cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: border-color var(--t);
}
.pause-btn:hover { border-color: var(--ink); }

.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.875rem; margin-bottom: 0.875rem; }

.ops-grid { display: grid; grid-template-columns: 1.7fr 1fr; gap: 0.875rem; align-items: start; }

/* ── Consola oscura ── */
.console {
  background: var(--black); border: 1px solid var(--black);
  border-radius: var(--radius-lg); overflow: hidden;
}
.console-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.9rem 1.1rem; border-bottom: 1px solid #222;
}
.section-label--light { color: #9a9a9a !important; border: none !important; padding: 0 !important; margin: 0 !important; }
.console-meta { font-size: 0.6rem; color: #6a6a6a; letter-spacing: 0.1em; text-transform: uppercase; }

.stream {
  padding: 0.5rem; max-height: 540px; overflow-y: auto;
  font-family: 'SF Mono', ui-monospace, 'JetBrains Mono', Menlo, monospace;
}
.ev {
  display: grid;
  grid-template-columns: 4.6rem 8.5rem 5.2rem 1fr auto;
  align-items: center; gap: 0.6rem;
  padding: 0.4rem 0.6rem; border-radius: var(--radius);
  font-size: 0.74rem; color: #c8c8c8; white-space: nowrap;
}
.ev:hover { background: #161616; }
.ev--alert { background: rgba(192, 57, 43, 0.10); }
.ev--alert:hover { background: rgba(192, 57, 43, 0.16); }
.ev-time { color: #6a6a6a; font-variant-numeric: tabular-nums; }
.ev-ip { color: #e8e8e8; font-variant-numeric: tabular-nums; }
.ev-type { font-size: 0.6rem; font-weight: 700; letter-spacing: 0.06em; color: #8a8a8a; }
.ev-type--auth_failure { color: #d98a3d; }
.ev-detail { color: #9a9a9a; overflow: hidden; text-overflow: ellipsis; }
.ev-rule {
  font-size: 0.56rem; font-weight: 800; letter-spacing: 0.08em;
  color: #fff; background: #C0392B; padding: 0.15rem 0.4rem; border-radius: 3px;
}
.stream-empty { padding: 2.5rem 1rem; text-align: center; color: #5a5a5a; font-size: 0.78rem; }

/* animación de entrada de cada evento nuevo */
.ev-enter-active { transition: all 0.35s ease; }
.ev-enter-from { opacity: 0; transform: translateX(-8px); }

.kpi-value--block { color: #C0392B !important; }

/* ── Contención (SOAR) ── */
.side-col { display: flex; flex-direction: column; gap: 0.875rem; }
.block-list { display: flex; flex-direction: column; gap: 0.4rem; }
.block {
  padding: 0.5rem 0.55rem 0.55rem; border-radius: var(--radius);
  border: 1px solid var(--border); background: var(--white);
}
.block-head {
  display: flex; align-items: center; gap: 0.5rem;
  font-family: 'SF Mono', ui-monospace, Menlo, monospace;
}
.block-ip { font-size: 0.78rem; font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums; }
.block-rule {
  margin-left: auto; font-size: 0.56rem; font-weight: 800; letter-spacing: 0.06em;
  color: #fff; background: #C0392B; padding: 0.12rem 0.38rem; border-radius: 3px;
}

/* ── Pasos del playbook SOAR ── */
.pb-steps { display: flex; flex-wrap: wrap; align-items: center; gap: 0.3rem; margin-top: 0.5rem; }
.pb {
  position: relative; font-size: 0.56rem; font-weight: 700; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--ink-4); background: var(--bg);
  border: 1px solid var(--border); border-radius: 99px; padding: 0.14rem 0.46rem;
}
.pb.on { color: var(--white); background: var(--ink); border-color: var(--ink); }
.pb.on::before { content: '✓ '; }
.pb-release {
  margin-left: auto; font-size: 0.58rem; font-weight: 800; letter-spacing: 0.05em;
  color: #C0392B; background: #FCF3F2; border: 1px solid #E8C5C0;
  border-radius: 99px; padding: 0.16rem 0.55rem; cursor: pointer; transition: all var(--t);
}
.pb-release:hover { color: #fff; background: #C0392B; border-color: #C0392B; }

/* ── Botón Reiniciar demo (cabecera) ── */
.reset-btn {
  display: inline-flex; align-items: center; gap: 0.3rem;
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.04em;
  color: var(--ink-2); background: var(--white);
  border: 1px solid var(--border); border-radius: 99px; padding: 0.3rem 0.6rem;
  cursor: pointer; transition: all var(--t);
}
.reset-btn:hover { color: var(--ink); border-color: var(--ink); }

/* ── Incidentes ── */
.inc-list { display: flex; flex-direction: column; gap: 0.2rem; }
.inc {
  display: flex; align-items: stretch; gap: 0.7rem; text-decoration: none;
  padding: 0.6rem 0.5rem; border-radius: var(--radius); transition: background var(--t);
}
.inc:hover { background: var(--bg); }
.inc-crit { width: 3px; border-radius: 99px; flex-shrink: 0; }
.inc-title { font-size: 0.78rem; font-weight: 500; color: var(--ink); line-height: 1.3; margin-bottom: 0.15rem; }
.inc-meta { font-size: 0.62rem; color: var(--ink-4); letter-spacing: 0.02em; }

@media (max-width: 1024px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .ops-grid { grid-template-columns: 1fr; }
}
@media (max-width: 600px) { .kpi-row { grid-template-columns: 1fr; } }
</style>
