<template>
  <span class="status-chip" :class="`status-chip--${cfg.key}`">
    <span class="sdot" />{{ cfg.label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ status: String })
const MAP = {
  abierto:          { key: 'open',    label: 'Abierto' },
  en_investigacion: { key: 'invest',  label: 'En Investigación' },
  resuelto:         { key: 'done',    label: 'Resuelto' },
  cerrado:          { key: 'closed',  label: 'Cerrado' },
}
const cfg = computed(() => MAP[props.status] || { key: 'open', label: props.status })
</script>

<style scoped>
.status-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 9px;
  border-radius: 99px;
  font-size: 0.7rem;
  font-weight: 500;
  white-space: nowrap;
  border: 1px solid transparent;
}
.sdot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }

.status-chip--open   { background: #F0F0F0; color: var(--ink-2); border-color: var(--border); }
.status-chip--open   .sdot { background: var(--ink-3); }
.status-chip--invest { background: #F5F5F5; color: var(--ink-2); border-color: var(--border-hi); }
.status-chip--invest .sdot { background: #B36B00; }
.status-chip--done   { background: var(--ink); color: var(--white); border-color: var(--ink); }
.status-chip--done   .sdot { background: rgba(255,255,255,0.6); }
.status-chip--closed { background: var(--bg-2); color: var(--ink-4); border-color: var(--border); }
.status-chip--closed .sdot { background: var(--border-hi); }
</style>
