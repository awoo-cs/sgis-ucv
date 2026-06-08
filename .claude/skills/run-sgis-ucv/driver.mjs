/**
 * Driver para SGIS-UCV — lanza Chrome headless, hace login y toma screenshots.
 * Uso: node driver.mjs [comando]
 *   smoke       — login + dashboard + crear incidente (default)
 *   login       — solo screenshot del login
 *   dashboard   — screenshot del dashboard tras login
 *   ss <desc>   — screenshot de la página actual (dentro de sesión interactiva)
 *   api <token> — smoke test de los endpoints REST
 */

import { chromium } from 'playwright';
import { mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';

const FRONTEND = 'http://localhost:5173';
const BACKEND  = 'http://localhost:8000';
const SS_DIR   = '/tmp/sgis-screenshots';
const CREDS    = { username: 'admin.ti', password: 'Sgis2026*' };

await mkdir(SS_DIR, { recursive: true });

const cmd = process.argv[2] || 'smoke';

if (cmd === 'api') {
  await apiSmoke(process.argv[3]);
} else {
  await browserSmoke(cmd);
}

async function browserSmoke(mode) {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome-stable',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
    headless: true,
  });
  const ctx  = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();

  async function ss(name) {
    const file = path.join(SS_DIR, `${name}.png`);
    await page.screenshot({ path: file, fullPage: false });
    console.log(`screenshot → ${file}`);
    return file;
  }

  try {
    // --- Login ---
    await page.goto(FRONTEND, { waitUntil: 'networkidle' });
    await ss('01-login');

    if (mode === 'login') return;

    await page.fill('input[type="text"], input[autocomplete="username"]', CREDS.username);
    await page.fill('input[type="password"]', CREDS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 15000 });
    await page.waitForLoadState('networkidle');
    await ss('02-dashboard');

    if (mode === 'dashboard') return;

    // --- Lista de incidentes ---
    await page.click('a[href="/incidents"], .v-list-item[href="/incidents"]');
    await page.waitForLoadState('networkidle');
    await ss('03-incidents-list');

    // --- Crear incidente ---
    const createBtn = page.locator('a[href="/incidents/create"], button:has-text("Registrar")');
    if (await createBtn.count() > 0) {
      await createBtn.first().click();
      await page.waitForLoadState('networkidle');
      await ss('04-incident-create');

      // Rellenar el formulario
      await page.fill('input[label="Título del incidente *"], .v-text-field input', 'Smoke test — malware en Lab-01');
      await page.keyboard.press('Tab');

      // Descripción
      const textarea = page.locator('textarea').first();
      await textarea.fill('Equipo infectado con ransomware detectado en laboratorio 1.');

      // Selectores Vuetify — tipo
      await page.locator('.v-select').nth(0).click();
      await page.locator('.v-list-item:has-text("Malware")').first().click();

      // Criticidad
      await page.locator('.v-select').nth(1).click();
      await page.locator('.v-list-item:has-text("Crítico")').first().click();

      // Área afectada
      const inputs = page.locator('.v-text-field input');
      await inputs.nth(2).fill('Laboratorio 1');

      // Fecha detección
      await inputs.nth(4).fill('2026-06-07T20:00');

      await ss('04b-incident-form-filled');

      await page.click('button[type="submit"], button:has-text("Registrar incidente")');
      await page.waitForLoadState('networkidle');
      await ss('05-incident-detail');
    }

    // --- Reportes ---
    await page.click('a[href="/reports"], .v-list-item[href="/reports"]');
    await page.waitForLoadState('networkidle');
    await ss('06-reports');

    console.log('\n✓ Smoke completo. Screenshots en:', SS_DIR);
  } finally {
    await browser.close();
  }
}

async function apiSmoke(token) {
  const headers = token
    ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };

  // Login
  const loginRes = await fetch(`${BACKEND}/api/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(CREDS),
  });
  const { access } = await loginRes.json();
  const authHeaders = { Authorization: `Bearer ${access}`, 'Content-Type': 'application/json' };

  const checks = [
    ['GET', '/api/auth/me/', null, 200],
    ['GET', '/api/incidents/', null, 200],
    ['GET', '/api/incidents/dashboard/', null, 200],
    ['POST', '/api/incidents/', {
      title: 'API smoke test',
      description: 'Test automatico desde driver',
      incident_type: 'otro',
      criticality: 'bajo',
      affected_area: 'Test',
      detected_at: new Date().toISOString(),
    }, 201],
  ];

  let pass = 0, fail = 0;
  for (const [method, url, body, expectedStatus] of checks) {
    const res = await fetch(`${BACKEND}${url}`, {
      method,
      headers: authHeaders,
      body: body ? JSON.stringify(body) : undefined,
    });
    const ok = res.status === expectedStatus;
    console.log(`${ok ? '✓' : '✗'} ${method} ${url} → ${res.status} (expected ${expectedStatus})`);
    ok ? pass++ : fail++;
  }
  console.log(`\n${pass} passed, ${fail} failed`);
  if (fail > 0) process.exit(1);
}
