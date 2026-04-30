async function getReportId() {
  const url = new URL(window.location.href);
  const queryId = url.searchParams.get('report_id');
  if (queryId) {
    localStorage.setItem('cleo_report_id', queryId);
    return queryId;
  }
  const stored = localStorage.getItem('cleo_report_id');
  if (stored) return stored;
  try {
    const res = await fetch('/api/cleo-reports');
    if (!res.ok) return null;
    const json = await res.json();
    const latest = (json.reports || [])[0];
    if (latest && latest.id) {
      const id = String(latest.id);
      localStorage.setItem('cleo_report_id', id);
      return id;
    }
  } catch (_) {
    return null;
  }
  return null;
}

let cleoDirty = false;

function serializeForm() {
  const fields = Array.from(document.querySelectorAll('input, textarea, select'));
  return fields.map((el, idx) => {
    const row = el.closest('.ia-row, .person-row, .involved-row, .off-row, .prop-row, .org-row, .nar-row, .veh-row, .v1408-row, tr, .form-group, .row');
    const labelEl = row ? row.querySelector('label, .label, .form-label, th') : null;
    const label = ((labelEl && labelEl.textContent) || el.getAttribute('aria-label') || el.name || el.id || `Field ${idx + 1}`).trim();
    const type = (el.type || '').toLowerCase();
    if (type === 'checkbox' || type === 'radio') {
      return { idx, label, value: el.value, checked: !!el.checked };
    }
    return { idx, label, value: el.value };
  });
}

function applyForm(data) {
  const fields = Array.from(document.querySelectorAll('input, textarea, select'));
  data.forEach(item => {
    const el = fields[item.idx];
    if (!el) return;
    const type = (el.type || '').toLowerCase();
    if (type === 'checkbox' || type === 'radio') {
      el.checked = !!item.checked;
      return;
    }
    el.value = item.value || '';
  });
}

function clearFormValues() {
  const fields = Array.from(document.querySelectorAll('input, textarea, select'));
  fields.forEach((el) => {
    const type = (el.type || '').toLowerCase();
    if (type === 'radio' || type === 'checkbox') {
      el.checked = false;
      return;
    }
    if (el.tagName === 'SELECT') {
      el.selectedIndex = 0;
      return;
    }
    el.value = '';
  });
}

function markDirty() {
  cleoDirty = true;
}

async function saveReport(pageKey, notify = true) {
  const reportId = await getReportId();
  if (!reportId) {
    alert('No report selected. Use Reports to load or New Report to create.');
    return;
  }
  const res = await fetch(`/api/cleo-reports/${reportId}/page/${pageKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: serializeForm() })
  });
  if (!res.ok) {
    let message = 'Save failed.';
    try {
      const json = await res.json();
      message = json.error || message;
    } catch (_) {}
    alert(message);
    return;
  }
  if (res.ok) cleoDirty = false;
  // Legacy flow avoids modal confirmations on every save.
  if (res.ok && notify) return;
}

async function loadReport(pageKey) {
  const reportId = await getReportId();
  if (!reportId) return;
  const res = await fetch(`/api/cleo-reports/${reportId}/page/${pageKey}`);
  if (!res.ok) return;
  const json = await res.json();
  if (json && json.editable === false) {
    const fields = Array.from(document.querySelectorAll('input, textarea, select'));
    fields.forEach((el) => {
      if (el.tagName === 'SELECT' || el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
        el.setAttribute('disabled', 'disabled');
      }
    });
    document.body.classList.add('cleo-readonly');
    alert('This mock report is read-only because it has already been submitted. Review it from the summary page or wait for it to be returned for corrections.');
  }
  const saved = Array.isArray(json.data) ? json.data : [];
  if (!saved.length) {
    clearFormValues();
    return;
  }
  applyForm(saved);
}

async function newReport() {
  const res = await fetch('/api/cleo-reports', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
  const json = await res.json();
  localStorage.setItem('cleo_report_id', json.id);
  window.top.location.href = `/static/cleo/incident-admin.html?report_id=${json.id}`;
}

async function openSummary() {
  const reportId = await getReportId();
  if (!reportId) {
    alert('No report selected. Use Reports to load or New Report to create.');
    return;
  }
  window.top.location.href = `/cleo/report/${reportId}`;
}

function openReports() {
  window.top.location.href = '/cleo/reports';
}

async function withReportId(path) {
  const reportId = await getReportId();
  if (!reportId) return path;
  const sep = path.includes('?') ? '&' : '?';
  return `${path}${sep}report_id=${reportId}`;
}

async function openCleoPage(pagePath) {
  const full = pagePath.startsWith('/static/cleo/') ? pagePath : `/static/cleo/${pagePath}`;
  window.location.href = await withReportId(full);
}

async function saveAndReturnAdmin() {
  const pageKey = document.body.getAttribute('data-page-key');
  if (pageKey) {
    await saveReport(pageKey, false);
  }
  cleoDirty = false;
  window.location.href = await withReportId('/static/cleo/admin-summary.html');
}

function removeLegacyDropdownNav() {
  document.querySelectorAll('.nav').forEach((n) => n.remove());
}

function removeModernHeaderBar() {
  const badge = document.getElementById('reportBadge');
  if (!badge) return;
  const modernBar = badge.closest('.cleo-headerbar');
  if (modernBar) modernBar.remove();
}

function ensureLegacyToolbarShape() {
  let bars = Array.from(document.querySelectorAll('.cleo-headerbar'));
  if (!bars.length) {
    const bar = document.createElement('div');
    bar.className = 'cleo-headerbar';
    bar.innerHTML = `
      <div class="CLEOC-toolbar"><div class="CLEOC-icon"></div><div class="CLEOC-icon"></div><div class="CLEOC-icon"></div></div>
      <div><strong>MCLB ALBANY</strong> &nbsp; Watch / Platoon Commander</div>
      <div class="CLEOC-toolbar">
        <div class="CLEOC-icon"></div><div class="CLEOC-icon"></div><div class="CLEOC-icon"></div><div class="CLEOC-icon"></div>
        <div class="CLEOC-icon"></div><div class="CLEOC-icon"></div><div class="CLEOC-icon"></div><div class="CLEOC-icon"></div>
        <div class="CLEOC-icon"></div><div class="CLEOC-icon"></div><div class="CLEOC-icon"></div><div class="CLEOC-icon"></div>
      </div>
    `;
    const wrap = document.querySelector('.wrap') || document.body;
    wrap.insertBefore(bar, wrap.firstChild);
    bars = Array.from(document.querySelectorAll('.cleo-headerbar'));
  }
  const bar = bars[0];
  let toolbars = Array.from(bar.querySelectorAll('.CLEOC-toolbar, .cleo-toolbar'));
  if (toolbars.length < 2) return;
  const left = toolbars[0];
  const right = toolbars[1];

  while (left.children.length < 3) {
    const icon = document.createElement('div');
    icon.className = 'CLEOC-icon';
    left.appendChild(icon);
  }
  while (right.children.length < 12) {
    const icon = document.createElement('div');
    icon.className = 'CLEOC-icon';
    right.appendChild(icon);
  }
}

function legacyMenuLinksHtml() {
  return `
    <a href="#" onclick="cleoReports(); return false;">Search Incidents</a>
    <a href="#" onclick="cleoReports(); return false;">My Cases</a>
    <a href="#" onclick="cleoOpen('incident-admin.html'); return false;">Military Police Reporting</a>
    <a href="#" onclick="cleoOpen('ta-main.html'); return false;">Accident Investigation Reporting</a>
    <a href="#" onclick="cleoOpen('violation-1408.html'); return false;">Traffic Enforcement</a>
    <a href="#" onclick="cleoOpen('persons.html'); return false;">Registration</a>
    <div class="legacy-menu-item">
      <a href="#" onclick="return false;">Journal</a>
      <div class="legacy-submenu">
        <a href="#" onclick="cleoOpen('journal-report.html'); return false;">Journal Report</a>
        <a href="#" onclick="cleoOpen('desk-journal.html'); return false;">Summary Journal Entries</a>
      </div>
    </div>
    <a href="#" onclick="cleoOpen('narrative.html'); return false;">Communications Log</a>
    <a href="#" onclick="cleoReports(); return false;">Reports</a>
    <a href="#" onclick="cleoOpen('organization.html'); return false;">Background Records Check</a>
    <a href="#" onclick="cleoOpen('property.html'); return false;">Field Interviews</a>
    <a href="#" onclick="cleoOpen('offenses.html'); return false;">Protective Order</a>
  `;
}

function wireLegacyMenuStatus(container, statusEl) {
  if (!container || !statusEl) return;
  const allLinks = Array.from(container.querySelectorAll('a'));
  allLinks.forEach((a) => {
    a.addEventListener('mouseenter', () => {
      statusEl.textContent = a.href || '';
    });
    a.addEventListener('mouseleave', () => {
      statusEl.textContent = '';
    });
  });
}

function toggleLegacyMenuWindow() {
  const existing = document.getElementById('legacyMenuWindow');
  if (existing) {
    existing.remove();
    return;
  }
  const w = document.createElement('div');
  w.id = 'legacyMenuWindow';
  w.className = 'legacy-menu-window';
  w.innerHTML = `
    <div class="legacy-menu-header">
      <span>Menu Selection - Profile 1 - Microsoft Edge</span>
      <button class="legacy-popup-btn dark" type="button" id="legacyMenuCloseBtn">x</button>
    </div>
    <div class="legacy-menu-address">
      <span class="legacy-menu-lock">&#128274;</span>
      <input type="text" readonly value="https://cleoc.ncis.navy.mil/pls/cleoc/CLEOC_PORTAL.CLEOC_ME..." />
    </div>
    <div class="legacy-menu-body">
      <div class="legacy-popup-menu">${legacyMenuLinksHtml()}</div>
    </div>
    <div class="legacy-menu-status" id="legacyMenuStatusBar"></div>
  `;
  document.body.appendChild(w);
  document.getElementById('legacyMenuCloseBtn').addEventListener('click', () => w.remove());
  wireLegacyMenuStatus(w.querySelector('.legacy-popup-menu'), document.getElementById('legacyMenuStatusBar'));
}

function toggleLegacyNavigator() {
  // Kept for compatibility; no floating menu in video-match mode.
}

function optionsForMenuKey(menuKey) {
  const base = [''];
  const key = (menuKey || '').toLowerCase();
  if (key === 'type-incident') {
    return base.concat([
      'LE Response - Non Criminal',
      'LE Response - Criminal',
      'Traffic Accident Incident Reporting',
      'Traffic Enforcement',
      'Military Police Reporting',
      'Accident Investigation Reporting'
    ]);
  }
  if (key === 'incident-received-via') {
    return base.concat(['By Telephone', 'In Person', 'Radio', 'Email', 'Other']);
  }
  if (key === 'incident-included-journal') {
    return base.concat(['No', 'Yes', 'Restricted']);
  }
  if (key === 'city-limits-indicator') {
    return base.concat(['', 'City Limits', 'Center']);
  }
  if (key === 'case-category') {
    return base.concat([
      '10X - Other',
      '40 - Standards of Conduct',
      '4P - Product Substitution',
      '4Q - Embezzlement',
      '4T - Unauthorized Services - GOVT',
      '4U - TRICARE Claims Violation',
      '4W - Workers Compensation',
      '4X - Special Inquiry',
      '4Y - Integrated Support',
      '5A - Special Inquiry',
      '5C - Port Visit Support',
      '5G - Threat Assessment - General',
      '5H - Exceeding Authorized Access',
      '5I - Intrusion',
      '5J - Denial of Service',
      '5K - Malicious Code',
      '5M - OPSEC Support',
      '5P - PACE',
      '5T - Terrorism',
      '5V - Personal Security Vulnerability Assessment',
      '5X - Special Inquiry',
      '5Y - Suspicious Incident'
    ]);
  }
  if (key === 'project-identifier') {
    return base.concat(['MA', 'MC', 'MB', 'NA', 'OT']);
  }
  if (key === 'organization-code') {
    return base.concat([
      '29AB - MCLB Albany',
      '21HQ - HQMC (PS)',
      '22DC - HQMC Henderson Hall',
      '22QV - RTI NCR MCB Quantico',
      '23QV - MCB Quantico',
      '24LE - MCB Camp Lejeune',
      '25PE - MCB Camp Pendleton',
      '26TN - MCAGCC Twenty-Nine Palms',
      '27PI - MCRD Parris Island',
      '28MD - MCRD San Diego',
      '30BD - MCLB Barstow',
      '31CP - MCAS Cherry Point'
    ]);
  }
  if (key === 'yes-no') return base.concat(['Yes', 'No']);
  if (key === 'result') return base.concat(['', 'Accepted', 'Declined']);
  if (key === 'reason-declination') return base.concat(['', 'Outside Jurisdiction', 'Insufficient Information', 'Other']);
  if (key === 'remove-yes-no') return base.concat(['No', 'Yes']);
  return base;
}

function buildSelectOptions(labelText, menuKey) {
  const keyed = optionsForMenuKey(menuKey);
  if (keyed.length > 1) return keyed;
  const base = [''];
  const label = (labelText || '').toLowerCase();
  if (label.includes('case category code')) {
    return optionsForMenuKey('case-category');
  }
  if (label.includes('type of incident')) {
    return base.concat(['LE Response - Non Criminal', 'LE Response - Criminal', 'Traffic Accident']);
  }
  if (label.includes('type of accident')) {
    return optionsForMenuKey('type-incident');
  }
  if (label.includes('incident received via')) {
    return base.concat(['By Telephone', 'In Person', 'Radio', 'Email', 'Other']);
  }
  if (label.includes('project identifier code')) {
    return base.concat(['MA', 'MC', 'MB', 'NA', 'OT']);
  }
  if (label.includes('organization identification code')) {
    return optionsForMenuKey('organization-code');
  }
  if (label.includes('is date and time of incident known')) {
    return base.concat(['Yes', 'No']);
  }
  if (label.includes('result')) {
    return base.concat(['', 'Accepted', 'Declined']);
  }
  if (label.includes('reason for declination')) {
    return base.concat(['', 'Outside Jurisdiction', 'Insufficient Information', 'Other']);
  }
  if (label.includes('incident included in journal')) {
    return optionsForMenuKey('incident-included-journal');
  }
  if (label.includes('outside city limits indicate')) {
    return optionsForMenuKey('city-limits-indicator');
  }
  if (label.includes('remove')) {
    return base.concat(['No', 'Yes']);
  }
  if (label.includes('person role')) {
    return base.concat([
      'Additional Officer',
      'Arrestee',
      'Complainant',
      'Reporting Official',
      'Sponsor',
      'Suspect',
      'Victim',
      'Witness'
    ]);
  }
  if (label.includes('deceased')) {
    return base.concat(['No', 'Yes']);
  }
  if (label.includes('person id type')) {
    return base.concat(['SSN', 'Alien Reg #', 'Driver License', 'Passport', 'DoD ID']);
  }
  if (label.includes('security clearance')) {
    return base.concat(['Secret Clearance', 'Top Secret', 'Confidential', 'None']);
  }
  if (label.includes('country')) {
    return base.concat(['UNITED STATES', 'CANADA', 'MEXICO', 'OTHER']);
  }
  if (label.includes('state/territory')) {
    return base.concat(['GEORGIA', 'ALABAMA', 'FLORIDA', 'SOUTH CAROLINA', 'OTHER']);
  }
  if (label.includes('civilian status')) {
    return base.concat(['Employee', 'Contractor', 'Visitor', 'Other']);
  }
  if (label.includes('dependent status')) {
    return base.concat(['No', 'Yes']);
  }
  if (label.includes('hair color')) {
    return base.concat(['Black', 'Brown', 'Blonde', 'Gray', 'Red', 'Other']);
  }
  if (label.includes('eye color')) {
    return base.concat(['Brown', 'Blue', 'Green', 'Hazel', 'Gray', 'Other']);
  }
  if (label.includes('race')) {
    return base.concat(['Black or African American', 'White', 'Asian', 'American Indian', 'Pacific Islander', 'Other']);
  }
  if (label.includes('ethnicity')) {
    return base.concat(['Not Hispanic or Latino', 'Hispanic or Latino']);
  }
  if (label.includes('yes') || label.includes('status') || label.includes('retired') || label.includes('deceased')) {
    return base.concat(['Yes', 'No']);
  }
  if (label.includes('lighting')) {
    return base.concat(['Dark (Lighted)', 'Dark (Not Lighted)', 'Dawn', 'Daylight', 'Dusk']);
  }
  if (label.includes('weather')) {
    return base.concat(['Clear', 'Cloudy', 'Foggy', 'Rain', 'Snow', 'Ice', 'Other']);
  }
  if (label.includes('case category')) {
    return base.concat([
      '10X - Other',
      '40 - Standards of Conduct',
      '4P - Product Substitution',
      '4Q - Embezzlement',
      '4T - Unauthorized Services - GOVT',
      '4U - TRICARE Claims Violation',
      '4W - Workers Compensation',
      '5A - Special Inquiry',
      '5C - Port Visit Support',
      '5G - Threat Assessment - General',
      '5H - Exceeding Authorized Access',
      '5I - Intrusion',
      '5J - Denial of Service',
      '5K - Malicious Code',
      '5M - OPSEC Support',
      '5P - PACE',
      '5T - Terrorism',
      '5V - Personal Security Vulnerability Assessment',
      '5X - Special Inquiry',
      '5Y - Suspicious Incident'
    ]);
  }
  if (label.includes('organization identification code')) {
    return base.concat([
      '29AB - MCLB Albany',
      '21HQ - HQMC (PS)',
      '22DC - HQMC Henderson Hall',
      '22QV - RTI NCR MCB Quantico',
      '23QV - MCB Quantico',
      '24LE - MCB Camp Lejeune',
      '25PE - MCB Camp Pendleton',
      '26TN - MCAGCC Twenty-Nine Palms',
      '27PI - MCRD Parris Island',
      '28MD - MCRD San Diego',
      '30BD - MCLB Barstow',
      '31CP - MCAS Cherry Point',
      '32ET - MCAS El Toro',
      '33LE - RTI East MCB Camp Lejeune',
      '34EL - MCAS New River',
      '35TU - MCAS Tustin',
      '36BE - MCAS Beaufort',
      '36VU - MCAS Yuma',
      '37IW - MCAS Iwakuni'
    ]);
  }
  if (label.includes('color')) {
    return base.concat([
      'Black','Blue','Brown','Gray','Green','Green, Light','Ivory','Lavender (purple)','Magenta',
      'Maroon','Mauve','Multicolored','Orange','Pink','Purple','Red','Silver','Stainless Steel',
      'Tan','Taupe (brown)','Teal (green)','Turquoise (blue)','Unknown','White','Yellow'
    ]);
  }
  return base;
}

function inferMenuKeyFromLabel(labelText) {
  const label = (labelText || '').toLowerCase();
  if (label.includes('case category code')) return 'case-category';
  if (label.includes('type of incident')) return 'type-incident';
  if (label.includes('type of accident')) return 'type-incident';
  if (label.includes('incident received via') || label.includes('incident received')) return 'incident-received-via';
  if (label.includes('project identifier code')) return 'project-identifier';
  if (label.includes('organization identification code')) return 'organization-code';
  if (label.includes('is date and time of incident known')) return 'yes-no';
  if (label.includes('ncis notified')) return 'yes-no';
  if (label.includes('incident included in journal')) return 'incident-included-journal';
  if (label.includes('outside city limits indicate')) return 'city-limits-indicator';
  if (label.includes('remove')) return 'remove-yes-no';
  if (label.includes('result')) return 'result';
  if (label.includes('reason for declination')) return 'reason-declination';
  return '';
}

function stripGenericOptions() {
  const selects = Array.from(document.querySelectorAll('select'));
  selects.forEach((select) => {
    const opts = Array.from(select.options);
    opts.forEach((opt) => {
      if (/^Option\s+\d+$/i.test((opt.textContent || '').trim()) || /^Option\s+\d+$/i.test((opt.value || '').trim())) {
        opt.remove();
      }
    });
    if (/^Option\s+\d+$/i.test((select.value || '').trim())) {
      select.value = '';
      if (select.options.length) select.selectedIndex = 0;
    }
  });
}

function convertLegacySelectInputs() {
  const candidates = Array.from(document.querySelectorAll('input.listbox, input.ia-select, input.person-select, input.involved-select, input.org-select, input.off-select, input.veh-select, input.v1408-select, input.prop-select, input.nar-select'));
  candidates.forEach((input) => {
    if (input.dataset.converted === '1') return;
    const select = document.createElement('select');
    select.className = input.className;
    select.value = input.value || '';
    const labelNode = input.closest('.ia-row, .person-row, .involved-row, .off-row, .prop-row, .org-row, .nar-row, .veh-row, .v1408-row');
    const labelText = labelNode ? labelNode.textContent : '';
    const menuKey = input.dataset.menu || inferMenuKeyFromLabel(labelText);
    if (menuKey) select.dataset.menu = menuKey;
    const options = buildSelectOptions(labelText, menuKey);
    options.forEach((optText) => {
      const opt = document.createElement('option');
      opt.value = optText;
      opt.textContent = optText;
      select.appendChild(opt);
    });
    if (input.value && !options.includes(input.value)) {
      const custom = document.createElement('option');
      custom.value = input.value;
      custom.textContent = input.value;
      select.appendChild(custom);
      select.value = input.value;
    }
    input.replaceWith(select);
  });
}

function populateEmptySelects() {
  const selects = Array.from(document.querySelectorAll('select'));
  selects.forEach((select) => {
    if (select.id === 'cleoNav') return;
    const nonEmptyCount = Array.from(select.options)
      .filter((o) => ((o.value || '').trim().length > 0)).length;
    if (nonEmptyCount > 1) return;
    const labelNode = select.closest('.ia-row, .person-row, .involved-row, .off-row, .prop-row, .org-row, .nar-row, .veh-row, .v1408-row, .legacy-grid, .legacy-section, .legacy-card, tr');
    const labelText = labelNode ? labelNode.textContent : '';
    const options = buildSelectOptions(labelText, select.dataset.menu || '');
    if (options.length <= 1) return;
    const currentValue = select.value || '';
    select.innerHTML = '';
    options.forEach((optText) => {
      const opt = document.createElement('option');
      opt.value = optText;
      opt.textContent = optText;
      select.appendChild(opt);
    });
    if (currentValue && options.includes(currentValue)) {
      select.value = currentValue;
    } else if (currentValue) {
      const custom = document.createElement('option');
      custom.value = currentValue;
      custom.textContent = currentValue;
      select.appendChild(custom);
      select.value = currentValue;
    } else {
      select.selectedIndex = 0;
    }
  });
}

function enforceMenuKeySelects() {
  const keyedSelects = Array.from(document.querySelectorAll('select[data-menu]'));
  keyedSelects.forEach((select) => {
    const menuKey = select.dataset.menu || '';
    const options = optionsForMenuKey(menuKey);
    if (options.length <= 1) return;
    const currentValue = select.value || '';
    select.innerHTML = '';
    options.forEach((optText) => {
      const opt = document.createElement('option');
      opt.value = optText;
      opt.textContent = optText;
      select.appendChild(opt);
    });
    if (currentValue && options.includes(currentValue)) {
      select.value = currentValue;
    } else {
      select.selectedIndex = 0;
    }
  });
}

function enhanceLegacyInputs() {
  const all = Array.from(document.querySelectorAll('input'));
  all.forEach((el) => {
    const hint = `${el.placeholder || ''} ${el.name || ''} ${el.id || ''}`.toLowerCase();
    if (hint.includes('date')) {
      el.maxLength = 8;
      el.placeholder = 'YYYYMMDD';
    }
    if (hint.includes('time')) {
      el.maxLength = 4;
      if (!el.placeholder) el.placeholder = 'HHMM';
    }
  });
}

function wireToolbarIcons() {
  const bars = Array.from(document.querySelectorAll('.cleo-headerbar'));
  if (!bars.length) return;
  const bar = bars[0];
  const toolbars = Array.from(bar.querySelectorAll('.CLEOC-toolbar, .cleo-toolbar'));
  if (toolbars.length < 2) return;
  const leftIcons = Array.from(toolbars[0].querySelectorAll('.CLEOC-icon, .cleo-icon'));
  const rightIcons = Array.from(toolbars[1].querySelectorAll('.CLEOC-icon, .cleo-icon'));

  const leftActions = [
    { title: 'Submit Form for Addition or Update', fn: () => saveAndReturnAdmin() },
    { title: 'Menu Selection', fn: () => toggleLegacyMenuWindow() },
    { title: 'Status', fn: () => {} }
  ];
  const rightActions = [
    { title: 'Home', fn: () => openCleoPage('index.html') },
    { title: 'Admin Summary', fn: () => openCleoPage('admin-summary.html') },
    { title: 'Incident Admin', fn: () => openCleoPage('incident-admin.html') },
    { title: 'TA Main', fn: () => openCleoPage('ta-main.html') },
    { title: 'TA Person', fn: () => openCleoPage('ta-person.html') },
    { title: 'Persons', fn: () => openCleoPage('persons.html') },
    { title: 'Property', fn: () => openCleoPage('property.html') },
    { title: 'Organization', fn: () => openCleoPage('organization.html') },
    { title: 'Vehicle', fn: () => openCleoPage('vehicle.html') },
    { title: 'Offenses', fn: () => openCleoPage('offenses.html') },
    { title: 'Narcotics', fn: () => openCleoPage('narcotics.html') },
    { title: 'Narrative', fn: () => openCleoPage('narrative.html') }
  ];

  function bind(icon, action) {
    icon.title = action.title;
    icon.setAttribute('role', 'button');
    icon.setAttribute('tabindex', '0');
    icon.onclick = action.fn;
    icon.onkeydown = (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        action.fn();
      }
    };
  }

  leftIcons.forEach((icon, idx) => bind(icon, leftActions[idx] || leftActions[leftActions.length - 1]));
  rightIcons.forEach((icon, idx) => bind(icon, rightActions[idx] || rightActions[rightActions.length - 1]));
}

function initLegacyHomePopup() {
  const pageKey = document.body.getAttribute('data-page-key');
  if (pageKey !== 'home') return;

  const reopenBtn = document.createElement('button');
  reopenBtn.type = 'button';
  reopenBtn.className = 'legacy-popup-reopen';
  reopenBtn.textContent = 'Open Mock Reports Window';
  document.body.appendChild(reopenBtn);

  const popup = document.createElement('div');
  popup.className = 'legacy-popup';
  popup.innerHTML = `
    <div class="legacy-popup-titlebar" id="legacyPopupDragHandle">
      <span class="legacy-popup-title">Menu Selection - Profile 1 - Microsoft Edge</span>
      <div class="legacy-popup-controls">
        <button class="legacy-popup-btn dark" type="button" id="legacyPopupMinBtn">_</button>
        <button class="legacy-popup-btn dark" type="button" id="legacyPopupCloseBtn">x</button>
      </div>
    </div>
    <div class="legacy-menu-address">
      <span class="legacy-menu-lock">&#128274;</span>
      <input type="text" readonly value="https://cleoc.ncis.navy.mil/pls/cleoc/CLEOC_PORTAL.CLEOC_ME..." />
    </div>
    <div class="legacy-popup-body">
      <div class="legacy-popup-menu">${legacyMenuLinksHtml()}</div>
    </div>
    <div class="legacy-menu-status" id="legacyPopupStatusBar"></div>
  `;
  document.body.appendChild(popup);

  const minBtn = document.getElementById('legacyPopupMinBtn');
  const closeBtn = document.getElementById('legacyPopupCloseBtn');
  const dragHandle = document.getElementById('legacyPopupDragHandle');

  minBtn.addEventListener('click', () => {
    popup.classList.toggle('minimized');
  });

  closeBtn.addEventListener('click', () => {
    popup.style.display = 'none';
    reopenBtn.classList.add('visible');
  });

  reopenBtn.addEventListener('click', () => {
    popup.style.display = 'block';
    popup.classList.remove('minimized');
    reopenBtn.classList.remove('visible');
  });
  wireLegacyMenuStatus(popup.querySelector('.legacy-popup-menu'), document.getElementById('legacyPopupStatusBar'));

  let dragging = false;
  let startX = 0;
  let startY = 0;
  let startLeft = 0;
  let startTop = 0;

  dragHandle.addEventListener('mousedown', (e) => {
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    const rect = popup.getBoundingClientRect();
    startLeft = rect.left;
    startTop = rect.top;
    document.body.style.userSelect = 'none';
  });

  window.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const nextLeft = Math.max(0, startLeft + (e.clientX - startX));
    const nextTop = Math.max(0, startTop + (e.clientY - startY));
    popup.style.left = `${nextLeft}px`;
    popup.style.top = `${nextTop}px`;
  });

  window.addEventListener('mouseup', () => {
    dragging = false;
    document.body.style.userSelect = '';
  });
}

async function hydrateAdminSummary() {
  const pageKey = document.body.getAttribute('data-page-key');
  if (pageKey !== 'admin-summary') return;
  const reportId = await getReportId();
  if (!reportId) return;
  const res = await fetch(`/api/cleo-reports/${reportId}/summary`);
  if (!res.ok) return;
  const json = await res.json();
  const caseNo = (json.report && json.report.case_control_number) ? json.report.case_control_number : '';
  const incidentType = (json.report && json.report.incident_type) ? json.report.incident_type : '';
  const caseNode = document.getElementById('adminCaseControlNumber');
  const typeNode = document.getElementById('adminIncidentType');
  if (caseNode) caseNode.textContent = caseNo;
  if (typeNode) typeNode.textContent = incidentType;
}

window.addEventListener('load', async () => {
  const pageKey = document.body.getAttribute('data-page-key');
  removeLegacyDropdownNav();
  removeModernHeaderBar();
  ensureLegacyToolbarShape();
  convertLegacySelectInputs();
  enforceMenuKeySelects();
  populateEmptySelects();
  stripGenericOptions();
  if (pageKey) await loadReport(pageKey);
  // Re-apply keyed menus after load so custom saved values are preserved when not in static lists.
  enforceMenuKeySelects();
  enhanceLegacyInputs();
  wireToolbarIcons();
  const badge = document.getElementById('reportBadge');
  if (badge) {
    const reportId = await getReportId();
    badge.textContent = reportId ? `Report #${reportId}` : 'No Report';
  }
  initLegacyHomePopup();
  await hydrateAdminSummary();
  document.addEventListener('input', markDirty, true);
  document.addEventListener('change', markDirty, true);
});

window.addEventListener('beforeunload', (e) => {
  if (!cleoDirty) return;
  e.preventDefault();
  e.returnValue = '';
});

window.cleoSave = async () => {
  const pageKey = document.body.getAttribute('data-page-key');
  if (pageKey) await saveReport(pageKey);
};
window.cleoNewReport = newReport;
window.cleoSummary = openSummary;
window.cleoReports = openReports;
window.cleoOpen = openCleoPage;
