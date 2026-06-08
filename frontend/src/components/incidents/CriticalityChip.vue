<template>
  <span class="crit-chip" :class="`crit-chip--${props.criticality}`">
    {{ MAP[props.criticality] || props.criticality }}
  </span>
</template>

<script setup>
const props = defineProps({ criticality: String })
const MAP = { bajo: 'Bajo', medio: 'Medio', alto: 'Alto', critico: 'Crítico' }
</script>

<style scoped>
.crit-chip {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.04em;
}
.crit-chip--bajo    { background: var(--bg-2); color: var(--ink-3); }
.crit-chip--medio   { background: #E5E5E5;     color: var(--ink-2); }
.crit-chip--alto    { background: #C8C8C8;     color: var(--ink);   }
.crit-chip--critico { background: var(--ink);   color: var(--white); }
</style>
