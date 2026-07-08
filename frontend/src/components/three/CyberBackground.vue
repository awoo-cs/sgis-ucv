<template>
  <canvas ref="el" class="cyber-canvas" />
</template>

<script setup>
// Fondo 3D con Three.js: campo de partículas + poliedro wireframe.
// Se usa en Login (completo) y Dashboard (modo minimal, sin poliedro).
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'

const props = defineProps({
  density: { type: Number, default: 1 },    // multiplicador de partículas
  shape:   { type: Boolean, default: true }, // dibujar poliedro central
  speed:   { type: Number, default: 1 },
})

const el = ref(null)

let renderer = null
let raf = 0
let onResize = null
let onMove = null
const disposables = []

onMounted(() => {
  const canvas = el.value
  if (!canvas) return

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 100)
  camera.position.z = 7

  // ── Partículas (dos nubes: violeta + celeste) ──
  const makePoints = (count, color, size, spread) => {
    const geo = new THREE.BufferGeometry()
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < pos.length; i++) pos[i] = (Math.random() - 0.5) * spread
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    const mat = new THREE.PointsMaterial({
      color, size,
      transparent: true, opacity: 0.75,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
    disposables.push(geo, mat)
    return new THREE.Points(geo, mat)
  }
  const cloudA = makePoints(Math.round(650 * props.density), 0x8b5cf6, 0.045, 18)
  const cloudB = makePoints(Math.round(350 * props.density), 0x38bdf8, 0.035, 16)
  scene.add(cloudA, cloudB)

  // ── Poliedro central (solo Login) ──
  let core = null
  let inner = null
  if (props.shape) {
    const g1 = new THREE.IcosahedronGeometry(2.1, 1)
    const m1 = new THREE.MeshBasicMaterial({ color: 0x8b5cf6, wireframe: true, transparent: true, opacity: 0.32 })
    core = new THREE.Mesh(g1, m1)

    const g2 = new THREE.IcosahedronGeometry(1.35, 0)
    const m2 = new THREE.MeshBasicMaterial({ color: 0x38bdf8, wireframe: true, transparent: true, opacity: 0.22 })
    inner = new THREE.Mesh(g2, m2)

    scene.add(core, inner)
    disposables.push(g1, m1, g2, m2)
  }

  // ── Parallax con el mouse ──
  const mouse = { x: 0, y: 0 }
  onMove = (e) => {
    mouse.x = e.clientX / window.innerWidth - 0.5
    mouse.y = e.clientY / window.innerHeight - 0.5
  }
  window.addEventListener('pointermove', onMove, { passive: true })

  onResize = () => {
    const w = canvas.clientWidth || 1
    const h = canvas.clientHeight || 1
    renderer.setSize(w, h, false)
    camera.aspect = w / h
    camera.updateProjectionMatrix()
  }
  window.addEventListener('resize', onResize)
  onResize()

  const clock = new THREE.Clock()
  const frame = () => {
    const t = clock.getElapsedTime() * props.speed
    cloudA.rotation.y = t * 0.030
    cloudA.rotation.x = t * 0.011
    cloudB.rotation.y = -t * 0.022
    if (core) {
      core.rotation.y = t * 0.12
      core.rotation.x = t * 0.05
      inner.rotation.y = -t * 0.20
      inner.rotation.z = t * 0.08
    }
    camera.position.x += (mouse.x * 1.4 - camera.position.x) * 0.04
    camera.position.y += (-mouse.y * 1.0 - camera.position.y) * 0.04
    camera.lookAt(0, 0, 0)
    renderer.render(scene, camera)
    if (!reduced) raf = requestAnimationFrame(frame)
  }
  frame()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  if (onMove) window.removeEventListener('pointermove', onMove)
  if (onResize) window.removeEventListener('resize', onResize)
  disposables.forEach((d) => d.dispose())
  renderer?.dispose()
  renderer = null
})
</script>

<style scoped>
.cyber-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}
</style>
