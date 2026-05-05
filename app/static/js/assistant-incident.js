(function () {
  'use strict';

  var INCIDENT_INTENT_KEY = 'mcpd.incidentAutomationIntent';

  function speak(text) {
    if (!window.speechSynthesis || !text) return;
    try {
      window.speechSynthesis.cancel();
      var utt = new SpeechSynthesisUtterance(text);
      utt.rate = 1.25;
      utt.pitch = 0.85;
      window.speechSynthesis.speak(utt);
    } catch (e) {}
  }

  function normalize(text) {
    return String(text || '').toLowerCase();
  }

  function detectIncidentType(text) {
    var t = normalize(text);
    if (/domestic|family violence|battery|spouse|girlfriend|boyfriend|child abuse|juvenile/.test(t)) return 'domestic disturbance';
    if (/crash|accident|collision|vehicle accident|wreck/.test(t)) return 'accident';
    if (/traffic stop|citation|1408|1805|speeding|dui|license/.test(t)) return 'traffic stop';
    if (/statement|voluntary statement|witness statement/.test(t)) return 'statement';
    if (/evidence|property|found property|lost property|receipt/.test(t)) return 'evidence property';
    if (/trespass|barment|unauthorized entry|base access/.test(t)) return 'trespass';
    if (/stat sheet|stats|daily stats|activity totals/.test(t)) return 'stat sheet';
    return '';
  }

  function recommendedFormsFor(type) {
    var map = {
      'domestic disturbance': ['domestic', 'statement', 'rights', 'incident'],
      'accident': ['accident', 'crash', 'reconstruction', 'statement'],
      'traffic stop': ['1408', '1805', 'traffic', 'citation'],
      'statement': ['statement'],
      'evidence property': ['evidence', 'property', 'receipt'],
      'trespass': ['barment', 'trespass', 'statement'],
      'stat sheet': ['stat sheet', 'stat']
    };
    return map[type] || [];
  }

  function extract5W(text) {
    var raw = String(text || '').trim();
    var lower = normalize(raw);
    var who = [];
    var when = '';
    var where = '';
    var what = '';
    var how = '';

    var atMatch = raw.match(/(?:at|inside|outside|near|behind|in front of)\s+([^,.]+(?:building|bldg|gate|cdc|barracks|warehouse|office|road|street|avenue|ave|drive|dr|lane|ln|boulevard|blvd)?[^,.]*)/i);
    if (atMatch) where = atMatch[0].trim();

    var timeMatch = raw.match(/\b(\d{3,4}\s*hours|\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm)|today|yesterday|this morning|this afternoon|this evening|on\s+\d{1,2}\/\d{1,2}\/\d{2,4})\b/i);
    if (timeMatch) when = timeMatch[0].trim();

    var names = raw.match(/\b[A-Z][a-z]+,?\s+[A-Z][a-z]+\b/g);
    if (names) who = Array.from(new Set(names)).slice(0, 6);

    if (/domestic|argument|fight|battery|assault|child abuse/i.test(raw)) what = 'Domestic disturbance / alleged assault complaint';
    else if (/crash|accident|collision|wreck/i.test(raw)) what = 'Motor vehicle accident / crash';
    else if (/traffic stop|speeding|citation|dui/i.test(raw)) what = 'Traffic enforcement activity';
    else if (/trespass|barment|unauthorized/i.test(raw)) what = 'Unauthorized presence / trespass complaint';
    else if (/property|evidence|found|lost/i.test(raw)) what = 'Property/evidence matter';
    else what = raw.length > 120 ? raw.slice(0, 120) + '...' : raw;

    var howMatch = raw.match(/(?:because|after|when|while|by|via|due to)\s+([^.]*)/i);
    how = howMatch ? howMatch[0].trim() : 'Based on officer-provided facts. Verify details before final report.';

    return { who: who.join('; ') || 'Unknown / not stated', what: what || 'Unknown / not stated', when: when || 'Unknown / not stated', where: where || 'Unknown / not stated', how: how || 'Unknown / not stated', raw: raw, incidentType: detectIncidentType(raw) || 'general incident' };
  }

  function show5WPanel(data) {
    var old = document.getElementById('ai-5w-panel');
    if (old) old.remove();
    var panel = document.createElement('div');
    panel.id = 'ai-5w-panel';
    panel.style.cssText = 'position:fixed;left:12px;right:12px;bottom:12px;z-index:10000;background:#06182d;color:#fff;border:1px solid rgba(255,255,255,.25);border-radius:16px;padding:12px;box-shadow:0 12px 32px rgba(0,0,0,.38);font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-height:70vh;overflow:auto;';
    panel.innerHTML = '<div style="display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:8px;"><strong>5W Builder</strong><button type="button" data-close style="background:transparent;color:#fff;border:1px solid rgba(255,255,255,.35);border-radius:8px;padding:4px 8px;">Close</button></div>' +
      '<div style="display:grid;gap:8px;font-size:14px;">' +
      row('WHO', data.who) + row('WHAT', data.what) + row('WHEN', data.when) + row('WHERE', data.where) + row('HOW', data.how) +
      '</div><div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;"><button type="button" data-copy style="border:0;border-radius:10px;padding:10px;background:#d4af37;color:#071b33;font-weight:700;">Copy 5Ws</button><button type="button" data-forms style="border:0;border-radius:10px;padding:10px;background:#fff;color:#071b33;font-weight:700;">Open Recommended Forms</button></div>';
    document.body.appendChild(panel);
    panel.querySelector('[data-close]').addEventListener('click', function () { panel.remove(); });
    panel.querySelector('[data-copy]').addEventListener('click', function () {
      var txt = 'WHO: ' + data.who + '\nWHAT: ' + data.what + '\nWHEN: ' + data.when + '\nWHERE: ' + data.where + '\nHOW: ' + data.how;
      navigator.clipboard && navigator.clipboard.writeText(txt).then(function () { speak('5 Ws copied.'); });
    });
    panel.querySelector('[data-forms]').addEventListener('click', function () { openIncidentForms(data.incidentType); });
    speak('5 W builder complete. Review who, what, when, where, and how.');
  }

  function row(label, value) {
    return '<div style="background:rgba(255,255,255,.08);border-radius:12px;padding:8px;"><div style="font-size:11px;color:#d4af37;font-weight:800;letter-spacing:.08em;">' + label + '</div><div>' + escapeHtml(value) + '</div></div>';
  }

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"]/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]; });
  }

  function openIncidentForms(type) {
    var forms = recommendedFormsFor(type);
    var q = forms[0] || type || 'forms';
    try { sessionStorage.setItem(INCIDENT_INTENT_KEY, JSON.stringify({ type: type, forms: forms })); } catch (e) {}
    speak('Opening recommended forms.');
    window.location.assign('/forms?q=' + encodeURIComponent(q));
  }

  function autoShowIncidentFormRecommendations() {
    var raw = '';
    try { raw = sessionStorage.getItem(INCIDENT_INTENT_KEY) || ''; } catch (e) {}
    if (!raw || !document.querySelector('.forms-library-shell')) return;
    var data = null;
    try { data = JSON.parse(raw); } catch (e) {}
    if (!data || !data.forms) return;
    var existing = document.getElementById('incident-form-recommend-panel');
    if (existing) return;
    var panel = document.createElement('div');
    panel.id = 'incident-form-recommend-panel';
    panel.style.cssText = 'margin:12px 0;padding:12px;border-radius:14px;background:#071b33;color:#fff;border:1px solid rgba(255,255,255,.2);';
    panel.innerHTML = '<strong>Recommended forms for ' + escapeHtml(data.type) + '</strong><div style="font-size:13px;margin-top:4px;">Search terms: ' + escapeHtml(data.forms.join(', ')) + '</div><div style="font-size:12px;color:#d6e2f0;margin-top:6px;">Open the required form, then say: fill this form.</div>';
    var head = document.querySelector('.forms-library-shell .page-head') || document.querySelector('.forms-library-shell');
    if (head && head.parentNode) head.parentNode.insertBefore(panel, head.nextSibling);
  }

  function shouldStart5W(text) {
    return /5w|5 w|five w|who what when where how|builder everything|narrative builder|build narrative facts/i.test(text || '');
  }

  function patchAssistantForIncidents() {
    var originalFetch = window.fetch;
    if (!originalFetch || originalFetch.mcpdIncidentPatch) return;
    function patchedFetch(input, init) {
      try {
        var url = (typeof input === 'string') ? input : ((input && input.url) || '');
        if (url.indexOf('/api/assistant/ask') !== -1 && init && init.body) {
          var payload = JSON.parse(init.body);
          var msg = payload.message || '';
          var type = detectIncidentType(msg);
          if (shouldStart5W(msg)) {
            show5WPanel(extract5W(msg));
            return Promise.resolve(new Response(JSON.stringify({ ok: true, reply: '5W builder complete. Review the extracted facts.', mode: 'local_5w_builder' }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
          }
          if (/incident based forms|incident forms|what forms|forms for this incident|paperwork for this incident/i.test(msg) && type) {
            openIncidentForms(type);
            return Promise.resolve(new Response(JSON.stringify({ ok: true, reply: 'Opening recommended forms for ' + type + '.', mode: 'local_incident_forms' }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
          }
        }
      } catch (e) {}
      return originalFetch.apply(this, arguments);
    }
    patchedFetch.mcpdIncidentPatch = true;
    window.fetch = patchedFetch;
  }

  window.addEventListener('load', function () {
    patchAssistantForIncidents();
    autoShowIncidentFormRecommendations();
  });
}());
