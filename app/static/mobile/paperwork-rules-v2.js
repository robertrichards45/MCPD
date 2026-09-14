(function () {
  'use strict';

  var STORAGE_KEY = 'mcpd.mobile.incident.state';
  var store = window.McpdIncidentStore;
  if (!store) return;

  function clone(value) {
    return JSON.parse(JSON.stringify(value == null ? null : value));
  }

  function readState() {
    try {
      return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}');
    } catch (_error) {
      return {};
    }
  }

  function writeState(state) {
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (_error) {}
    return state;
  }

  function readRules() {
    var node = document.getElementById('mobile-call-type-rules-data');
    if (!node) return {};
    try { return JSON.parse(node.textContent || '{}') || {}; } catch (_error) { return {}; }
  }

  function esc(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function unique(values) {
    var out = [];
    var seen = {};
    (values || []).forEach(function (value) {
      var text = String(value || '').trim();
      var key = text.toLowerCase();
      if (!text || seen[key]) return;
      seen[key] = true;
      out.push(text);
    });
    return out;
  }

  var rules = readRules();
  var originalResetIncident = store.resetIncident ? store.resetIncident.bind(store) : null;

  function ruleFor(state) {
    return state && state.callType ? (rules[state.callType] || null) : null;
  }

  function managedForms(rule) {
    var forms = [].concat((rule && rule.recommendedForms) || []);
    ((rule && rule.conditionalRules) || []).forEach(function (condition) {
      forms = forms.concat(condition.forms || []);
    });
    return unique(forms);
  }

  function automaticForms(rule, circumstances) {
    var forms = [].concat((rule && rule.recommendedForms) || []);
    ((rule && rule.conditionalRules) || []).forEach(function (condition) {
      if (circumstances && circumstances[condition.key]) forms = forms.concat(condition.forms || []);
    });
    return unique(forms);
  }

  function recomputePacket(state) {
    var next = clone(state || {}) || {};
    var rule = ruleFor(next);
    if (!rule) return next;

    var circumstances = next.paperworkCircumstances || {};
    var managed = managedForms(rule);
    var managedKeys = {};
    managed.forEach(function (name) { managedKeys[name.toLowerCase()] = true; });

    var manual = unique(next.paperworkManualForms || (next.selectedForms || []).filter(function (name) {
      return !managedKeys[String(name || '').toLowerCase()];
    }));
    var suppressed = unique(next.paperworkSuppressedForms || []);
    var suppressedKeys = {};
    suppressed.forEach(function (name) { suppressedKeys[name.toLowerCase()] = true; });

    var auto = automaticForms(rule, circumstances).filter(function (name) {
      return !suppressedKeys[name.toLowerCase()];
    });

    next.selectedForms = unique(auto.concat(manual));
    next.paperworkManualForms = manual;
    next.paperworkSuppressedForms = suppressed;
    next.paperworkCircumstances = circumstances;
    next.paperworkGuidance = {
      conditionalRules: clone(rule.conditionalRules || []),
      optionalForms: clone(rule.optionalForms || []),
      notNormallyRequiredForms: clone(rule.notNormallyRequiredForms || [])
    };
    return next;
  }

  store.getState = function () {
    return readState();
  };

  store.resetIncident = function () {
    var state = originalResetIncident ? originalResetIncident() : {};
    state = Object.assign({}, state || {}, {
      paperworkCircumstances: {},
      paperworkManualForms: [],
      paperworkSuppressedForms: [],
      paperworkGuidance: {}
    });
    return writeState(state);
  };

  store.setCallType = function (slug) {
    var current = readState();
    var rule = rules[slug] || null;
    var next = Object.assign({}, current, {
      callType: slug,
      selectedForms: rule ? unique(rule.recommendedForms || []) : [],
      statutes: rule ? clone(rule.statutes || []) : [],
      checklist: rule ? (rule.checklistItems || []).map(function (label, index) {
        return { id: slug + '-check-' + (index + 1), label: label, completed: false };
      }) : [],
      paperworkCircumstances: {},
      paperworkManualForms: [],
      paperworkSuppressedForms: [],
      paperworkGuidance: rule ? {
        conditionalRules: clone(rule.conditionalRules || []),
        optionalForms: clone(rule.optionalForms || []),
        notNormallyRequiredForms: clone(rule.notNormallyRequiredForms || [])
      } : {},
      packetStatus: 'draft'
    });
    return writeState(next);
  };

  store.toggleSelectedForm = function (formName) {
    var state = readState();
    var rule = ruleFor(state);
    var selected = unique(state.selectedForms || []);
    var selectedKeys = selected.map(function (name) { return name.toLowerCase(); });
    var index = selectedKeys.indexOf(String(formName || '').toLowerCase());
    var managed = managedForms(rule);
    var managedKeys = managed.map(function (name) { return name.toLowerCase(); });
    var isManaged = managedKeys.indexOf(String(formName || '').toLowerCase()) >= 0;
    var manual = unique(state.paperworkManualForms || []);
    var suppressed = unique(state.paperworkSuppressedForms || []);

    if (index >= 0) {
      selected.splice(index, 1);
      if (isManaged) suppressed = unique(suppressed.concat([formName]));
      else manual = manual.filter(function (name) { return name.toLowerCase() !== String(formName || '').toLowerCase(); });
    } else {
      selected.push(formName);
      if (isManaged) suppressed = suppressed.filter(function (name) { return name.toLowerCase() !== String(formName || '').toLowerCase(); });
      else manual = unique(manual.concat([formName]));
    }

    state.selectedForms = unique(selected);
    state.paperworkManualForms = manual;
    state.paperworkSuppressedForms = suppressed;
    state.packetStatus = 'forms_reviewed';
    return writeState(recomputePacket(state));
  };

  function setCircumstance(key, enabled) {
    var state = readState();
    var circumstances = Object.assign({}, state.paperworkCircumstances || {});
    circumstances[key] = !!enabled;
    state.paperworkCircumstances = circumstances;
    state.packetStatus = 'forms_reviewed';
    writeState(recomputePacket(state));
  }

  window.McpdPaperworkRulesV2 = {
    recompute: function () { return writeState(recomputePacket(readState())); },
    setCircumstance: setCircumstance,
    readState: readState,
    rules: rules
  };

  function renderMobileRules() {
    var app = document.querySelector('[data-mobile-incident-page]');
    if (!app || app.getAttribute('data-mobile-incident-page') !== 'selected-forms') return;
    var root = document.getElementById('paperwork-rules-v2-root');
    if (!root) return;

    var state = recomputePacket(readState());
    writeState(state);
    var rule = ruleFor(state);
    if (!rule) return;

    var circumstances = state.paperworkCircumstances || {};
    var conditions = rule.conditionalRules || [];
    var notNormal = rule.notNormallyRequiredForms || [];
    var html = '<section class="ops-panel" style="margin-bottom:1rem">' +
      '<div class="eyebrow">Call Type Paperwork</div>' +
      '<h3 style="margin:.25rem 0">' + esc(rule.title || 'Incident packet') + '</h3>' +
      '<p class="text-muted" style="margin:0 0 .75rem">Answer only the circumstances that actually apply. The packet updates from the current Call Type Paperwork Manager rules.</p>';

    if (conditions.length) {
      html += '<div style="display:grid;gap:.65rem">';
      conditions.forEach(function (condition) {
        var checked = circumstances[condition.key] ? ' checked' : '';
        html += '<label class="border rounded p-3" style="display:flex;gap:.7rem;align-items:flex-start">' +
          '<input class="form-check-input" type="checkbox" data-mobile-paperwork-condition="' + esc(condition.key) + '"' + checked + '>' +
          '<span><strong>' + esc(condition.label || condition.key) + '</strong>' +
          '<small class="d-block text-muted" style="margin-top:.25rem">' + esc(condition.question || 'Select when this circumstance applies.') + '</small>' +
          (condition.why ? '<small class="d-block" style="margin-top:.25rem">Why: ' + esc(condition.why) + '</small>' : '') +
          '</span></label>';
      });
      html += '</div>';
    } else {
      html += '<div class="alert alert-light border">No circumstance rules are configured for this call type.</div>';
    }

    if (notNormal.length) {
      html += '<details style="margin-top:.8rem"><summary><strong>Not normally required</strong></summary><ul style="margin:.5rem 0 0;padding-left:1.25rem">';
      notNormal.forEach(function (row) {
        var name = row.form || row.name || '';
        html += '<li>' + esc(name) + (row.why ? ' — ' + esc(row.why) : '') + '</li>';
      });
      html += '</ul></details>';
    }

    html += '<p class="small text-muted" style="margin:.75rem 0 0">Paperwork guidance is decision support. Verify current approved guidance and supervisor direction before final submission.</p></section>';
    root.innerHTML = html;

    root.querySelectorAll('[data-mobile-paperwork-condition]').forEach(function (input) {
      input.addEventListener('change', function () {
        setCircumstance(input.getAttribute('data-mobile-paperwork-condition'), input.checked);
        window.location.reload();
      });
    });
  }

  window.addEventListener('load', renderMobileRules);
}());
