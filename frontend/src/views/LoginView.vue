<template>
  <v-app>
    <div class="login-root">
      <!-- Left panel — branding -->
      <div class="login-left">
        <div class="login-left__inner">
          <div class="brand-mark">
            <v-icon color="#0A0A0A" size="20">mdi-shield-lock</v-icon>
          </div>
          <div class="brand-name">SGIS·UCV</div>
          <div class="brand-desc">
            Sistema de Gestión de<br>Incidentes de Seguridad
          </div>

          <div class="feature-list">
            <div v-for="f in features" :key="f" class="feature-item">
              <span class="feature-dash">—</span>
              {{ f }}
            </div>
          </div>
        </div>

        <div class="left-footer">
          <span>ISO/IEC 27035</span>
          <span class="dot-sep">·</span>
          <span>NIST SP 800-61r2</span>
          <span class="dot-sep">·</span>
          <span>UCV 2026</span>
        </div>
      </div>

      <!-- Right panel — form -->
      <div class="login-right">
        <div class="login-form-wrap">
          <div class="form-header">
            <h1 class="form-title">Iniciar sesión</h1>
            <p class="form-sub">Centro de Cómputo — Acceso restringido</p>
          </div>

          <transition name="err">
            <div v-if="error" class="form-error">
              <v-icon size="14" color="#D92B2B">mdi-alert-circle</v-icon>
              {{ error }}
            </div>
          </transition>

          <form @submit.prevent="handleLogin" class="form-fields">
            <div class="field-block">
              <label class="field-label">Usuario</label>
              <div class="field-wrap" :class="{ active: focusUser }">
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
                  <v-icon size="15" color="#9E9E9E">{{ showPass ? 'mdi-eye-off' : 'mdi-eye' }}</v-icon>
                </button>
              </div>
            </div>

            <button type="submit" class="submit-btn" :disabled="loading">
              <span v-if="!loading">Acceder</span>
              <span v-else class="loading-dots"><span/><span/><span/></span>
            </button>
          </form>

          <p class="form-note">
            Acceso exclusivo para personal autorizado del Centro de Cómputo UCV.
          </p>
        </div>
      </div>
    </div>
  </v-app>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const loading  = ref(false)
const error    = ref('')
const showPass = ref(false)
const focusUser = ref(false)
const focusPass = ref(false)
const form = ref({ username: '', password: '' })

const features = [
  'Registro y clasificación de incidentes',
  'Planes de acción automáticos',
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
/* ─── Layout ─────────────────────────────────────────────────────── */
.login-root {
  min-height: 100vh;
  display: flex;
  background: var(--white);
}

/* ─── Left panel ─────────────────────────────────────────────────── */
.login-left {
  width: 360px;
  flex-shrink: 0;
  background: var(--black);
  display: flex;
  flex-direction: column;
  padding: 2.5rem;
  position: relative;
}
.login-left__inner { flex: 1; display: flex; flex-direction: column; gap: 0; }

.brand-mark {
  width: 36px; height: 36px;
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 1.5rem;
  background: rgba(255,255,255,0.05);
}
.brand-mark :deep(.v-icon) { color: #FFFFFF !important; }

.brand-name {
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #FFFFFF;
  margin-bottom: 0.5rem;
}
.brand-desc {
  font-size: 0.8rem;
  font-weight: 400;
  line-height: 1.6;
  color: rgba(255,255,255,0.45);
  margin-bottom: 3rem;
}

.feature-list { display: flex; flex-direction: column; gap: 0.9rem; }
.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  font-size: 0.78rem;
  font-weight: 400;
  color: rgba(255,255,255,0.55);
  line-height: 1.4;
}
.feature-dash {
  color: rgba(255,255,255,0.2);
  flex-shrink: 0;
  font-size: 0.7rem;
  margin-top: 0.05rem;
}

.left-footer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  font-size: 0.6rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: rgba(255,255,255,0.2);
  text-transform: uppercase;
}
.dot-sep { color: rgba(255,255,255,0.12); }

/* ─── Right panel ────────────────────────────────────────────────── */
.login-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--white);
  padding: 3rem 2rem;
}
.login-form-wrap {
  width: 100%;
  max-width: 380px;
  animation: fadeUp 0.3s ease both;
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ─── Form header ────────────────────────────────────────────────── */
.form-header { margin-bottom: 2rem; }
.form-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.02em;
  margin-bottom: 0.35rem;
}
.form-sub {
  font-size: 0.78rem;
  font-weight: 400;
  color: var(--ink-3);
}

/* ─── Error ──────────────────────────────────────────────────────── */
.form-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #FEF1F1;
  border: 1px solid #F5C6C6;
  border-radius: var(--radius);
  padding: 0.65rem 0.875rem;
  font-size: 0.8rem;
  color: #D92B2B;
  margin-bottom: 1.25rem;
}
.err-enter-active, .err-leave-active { transition: opacity 0.2s, transform 0.2s; }
.err-enter-from, .err-leave-to { opacity: 0; transform: translateY(-4px); }

/* ─── Fields ─────────────────────────────────────────────────────── */
.form-fields { display: flex; flex-direction: column; gap: 1.125rem; }

.field-block { display: flex; flex-direction: column; gap: 0.4rem; }
.field-label {
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--ink-2);
}
.field-wrap {
  display: flex;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--white);
  transition: border-color var(--t);
  overflow: hidden;
}
.field-wrap.active { border-color: var(--ink); }
.field-input {
  flex: 1;
  height: 42px;
  padding: 0 0.875rem;
  border: none;
  outline: none;
  font-family: var(--font);
  font-size: 0.9rem;
  font-weight: 400;
  color: var(--ink);
  background: transparent;
}
.field-input::placeholder { color: var(--ink-4); }
.eye-btn {
  padding: 0 0.75rem;
  background: none;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  height: 42px;
  color: var(--ink-4);
}

/* ─── Submit ─────────────────────────────────────────────────────── */
.submit-btn {
  margin-top: 0.375rem;
  width: 100%;
  height: 42px;
  background: var(--black);
  color: var(--white);
  border: none;
  border-radius: var(--radius);
  font-family: var(--font);
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: opacity var(--t);
  display: flex;
  align-items: center;
  justify-content: center;
}
.submit-btn:hover:not(:disabled) { opacity: 0.85; }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.loading-dots { display: flex; gap: 4px; align-items: center; }
.loading-dots span {
  width: 5px; height: 5px; border-radius: 50%; background: var(--white);
  animation: dot 1s ease-in-out infinite;
}
.loading-dots span:nth-child(2) { animation-delay: 0.15s; }
.loading-dots span:nth-child(3) { animation-delay: 0.3s; }
@keyframes dot {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* ─── Footer note ────────────────────────────────────────────────── */
.form-note {
  margin-top: 1.75rem;
  font-size: 0.7rem;
  font-weight: 400;
  color: var(--ink-4);
  line-height: 1.5;
  text-align: center;
}

/* ─── Responsive ─────────────────────────────────────────────────── */
@media (max-width: 640px) {
  .login-root { flex-direction: column; }
  .login-left { width: 100%; padding: 2rem; }
  .brand-desc, .feature-list { display: none; }
}
</style>
