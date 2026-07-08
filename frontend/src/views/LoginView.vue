<template>
  <div class="login-root">
    <!-- Fondo 3D -->
    <CyberBackground class="login-bg" :density="1" :shape="true" />
    <div class="login-vignette" />

    <!-- Marca (esquina superior izquierda) -->
    <div class="login-brand">
      <div class="brand-mark">
        <v-icon size="18">mdi-shield-lock</v-icon>
      </div>
      <div>
        <div class="brand-name">SGIS·UCV</div>
        <div class="brand-sub">Security Incident Management</div>
      </div>
    </div>

    <!-- Tarjeta central -->
    <div class="login-center">
      <div class="glass-card">
        <div class="card-border" aria-hidden="true" />

        <div class="form-header">
          <h1 class="form-title">Iniciar sesión</h1>
          <p class="form-sub">Centro de Cómputo — Acceso restringido</p>
        </div>

        <transition name="err">
          <div v-if="error" class="form-error">
            <v-icon size="14" color="#F87171">mdi-alert-circle</v-icon>
            {{ error }}
          </div>
        </transition>

        <form @submit.prevent="handleLogin" class="form-fields">
          <div class="field-block">
            <label class="field-label">Usuario</label>
            <div class="field-wrap" :class="{ active: focusUser }">
              <v-icon size="15" class="field-icon">mdi-account-outline</v-icon>
              <input
                v-model="form.username"
                type="text"
                class="field-input"
                autocomplete="username"
                required
                @focus="focusUser = true"
                @blur="focusUser = false"
              />
            </div>
          </div>

          <div class="field-block">
            <label class="field-label">Contraseña</label>
            <div class="field-wrap" :class="{ active: focusPass }">
              <v-icon size="15" class="field-icon">mdi-lock-outline</v-icon>
              <input
                v-model="form.password"
                :type="showPass ? 'text' : 'password'"
                class="field-input"
                autocomplete="current-password"
                required
                @focus="focusPass = true"
                @blur="focusPass = false"
              />
              <button type="button" class="eye-btn" @click="showPass = !showPass" tabindex="-1">
                <v-icon size="15">{{ showPass ? 'mdi-eye-off' : 'mdi-eye' }}</v-icon>
              </button>
            </div>
          </div>

          <button type="submit" class="submit-btn" :disabled="loading">
            <span v-if="!loading">Acceder</span>
            <span v-else class="loading-dots"><span/><span/><span/></span>
          </button>
        </form>

        <div class="feature-list">
          <div v-for="f in features" :key="f" class="feature-item">
            <span class="feature-dot" />
            {{ f }}
          </div>
        </div>
      </div>

      <p class="form-note">
        Acceso exclusivo para personal autorizado del Centro de Cómputo UCV.
      </p>
    </div>

    <!-- Footer estándares -->
    <div class="login-footer">
      <span>ISO/IEC 27035</span>
      <span class="dot-sep">·</span>
      <span>NIST SP 800-61r2</span>
      <span class="dot-sep">·</span>
      <span>UCV 2026</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import CyberBackground from '@/components/three/CyberBackground.vue'

const router = useRouter()
const auth = useAuthStore()

const loading  = ref(false)
const error    = ref('')
const showPass = ref(false)
const focusUser = ref(false)
const focusPass = ref(false)
const form = ref({ username: '', password: '' })

const features = [
  'Detección y contención automática (SOAR)',
  'Planes de acción y SLA por criticidad',
  'Dashboard de métricas en tiempo real',
  'Reportes exportables en PDF',
]

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(form.value.username, form.value.password)
    router.push('/dashboard')
  } catch {
    error.value = 'Credenciales incorrectas.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* El login es siempre oscuro (pantalla insignia), independiente del toggle */
.login-root {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(ellipse 70% 55% at 50% 40%, rgba(124, 58, 237, 0.16), transparent 65%),
    radial-gradient(ellipse 50% 40% at 80% 90%, rgba(56, 189, 248, 0.10), transparent 60%),
    #07040f;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font);
}

.login-bg { position: absolute; inset: 0; z-index: 0; }
.login-vignette {
  position: absolute; inset: 0; z-index: 1;
  background: radial-gradient(ellipse 80% 70% at 50% 50%, transparent 40%, rgba(7, 4, 15, 0.85) 100%);
  pointer-events: none;
}

/* ─── Marca ──────────────────────────────────────────────────────── */
.login-brand {
  position: absolute; top: 1.75rem; left: 2rem; z-index: 3;
  display: flex; align-items: center; gap: 0.75rem;
}
.brand-mark {
  width: 38px; height: 38px;
  border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #8b5cf6, #6d28d9);
  box-shadow: 0 0 22px rgba(139, 92, 246, 0.55);
}
.brand-mark :deep(.v-icon) { color: #ffffff !important; }
.brand-name {
  font-size: 0.95rem; font-weight: 800; letter-spacing: 0.06em;
  color: #f0edfa; line-height: 1.2;
}
.brand-sub {
  font-size: 0.58rem; font-weight: 500; letter-spacing: 0.14em;
  text-transform: uppercase; color: #8f87b8;
}

/* ─── Tarjeta glass ──────────────────────────────────────────────── */
.login-center {
  position: relative; z-index: 2;
  width: 100%; max-width: 420px;
  padding: 1rem;
  animation: fadeUp 0.5s ease both;
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

.glass-card {
  position: relative;
  border-radius: 16px;
  padding: 2.25rem 2rem 1.75rem;
  background: linear-gradient(165deg, rgba(139, 92, 246, 0.10) 0%, rgba(14, 9, 32, 0.78) 50%);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border: 1px solid rgba(139, 92, 246, 0.22);
  box-shadow:
    0 24px 70px rgba(0, 0, 0, 0.55),
    0 0 40px rgba(124, 58, 237, 0.14);
  overflow: hidden;
}

/* Línea superior con gradiente animado */
.card-border {
  position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, #8b5cf6, #38bdf8, #f472b6, #8b5cf6);
  background-size: 300% 100%;
  animation: borderFlow 6s linear infinite;
}
@keyframes borderFlow { to { background-position: 300% 0; } }

/* ─── Header ─────────────────────────────────────────────────────── */
.form-header { margin-bottom: 1.75rem; }
.form-title {
  font-size: 1.6rem; font-weight: 800; letter-spacing: -0.02em;
  background: linear-gradient(120deg, #f0edfa 30%, #c4b5fd 70%, #7dd3fc);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 0.35rem;
}
.form-sub { font-size: 0.78rem; color: #8f87b8; }

/* ─── Error ──────────────────────────────────────────────────────── */
.form-error {
  display: flex; align-items: center; gap: 0.5rem;
  background: rgba(248, 113, 113, 0.10);
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: 8px;
  padding: 0.65rem 0.875rem;
  font-size: 0.8rem; color: #fca5a5;
  margin-bottom: 1.25rem;
}
.err-enter-active, .err-leave-active { transition: opacity 0.2s, transform 0.2s; }
.err-enter-from, .err-leave-to { opacity: 0; transform: translateY(-4px); }

/* ─── Campos ─────────────────────────────────────────────────────── */
.form-fields { display: flex; flex-direction: column; gap: 1.125rem; }
.field-block { display: flex; flex-direction: column; gap: 0.4rem; }
.field-label {
  font-size: 0.7rem; font-weight: 600; letter-spacing: 0.1em;
  text-transform: uppercase; color: #8f87b8;
}
.field-wrap {
  display: flex; align-items: center;
  border: 1px solid rgba(139, 92, 246, 0.20);
  border-radius: 8px;
  background: rgba(7, 4, 15, 0.55);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  overflow: hidden;
}
.field-wrap.active {
  border-color: #8b5cf6;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.18), 0 0 18px rgba(139, 92, 246, 0.25);
}
.field-icon { color: #5e5787 !important; margin-left: 0.8rem; flex-shrink: 0; }
.field-wrap.active .field-icon { color: #a78bfa !important; }
.field-input {
  flex: 1; height: 44px; padding: 0 0.75rem;
  border: none; outline: none;
  font-family: var(--font); font-size: 0.9rem;
  color: #f0edfa; background: transparent;
}
.field-input:-webkit-autofill,
.field-input:-webkit-autofill:hover,
.field-input:-webkit-autofill:focus {
  -webkit-text-fill-color: #f0edfa;
  -webkit-box-shadow: 0 0 0 1000px #0e0920 inset;
  transition: background-color 9999s ease-in-out 0s;
}
.eye-btn {
  padding: 0 0.75rem; height: 44px;
  background: none; border: none; cursor: pointer;
  display: flex; align-items: center;
}
.eye-btn :deep(.v-icon) { color: #5e5787 !important; }
.eye-btn:hover :deep(.v-icon) { color: #a78bfa !important; }

/* ─── Submit ─────────────────────────────────────────────────────── */
.submit-btn {
  margin-top: 0.375rem;
  width: 100%; height: 44px;
  background: linear-gradient(120deg, #7c3aed, #6d28d9 55%, #0ea5e9 130%);
  color: #ffffff;
  border: none; border-radius: 8px;
  font-family: var(--font); font-size: 0.875rem; font-weight: 600;
  letter-spacing: 0.02em; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 6px 24px rgba(124, 58, 237, 0.40);
  transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}
.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 32px rgba(124, 58, 237, 0.55);
  filter: brightness(1.08);
}
.submit-btn:disabled { opacity: 0.55; cursor: not-allowed; }

.loading-dots { display: flex; gap: 4px; align-items: center; }
.loading-dots span {
  width: 5px; height: 5px; border-radius: 50%; background: #ffffff;
  animation: dot 1s ease-in-out infinite;
}
.loading-dots span:nth-child(2) { animation-delay: 0.15s; }
.loading-dots span:nth-child(3) { animation-delay: 0.3s; }
@keyframes dot {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* ─── Features ───────────────────────────────────────────────────── */
.feature-list {
  margin-top: 1.75rem;
  padding-top: 1.25rem;
  border-top: 1px solid rgba(139, 92, 246, 0.14);
  display: flex; flex-direction: column; gap: 0.55rem;
}
.feature-item {
  display: flex; align-items: center; gap: 0.6rem;
  font-size: 0.74rem; color: #8f87b8; line-height: 1.4;
}
.feature-dot {
  width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0;
  background: linear-gradient(120deg, #8b5cf6, #38bdf8);
  box-shadow: 0 0 8px rgba(139, 92, 246, 0.8);
}

/* ─── Notas y footer ─────────────────────────────────────────────── */
.form-note {
  margin-top: 1.25rem;
  font-size: 0.68rem; color: #5e5787;
  line-height: 1.5; text-align: center;
}
.login-footer {
  position: absolute; bottom: 1.5rem; left: 0; right: 0; z-index: 3;
  display: flex; align-items: center; justify-content: center; gap: 0.5rem;
  font-size: 0.6rem; font-weight: 500; letter-spacing: 0.1em;
  text-transform: uppercase; color: rgba(143, 135, 184, 0.55);
}
.dot-sep { color: rgba(139, 92, 246, 0.35); }

/* ─── Responsive ─────────────────────────────────────────────────── */
@media (max-width: 640px) {
  .login-brand { position: static; justify-content: center; margin-bottom: -2rem; padding-top: 2rem; }
  .login-root { flex-direction: column; }
  .glass-card { padding: 1.75rem 1.25rem 1.5rem; }
}
</style>
