const fs = require('fs');
const path = require('path');
const { test, devices } = require('@playwright/test');

test.setTimeout(240000);

const RESULTS_DIR = path.join(process.cwd(), 'mcpd-audit-results');
const SCREENSHOT_DIR = path.join(RESULTS_DIR, 'screenshots');
const BASE_URL = process.env.MCPD_AUDIT_BASE_URL || 'https://mcpd-production.up.railway.app';
const USERNAME = process.env.MCPD_AUDIT_USERNAME || 'robertrichards';
const PASSWORD = process.env.MCPD_AUDIT_PASSWORD || 'Stonecold1!';

const pagesToAudit = [
  { name: 'dashboard', path: '/dashboard' },
  { name: 'mobile-home', path: '/mobile/home', mobile: true },
  { name: 'mobile-start-incident', path: '/mobile/incident/start', mobile: true },
  { name: 'mobile-facts', path: '/mobile/incident/facts', mobile: true },
  { name: 'law-lookup-assault', path: '/legal/search?q=Victim%20said%20husband%20pushed%20her%20and%20took%20her%20phone&source=ALL&state=GA' },
  { name: 'law-lookup-base-reentry', path: '/legal/search?q=A%20man%20came%20back%20onto%20base%20after%20being%20told%20by%20police%20not%20to%20return&source=ALL&state=GA' },
  { name: 'reports-list', path: '/reports' },
  { name: 'reports-new', path: '/reports/new' },
  { name: 'forms', path: '/forms' },
  { name: 'forms-saved', path: '/forms/saved' },
  { name: 'orders', path: '/orders/reference' },
  { name: 'training', path: '/training/menu' },
  { name: 'personnel', path: '/admin/users' },
  { name: 'scanner-mobile-person', path: '/mobile/incident/persons/edit', mobile: true },
  { name: 'scenario-builder', path: '/forms/call-types' },
  { name: 'navigator-editor', path: '/incident-paperwork-guide/manage' },
];

function ensureDirs() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function markdownEscape(value) {
  return String(value || '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
}

async function login(page, events) {
  await page.goto(`${BASE_URL}/admin/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.locator('input[name="username"], input#username, input[type="text"]').first().fill(USERNAME);
  await page.locator('input[name="password"], input#password, input[type="password"]').first().fill(PASSWORD);
  const buttons = page.getByRole('button');
  await buttons.first().click();
  await page.waitForLoadState('domcontentloaded', { timeout: 60000 }).catch(() => {});

  const roleButtons = page.getByRole('button');
  const roleButtonCount = await roleButtons.count().catch(() => 0);
  if (roleButtonCount > 0 && !page.url().includes('/dashboard')) {
    await roleButtons.first().click().catch(() => {});
    await page.waitForLoadState('domcontentloaded', { timeout: 60000 }).catch(() => {});
  }

  events.push({
    type: 'login',
    url: page.url(),
    ok: page.url().includes('/dashboard') || page.url().includes('/mobile/home'),
  });
}

async function auditPage(page, target, viewportName, events) {
  const url = `${BASE_URL}${target.path}`;
  const started = Date.now();
  const record = {
    name: `${viewportName}-${target.name}`,
    url,
    status: 'unknown',
    durationMs: 0,
    title: '',
    consoleErrors: 0,
    pageErrors: 0,
    failedRequests: 0,
    notes: [],
  };

  try {
    const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    record.status = response ? String(response.status()) : 'no response';
    record.title = await page.title().catch(() => '');
    await page.waitForTimeout(900);
    const text = await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
    if (!text.trim()) record.notes.push('Blank or unreadable body');
    if (/traceback|internal server error|undefined|null reference/i.test(text)) record.notes.push('Potential debug/error text visible');
    try {
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, `${record.name}.png`),
        fullPage: true,
        timeout: 30000,
      });
    } catch (screenshotError) {
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, `${record.name}-viewport.png`),
        fullPage: false,
        timeout: 30000,
      });
      record.notes.push(`Full-page screenshot exceeded browser limit; viewport screenshot saved instead.`);
    }
  } catch (error) {
    record.status = 'failed';
    record.notes.push(error.message);
  } finally {
    record.durationMs = Date.now() - started;
    events.push(record);
  }
}

function writeReports(events) {
  const rows = events.map((event) => (
    `| ${markdownEscape(event.name || event.type)} | ${markdownEscape(event.status || (event.ok ? 'ok' : 'check'))} | ${markdownEscape(event.url)} | ${event.durationMs || ''} | ${markdownEscape((event.notes || []).join('; '))} |`
  ));
  const failures = events.filter((event) => {
    const status = String(event.status || '').toLowerCase();
    const notes = event.notes || [];
    const warningOnly = notes.length > 0 && notes.every((note) => String(note).includes('viewport screenshot saved'));
    return status === 'failed' || status.startsWith('4') || status.startsWith('5') || (notes.length && !warningOnly);
  });

  const audit = [
    '# MCPD Site Audit',
    '',
    `Base URL: ${BASE_URL}`,
    `Generated: ${new Date().toISOString()}`,
    '',
    '| Page | Status | URL | Duration ms | Notes |',
    '| --- | --- | --- | ---: | --- |',
    ...rows,
    '',
    `Screenshots: ${SCREENSHOT_DIR}`,
    '',
  ].join('\n');

  const fixPlan = [
    '# MCPD Fix Plan',
    '',
    failures.length ? '## Items Requiring Review' : '## No Blocking Items Captured',
    '',
    ...(failures.length ? failures.map((event, index) => (
      `${index + 1}. ${event.name || event.type}: ${String(event.status || 'check')} - ${(event.notes || ['Review screenshot and console logs.']).join('; ')}`
    )) : ['No blocking audit items were captured by this run. Continue manual workflow verification for form accuracy and field mapping.']),
    '',
    '## Required Manual Verification',
    '',
    '1. Confirm PDF form field placement against official originals.',
    '2. Confirm live ID scanning on HTTPS phone access.',
    '3. Confirm packet print/download/email with real incident packet data.',
  ].join('\n');

  fs.writeFileSync(path.join(RESULTS_DIR, 'MCPD_SITE_AUDIT.md'), audit);
  fs.writeFileSync(path.join(RESULTS_DIR, 'MCPD_FIX_PLAN.md'), fixPlan);
}

test('full MCPD desktop and mobile audit', async ({ browser }) => {
  ensureDirs();
  const events = [];

  for (const viewport of [
    { name: 'desktop', options: { viewport: { width: 1440, height: 950 } } },
    {
      name: 'iphone',
      options: {
        viewport: { width: 390, height: 844 },
        deviceScaleFactor: 3,
        hasTouch: true,
        userAgent: devices['iPhone 13'].userAgent,
      },
    },
  ]) {
    const context = await browser.newContext({
      ...viewport.options,
      ignoreHTTPSErrors: true,
    });
    const page = await context.newPage();
    page.on('console', (message) => {
      if (message.type() === 'error') {
        events.push({ type: 'console-error', url: page.url(), status: 'console', notes: [message.text()] });
      }
    });
    page.on('pageerror', (error) => {
      events.push({ type: 'page-error', url: page.url(), status: 'pageerror', notes: [error.message] });
    });
    page.on('requestfailed', (request) => {
      events.push({ type: 'request-failed', url: request.url(), status: 'requestfailed', notes: [request.failure()?.errorText || 'failed request'] });
    });

    await login(page, events);
    for (const target of pagesToAudit) {
      if (target.mobile && viewport.name !== 'iphone') continue;
      await auditPage(page, target, viewport.name, events);
    }
    await context.close();
  }

  writeReports(events);
});
