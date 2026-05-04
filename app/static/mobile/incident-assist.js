/* MCPD Phase 7 — Incident Assist Module
 * Provides: Narrative Assistant, Smart Form Suggestions,
 *           Incident Summary Generator, Dynamic Checklists
 * Runs after incident-core.js on specific pages.
 * Never overwrites officer input — suggest only.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'mcpd.mobile.incident.state';

  function getState() {
    try { return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}'); }
    catch (e) { return {}; }
  }

  function postJSON(url, data, cb) {
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
      .then(function (r) { return r.json(); })
      .then(cb)
      .catch(function () { cb(null); });
  }

  function esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function buildCard(title, bodyHtml, startOpen) {
    return (
      '<details class="assist-card"' + (startOpen ? ' open' : '') + '>' +
      '<summary class="assist-card-header">' +
      '<span class="assist-card-title">' + esc(title) + '</span>' +
      '<span class="assist-card-chevron">&#8250;</span>' +
      '</summary>' +
      '<div class="assist-card-body">' + bodyHtml + '</div>' +
      '</details>'
    );
  }

  function severityClass(sev) {
    if (sev === 'error') return 'assist-item-error';
    if (sev === 'warn') return 'assist-item-warn';
    if (sev === 'info') return 'assist-item-info';
    return 'assist-item-info';
  }

  function renderSuggestions(suggestions, aiUsed) {
    if (!suggestions || suggestions.length === 0) {
      return '<p class="assist-ok">&#10003; Looking good — no issues detected.</p>';
    }
    var html = '';
    if (aiUsed) {
      html += '<p class="assist-ai-label">&#10022; AI-enhanced analysis</p>';
    }
    html += '<ul class="assist-list">';
    suggestions.forEach(function (s) {
      var aiTag = s.ai ? ' <span class="assist-ai-tag">AI</span>' : '';
      html += '<li class="assist-item ' + severityClass(s.severity) + '">' + esc(s.text) + aiTag + '</li>';
    });
    html += '</ul>';
    return html;
  }

  /* ── Page Detection ──────────────────────────────────────────────────────── */
  var appEl = document.querySelector('[data-mobile-incident-page]');
  if (!appEl) return;
  var pageName = appEl.dataset.mobileIncidentPage;

  if (pageName === 'narrative-review') {
    initNarrativeAssist();
    initDynamicChecklist();
  }
  if (pageName === 'selected-forms') {
    initSmartFormsAssist();
  }
  if (pageName === 'packet-review') {
    initPacketSummaryAssist();
  }

  /* ── Narrative Assistant ─────────────────────────────────────────────────── */
  function initNarrativeAssist() {
    var root = document.getElementById('narrative-assist-root');
    if (!root) return;

    root.innerHTML = buildCard(
      'Narrative Assistant',
      '<p class="assist-hint">Checks your narrative for missing elements, clarity, and required content. Does not modify your text.</p>' +
      '<button class="assist-btn" id="assist-narrative-run">Analyze Narrative</button>' +
      '<div id="assist-narrative-output" class="assist-output" style="display:none;"></div>',
      false
    );

    document.getElementById('assist-narrative-run').addEventListener('click', function () {
      var state = getState();
      var narrative = '';
      var ta = document.querySelector('[data-narrative-editor]');
      if (ta) {
        narrative = ta.value.trim();
      } else {
        narrative = typeof state.narrative === 'string' ? state.narrative.trim() : '';
      }

      if (!narrative) {
        var out = document.getElementById('assist-narrative-output');
        out.innerHTML = '<p class="assist-warn">No narrative text found. Write your narrative first, then analyze.</p>';
        out.style.display = '';
        return;
      }

      var btn = document.getElementById('assist-narrative-run');
      btn.disabled = true;
      btn.textContent = 'Analyzing…';

      postJSON('/mobile/api/narrative/suggest', { narrative: narrative, state: state }, function (data) {
        btn.disabled = false;
        btn.textContent = 'Re-analyze';
        var out = document.getElementById('assist-narrative-output');
        out.style.display = '';
        if (!data) {
          out.innerHTML = '<p class="assist-error">Analysis unavailable. Try again.</p>';
          return;
        }
        var html = '';
        if (data.ai_error) {
          html += '<p class="assist-hint assist-ai-unavail">AI unavailable — showing rule-based analysis.</p>';
        }
        html += renderSuggestions(data.suggestions, data.ai_used);
        out.innerHTML = html;
      });
    });
  }

  /* ── Dynamic Checklist ───────────────────────────────────────────────────── */
  function initDynamicChecklist() {
    var root = document.getElementById('checklist-assist-root');
    if (!root) return;

    var state = getState();
    var callType = typeof state.callType === 'string' ? state.callType : '';
    if (!callType) return;

    var items = getChecklistItems(callType);
    if (!items.length) return;

    var displayName = callType.replace(/-/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
    var listHtml = '<ul class="assist-checklist">';
    items.forEach(function (item, i) {
      var uid = 'cl-' + i + '-' + Date.now();
      listHtml += '<li class="assist-cl-item"><label class="assist-cl-label">' +
        '<input type="checkbox" class="assist-cl-check" id="' + uid + '" />' +
        '<span>' + esc(item) + '</span>' +
        '</label></li>';
    });
    listHtml += '</ul>';

    root.innerHTML = buildCard('Scene Checklist — ' + displayName, listHtml, true);
  }

  function getChecklistItems(callType) {
    var checklists = {
      'domestic-disturbance': [
        'Separate involved parties before taking statements',
        'Document all visible injuries with photographs',
        'Obtain voluntary statements from all parties',
        'Notify supervisor if arrest or escalation occurs',
        'Complete Domestic Violence Supplement form',
        'Provide victim with DD Form 2701 (VWAP)',
        'Check for existing protective orders',
      ],
      'traffic-accident': [
        'Stabilize scene and establish traffic control',
        'Render / request medical aid for injuries',
        'Capture all driver, vehicle, and insurance data',
        'Complete accident diagram (TA Field Sketch)',
        'Photograph all vehicles, positions, and damage',
        'Obtain voluntary statements from drivers and witnesses',
        'Document tow or impound decision',
      ],
      'use-of-force': [
        'Render medical aid immediately if needed',
        'Notify watch commander as soon as practical',
        'Preserve body cam and all recording evidence',
        'Photograph all injuries to all parties',
        'Submit officer written statement',
        'Complete Use of Force Report (NAVMC 11130)',
        'Supervisor review required before end of shift',
      ],
      'arrest': [
        'Advise rights (Miranda) at custodial interrogation',
        'Document probable cause in writing',
        'Inventory all property before transport',
        'Photograph subject and any evidence',
        'Complete all required forms before booking',
        'Notify watch commander per procedure',
      ],
      'search-consent': [
        'Obtain and document voluntary consent',
        'Document scope of consent given',
        'Photograph evidence in place before collection',
        'Complete evidence/property receipt form',
        'Document chain of custody for seized items',
      ],
      'evidence-seizure': [
        'Photograph evidence in place before moving',
        'Complete OPNAV 5580-22 Evidence Custody Document',
        'Maintain chain of custody documentation',
        'Proper packaging and labeling required',
        'Notify supervisor of significant evidence',
      ],
      'suspicious-person': [
        'Document articulable facts for the contact',
        'Record all identifying information',
        'Document outcome (cleared, issued notice, arrested)',
      ],
      'theft': [
        'Document property description and estimated value',
        'Obtain victim statement',
        'Check for surveillance footage',
        'Document any witness information',
      ],
    };
    return checklists[callType] || [];
  }

  /* ── Smart Forms Assist ──────────────────────────────────────────────────── */
  function initSmartFormsAssist() {
    var root = document.getElementById('forms-assist-root');
    if (!root) return;

    var state = getState();
    postJSON('/mobile/api/forms/smart-suggest', state, function (data) {
      if (!data || !data.suggestions || !data.suggestions.length) return;
      root.innerHTML = buildCard(
        'Smart Paperwork Suggestions',
        '<p class="assist-hint">Based on your incident data. These are suggestions only — officer judgment governs.</p>' +
        renderSuggestions(data.suggestions, false),
        true
      );
    });
  }

  /* ── Packet Summary Generator ────────────────────────────────────────────── */
  function initPacketSummaryAssist() {
    var root = document.getElementById('packet-assist-root');
    if (!root) return;

    root.innerHTML = buildCard(
      'Incident Summary',
      '<p class="assist-hint">Auto-generated from your entered data. Review before finalizing.</p>' +
      '<button class="assist-btn" id="assist-summary-run">Generate Summary</button>' +
      '<div id="assist-summary-output" class="assist-output" style="display:none;"></div>',
      false
    );

    document.getElementById('assist-summary-run').addEventListener('click', function () {
      var state = getState();
      var btn = document.getElementById('assist-summary-run');
      btn.disabled = true;
      btn.textContent = 'Generating…';

      postJSON('/mobile/api/incident/summary', state, function (data) {
        btn.disabled = false;
        btn.textContent = 'Regenerate';
        var out = document.getElementById('assist-summary-output');
        out.style.display = '';
        if (!data || !data.summary) {
          out.innerHTML = '<p class="assist-error">Could not generate summary. Complete more of the incident first.</p>';
          return;
        }
        var s = data.summary;
        var html = '<div class="assist-summary">';
        if (s.incident_type) html += sumRow('Type', s.incident_type);
        if (s.date_time) html += sumRow('Date / Time', s.date_time);
        if (s.location) html += sumRow('Location', s.location);
        if (s.parties && s.parties.length) html += sumRow('Parties', s.parties.join('; '));
        if (s.key_facts && s.key_facts.length) {
          var factsHtml = '<ul class="assist-sum-list">' +
            s.key_facts.map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('') +
            '</ul>';
          html += '<div class="assist-sumrow"><span class="assist-sumkey">Key Facts</span><span class="assist-sumval">' + factsHtml + '</span></div>';
        }
        if (s.actions_taken) html += sumRow('Actions', s.actions_taken);
        if (s.disposition) html += sumRow('Disposition', s.disposition);
        if (s.form_count) html += sumRow('Forms', s.form_count + ' form(s) in packet');
        if (s.statement_count) html += sumRow('Statements', s.statement_count + ' statement(s) captured');
        html += '</div>';
        out.innerHTML = html;
      });
    });
  }

  function sumRow(key, val) {
    return '<div class="assist-sumrow">' +
      '<span class="assist-sumkey">' + esc(key) + '</span>' +
      '<span class="assist-sumval">' + esc(String(val)) + '</span>' +
      '</div>';
  }

}());
