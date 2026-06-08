<template>
  <v-navigation-drawer v-model="model" :width="224" class="sgis-drawer">
    <div class="drawer-brand">
      <div class="brand-icon">
        <v-icon size="16">mdi-shield-lock</v-icon>
      </div>
      <div>
        <div class="brand-name">SGIS-UCV</div>
        <div class="brand-sub">Gestión de Incidentes</div>
      </div>
    </div>

    <div class="drawer-rule" />

    <nav class="nav-list">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ 'nav-item--active': isActive(item.to) }"
      >
        <v-icon :size="16" class="nav-icon">{{ item.icon }}</v-icon>
        {{ item.title }}
      </RouterLink>
    </nav>

    <template #append>
      <div class="drawer-rule" />
      <div class="drawer-foot">
        <div class="foot-status">
          <span class="status-dot" />
          <span>Sistema operativo</span>
        </div>
        <div class="foot-ver">v1.0.0</div>
      </div>
    </template>
  </v-navigation-drawer>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const model = defineModel()
const auth = useAuthStore()
const route = useRoute()

const navItems = computed(() => [
  { title: 'Dashboard',        to: '/dashboard',        icon: 'mdi-view-dashboard-outline' },
  { title: 'Incidentes',       to: '/incidents',        icon: 'mdi-alert-circle-outline' },
  ...(auth.canCreateIncident
    ? [{ title: 'Registrar',   to: '/incidents/create', icon: 'mdi-plus-circle-outline' }]
    : []),
  { title: 'Reportes PDF',     to: '/reports',          icon: 'mdi-file-chart-outline' },
])
const isActive = (to) => route.path === to || route.path.startsWith(to + '/')
</script>

<style scoped>
:deep(.v-navigation-drawer__content) {
  display: flex; flex-direction: column; height: 100%;
  background: var(--white) !important;
}
.sgis-drawer {
  background: var(--white) !important;
  border-right: 1px solid var(--border) !important;
}

.drawer-brand {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 1.125rem 1.125rem 1rem;
}
.brand-icon {
  width: 30px; height: 30px;
  background: var(--ink);
  border-radius: 5px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.brand-icon :deep(.v-icon) { color: #FFFFFF !important; }
.brand-name {
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--ink);
  line-height: 1.2;
}
.brand-sub {
  font-size: 0.58rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: var(--ink-4);
  text-transform: uppercase;
  margin-top: 1px;
}

.drawer-rule { height: 1px; background: var(--border); }

.nav-list {
  display: flex; flex-direction: column;
  gap: 1px;
  padding: 0.5rem 0.625rem;
  flex: 1;
}
.nav-item {
  display: flex; align-items: center; gap: 0.6rem;
  padding: 0.575rem 0.75rem;
  border-radius: var(--radius);
  font-size: 0.83rem;
  font-weight: 500;
  color: var(--ink-3);
  text-decoration: none;
  transition: background var(--t), color var(--t);
}
.nav-item:hover { background: var(--bg); color: var(--ink); }
.nav-item--active {
  background: var(--ink);
  color: var(--white);
}
.nav-item--active :deep(.v-icon) { color: var(--white) !important; }
.nav-icon { flex-shrink: 0; }

.drawer-foot {
  padding: 0.875rem 1.125rem;
  display: flex; flex-direction: column; gap: 0.3rem;
}
.foot-status {
  display: flex; align-items: center; gap: 0.45rem;
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--ink-3);
}
.foot-ver {
  font-size: 0.62rem;
  font-weight: 400;
  color: var(--ink-4);
  letter-spacing: 0.04em;
}
</style>
