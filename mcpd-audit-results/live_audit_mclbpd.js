const fs = require('fs');
const path = require('path');
const { chromium, devices } = require('playwright');

const BASE_URL = process.env.MCPD_AUDIT_URL || 'https://mclbpd.com';
const USERNAME = process.env.MCPD_AUDIT_USERNAME || process.env.ADMIN_USERNAME || '';
const PASSWORD = process.env.MCPD_AUDIT_PASSWORD || process.env.ADMIN_PASSWORD || '';
const outDir = path.join(process.cwd(), 'mcpd-audit-results');
const screenshotDir = path.join(outDir, 'screenshots');
fs.mkdirSync(screenshotDir, { recursive: true });

const startedAt = new Date();
const results = {
  baseUrl: BASE_URL,
  startedAt: startedAt.toISOString(),
  authenticated: false,
  authSkipped: !USERNAME || !PASSWORD,
  pages: [],
  consoleErrors: [],
  failedRequests: [],
  notes: [],
};

function cleanName(name) {
  return name.replace(/[^a-z0-9_-]+/gi, '-').replace(/^-|-$/g, '').toLowerCase();
}

function isNoiseFailure(url) {
  return url.includes('/cdn-cgi/rum') || url.includes('cloudflareinsights.com');
}

async function snapshotPage(page, label) {
  const file = path.join(screenshotDir, `${cleanName(label)}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function measure(page, route, label) {
  const url = route.startsWith('http') ? route : `${BASE_URL}${route}`;
  const started = Date.now();
  const entry = {
    label,
    route,
    status: null,
    finalUrl: null,
    ms: null,
    title: '',
    bodyHints: [],
    screenshot: null,
    error: null,
  };
  try {
    const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForLoadState('load', { timeout: 15000 }).catch(() => {});
    entry.status = response ? response.status() : null;
    entry.finalUrl = page.url();
    entry.ms = Date.now() - started;
    entry.title = await page.title().catch(() => '');
    const text = await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
    for (const hint of ['Page Not Found', 'Internal Server Error', 'Something went wrong', 'Traceback', 'Debug', 'raw JSON', 'Watch Commander', 'Forms', 'Law Lookup', 'Reports']) {
      if (text.includes(hint)) entry.bodyHints.push(hint);
    }
    entry.screenshot = await snapshotPage(page, label);
  } catch (err) {
    entry.ms = Date.now() - started;
    entry.error = String(err.message || err).slice(0, 500);
  }
  results.pages.push(entry);
  return entry;
}

async function login(page) {
  await measure(page, '/login', 'desktop-login');
  if (!USERNAME || !PASSWORD) return false;
  const userInput = page.locator('input[name="username"], input[type="text"], input[type="email"]').first();
  const passInput = page.locator('input[name="password"], input[type="password"]').first();
  if (!(await userInput.count()) || !(await passInput.count())) {
    results.notes.push('Login form fields were not found.');
    return false;
  }
  await userInput.fill(USERNAME);
  await passInput.fill(PASSWORD);
  const submit = page.locator('button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign In")').first();
  if (await submit.count()) {
    await Promise.all([
      page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {}),
      submit.click(),
    ]);
  } else {
    await passInput.press('Enter');
    await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
  }
  await page.waitForLoadState('load', { timeout: 15000 }).catch(() => {});
  const body = await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
  const ok = !page.url().includes('/login') && !/invalid credentials|invalid cadentials|login failed/i.test(body);
  results.authenticated = ok;
  if (!ok) {
    results.notes.push(`Login did not complete. Final URL: ${page.url()}`);
    await snapshotPage(page, 'desktop-login-after-submit');
  }
  return ok;
}

async function exerciseLawLookup(page) {
  const entry = await measure(page, '/legal/search', 'desktop-law-lookup');
  if (entry.error || entry.finalUrl?.includes('/login')) return;
  const statement = 'A person was seen defecating on the sidewalk in public near the barracks while other people were present.';
  const textareas = page.locator('textarea');
  const inputs = page.locator('input[type="search"], input[name="q"], input[name="query"], input[type="text"]');
  if (await textareas.count()) {
    await textareas.first().fill(statement);
  } else if (await inputs.count()) {
    await inputs.first().fill(statement);
  } else {
    results.notes.push('Law Lookup input field was not found.');
    return;
  }
  const searchButton = page.locator('button:has-text("Search"), input[type="submit"]').first();
  const started = Date.now();
  if (await searchButton.count()) {
    await Promise.all([
      page.waitForLoadState('domcontentloaded', { timeout: 30000 }).catch(() => {}),
      searchButton.click(),
    ]);
  }
  await page.waitForLoadState('load', { timeout: 30000 }).catch(() => {});
  const body = await page.locator('body').innerText({ timeout: 10000 }).catch(() => '');
  results.pages.push({
    label: 'Law Lookup search: public defecation statement',
    route: '/legal/search',
    status: null,
    finalUrl: page.url(),
    ms: Date.now() - started,
    title: await page.title().catch(() => ''),
    bodyHints: ['resultText=' + body.slice(0, 600).replace(/\s+/g, ' ')],
    screenshot: await snapshotPage(page, 'desktop-law-lookup-results'),
    error: null,
  });
}

async function exerciseAssistant(page) {
  const status = await page.request.get(`${BASE_URL}/api/assistant/status`, { timeout: 20000 }).catch(err => ({ error: err }));
  if (status.error) {
    results.pages.push({ label: 'Assistant status API', route: '/api/assistant/status', error: String(status.error), ms: null });
    return;
  }
  let payload = '';
  try { payload = await status.text(); } catch {}
  results.pages.push({
    label: 'Assistant status API',
    route: '/api/assistant/status',
    status: status.status(),
    finalUrl: `${BASE_URL}/api/assistant/status`,
    ms: null,
    title: '',
    bodyHints: [payload.slice(0, 500).replace(/sk-[A-Za-z0-9_-]+/g, '[redacted-key]')],
    screenshot: null,
    error: null,
  });
}

async function auditContext(browser, name, contextOptions, routes) {
  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();
  page.on('console', msg => {
    if (['error', 'warning'].includes(msg.type())) {
      results.consoleErrors.push({ context: name, type: msg.type(), text: msg.text().slice(0, 500), url: page.url() });
    }
  });
  page.on('requestfailed', req => {
    if (!isNoiseFailure(req.url())) {
      results.failedRequests.push({ context: name, url: req.url(), failure: req.failure()?.errorText || '' });
    }
  });
  const authed = await login(page);
  if (!authed && (USERNAME || PASSWORD)) {
    results.notes.push(`${name}: authenticated checks blocked by login failure.`);
  }
  if (!authed && !USERNAME && !PASSWORD) {
    results.notes.push(`${name}: authenticated checks skipped because no audit credentials were available in environment.`);
  }
  for (const [route, label] of routes) {
    await measure(page, route, `${name}-${label}`);
  }
  await exerciseLawLookup(page);
  await exerciseAssistant(page);
  await context.close();
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const desktopRoutes = [
    ['/dashboard', 'dashboard'],
    ['/reports', 'reports'],
    ['/forms', 'forms'],
    ['/watch-commander', 'watch-commander'],
    ['/mobile', 'mobile-home-from-desktop'],
    ['/mobile/more', 'mobile-more-from-desktop'],
  ];
  const mobileRoutes = [
    ['/mobile', 'mobile-home'],
    ['/mobile/more', 'mobile-more'],
    ['/reports', 'reports-mobile'],
    ['/forms', 'forms-mobile'],
    ['/legal/search', 'law-lookup-mobile'],
  ];
  await auditContext(browser, 'desktop', { viewport: { width: 1440, height: 1000 } }, desktopRoutes);
  await auditContext(browser, 'mobile', { ...devices['iPhone 14'], viewport: { width: 390, height: 844 } }, mobileRoutes);
  await browser.close();

  results.finishedAt = new Date().toISOString();
  const lines = [];
  lines.push('# MCPD Live Audit - mclbpd.com');
  lines.push('');
  lines.push(`Started: ${results.startedAt}`);
  lines.push(`Finished: ${results.finishedAt}`);
  lines.push(`Base URL: ${results.baseUrl}`);
  lines.push(`Authenticated: ${results.authenticated ? 'yes' : 'no'}`);
  if (results.authSkipped) lines.push('Auth note: credentials were not available in this terminal environment.');
  lines.push('');
  lines.push('## Page Results');
  for (const p of results.pages) {
    lines.push(`- ${p.label}: status=${p.status ?? 'n/a'}, ms=${p.ms ?? 'n/a'}, final=${p.finalUrl ?? 'n/a'}${p.error ? `, error=${p.error}` : ''}`);
    if (p.bodyHints?.length) lines.push(`  Hints: ${p.bodyHints.join(' | ')}`);
    if (p.screenshot) lines.push(`  Screenshot: ${p.screenshot}`);
  }
  lines.push('');
  lines.push('## Console Errors / Warnings');
  if (!results.consoleErrors.length) lines.push('- None captured.');
  for (const e of results.consoleErrors) lines.push(`- [${e.context}] ${e.type}: ${e.text} (${e.url})`);
  lines.push('');
  lines.push('## Failed Requests');
  if (!results.failedRequests.length) lines.push('- None captured outside Cloudflare RUM noise.');
  for (const f of results.failedRequests) lines.push(`- [${f.context}] ${f.url}: ${f.failure}`);
  lines.push('');
  lines.push('## Notes');
  if (!results.notes.length) lines.push('- None.');
  for (const n of results.notes) lines.push(`- ${n}`);

  fs.writeFileSync(path.join(outDir, 'MCPD_LIVE_AUDIT_MCLBPD.md'), lines.join('\n'));
  fs.writeFileSync(path.join(outDir, 'MCPD_LIVE_AUDIT_MCLBPD.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify({ ok: true, pages: results.pages.length, authenticated: results.authenticated, md: path.join(outDir, 'MCPD_LIVE_AUDIT_MCLBPD.md') }, null, 2));
})().catch(err => {
  console.error(err);
  process.exit(1);
});
