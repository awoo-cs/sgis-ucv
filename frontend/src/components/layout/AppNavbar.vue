<template>
  <header class="sgis-navbar">
    <button class="nav-hamburger" @click="$emit('toggle-drawer')">
      <v-icon size="18" color="#6B6B6B">mdi-menu</v-icon>
    </button>

    <div class="nav-path">
      <span class="path-root">SGIS-UCV</span>
      <span class="path-sep">/</span>
      <span class="path-current">{{ currentPageLabel }}</span>
    </div>

    <div class="nav-spacer" />

    <div class="nav-status">
      <span class="status-dot" />
      <span class="status-text">Operativo</span>
    </div>

    <div class="nav-div" />

    <div class="role-tag">{{ auth.user?.role_display }}</div>

    <div class="nav-div" />

    <div class="nav-user">
      <div class="user-avatar">{{ initials }}</div>
      <span class="user-name">{{ auth.user?.username }}</span>
    </div>

    <button class="logout-btn" @click="handleLogout" title="Cerrar sesión">
      <v-icon size="16" color="#9E9E9E">mdi-logout-variant</v-icon>
    </button>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

defineEmits(['toggle-drawer'])

const PAGE_LABELS = {
  '/dashboard':        'Dashboard',
  '/incidents':        'Incidentes',
  '/incidents/create': 'Registrar',
  '/reports':          'Reportes',
}
const currentPageLabel = computed(() => {
  if (route.path.match(/^\/incidents\/\d+/)) return 'Detalle'
  return PAGE_LABELS[route.path] || '—'
})
const initials = computed(() => {
  const u = auth.user
  if (!u) return '?'
  return `${u.first_name?.[0] || ''}${u.last_name?.[0] || ''}`.toUpperCase() || u.username[0].toUpperCase()
})
function handleLogout() { auth.logout(); router.push('/login') }
</script>

<style scoped>
.sgis-navbar {
  position: fixed; top: 0; left: 0; right: 0;
  z-index: 1000;
  height: 52px;
  background: var(--white);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding-right: 0;
}

.nav-hamburger {
  width: 52px; height: 52px;
  border: none; border-right: 1px solid var(--border);
  background: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: background var(--t);
}
.nav-hamburger:hover { background: var(--bg); }

.nav-path {
  display: flex; align-items: center;
  gap: 0.4rem;
  padding: 0 1rem;
  font-size: 0.8rem;
}
.path-root {
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--ink-3);
  text-transform: uppercase;
}
.path-sep { color: var(--border-hi); }
.path-current {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--ink);
}

.nav-spacer { flex: 1; }

.nav-status {
  display: flex; align-items: center;
  gap: 0.4rem;
  padding: 0 1rem;
}
.status-text {
  font-size: 0.65rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: var(--ink-4);
  text-transform: uppercase;
}

.nav-div { width: 1px; height: 22px; background: var(--border); margin: 0 0.25rem; }

.role-tag {
  padding: 0 0.875rem;
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--ink-3);
}

.nav-user {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0 0.875rem;
}
.user-avatar {
  width: 26px; height: 26px;
  background: var(--ink);
  color: var(--white);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  flex-shrink: 0;
}
.user-name {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--ink-2);
}

.logout-btn {
  width: 48px; height: 52px;
  border: none; border-left: 1px solid var(--border);
  background: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: background var(--t);
}
.logout-btn:hover { background: var(--bg); }
</style>
