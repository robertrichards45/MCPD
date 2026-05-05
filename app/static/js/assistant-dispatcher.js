(function () {
  'use strict';

  var VOICE_STORAGE_KEY = 'mcpd.assistant.voice';
  var FORM_INTENT_KEY = 'mcpd.guidedFormIntent';
  var AUTO_START_KEY = 'mcpd.guidedFormAutoStart';
  var guidedState = { active: false, fields: [], index: 0, panel: null, input: null, status: null };

  function getSavedVoice() {
    try { return localStorage.getItem(VOICE_STORAGE_KEY) || 'coral'; } catch (e) { return 'coral'; }
  }

  function saveVoice(value) {
    try { localStorage.setItem(VOICE_STORAGE_KEY, value); } catch (e) {}
  }

  function speakRadio(text) {
    if (!window.speechSynthesis || !text) return;
    try {
      window.speechSynthesis.cancel();
      var utt = new SpeechSynthesisUtterance(text);
      utt.rate = getSavedVoice() === 'dispatcher' ? 1.32 : 1.18;
      utt.pitch = getSavedVoice() === 'dispatcher' ? 0.78 : 1.0;
      window.speechSynthesis.speak(utt);
    } catch (e) {}
  }

  function addDispatcherVoiceCard() {
    var list = document.getElementById('ai-voice-list');
    if (!list || list.querySelector('[data-voice="dispatcher"]')) return;
    var card = document.createElement('button');
    card.className = 'ai-voice-card' + (getSavedVoice() === 'dispatcher' ? ' ai-voice-selected' : '');
    card.setAttribute('data-voice', 'dispatcher');
    card.innerHTML = '<div class="ai-voice-card-top"><span class="ai-voice-name">Dispatcher</span><span class="ai-voice-tag">Radio</span></div><div class="ai-voice-desc">Short, direct, radio-style responses</div>';
    card.addEventListener('click', function () {
      saveVoice('dispatcher');
      list.querySelectorAll('.ai-voice-card').forEach(function (c) {
        c.classList.toggle('ai-voice-selected', c.getAttribute('data-voice') === 'dispatcher');
      });
      speakRadio('Dispatcher mode selected. Standing by.');
    });
    list.insertBefore(card, list.firstChild);
  }

  function cleanText(value) {
    return String(value || '').replace(/\*/g, '').replace(/Signature|Initials|Selected/g, '').replace(/\s+/g, ' ').trim();
  }

  function getFieldLabel(el) {
    var block = el.closest('.form-field-block') || el.parentElement;
    var label = block ? block.querySelector('label') : null;
    return cleanText(label ? label.textContent : el.name.replace(/^field_/, ''));
  }

  function collectGuidedFields() {
    var seen = {};
    return Array.prototype.slice.call(document.querySelectorAll('#form-fill-shell [name^="field_"]'))
      .filter(function (el) {
        if (!el.name || seen[el.name] || el.disabled || el.readOnly || el.type === 'hidden') return false;
        seen[el.name] = true;
        return true;
      })
      .map(function (el) {
        return { element: el, label: getFieldLabel(el), type: (el.type || el.tagName || 'text').toLowerCase(), required: !!el.required };
      })
      .filter(function (field) { return field.label; });
  }

  function fieldHasValue(field) {
    if (field.element.type === 'checkbox') return field.element.checked;
    return !!String(field.element.value || '').trim();
  }

  function questionFor(field) {
    if (field.element.type === 'checkbox') return field.label + '? Say yes or no.';
    if (field.type === 'date') return 'What date for ' + field.label + '?';
    if (field.type === 'time') return 'What time for ' + field.label + '?';
    if (field.type === 'number') return 'What number for ' + field.label + '?';
    return 'What should I enter for ' + field.label + '?';
  }

  function setFieldValue(field, answer) {
    var value = String(answer || '').trim();
    if (!value || /^(skip|n\/a|na|not applicable)$/i.test(value)) return;
    if (field.element.type === 'checkbox') {
      field.element.checked = /^(yes|y|true|check|checked|selected|1)$/i.test(value);
    } else {
      field.element.value = value;
    }
    field.element.dispatchEvent(new Event('input', { bubbles: true }));
    field.element.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function ensureGuidedPanel() {
    var existing = document.getElementById('ai-guided-form-panel');
    if (existing) return existing;
    var panel = document.createElement('div');
    panel.id = 'ai-guided-form-panel';
    panel.style.cssText = 'position:fixed;left:12px;right:12px;bottom:12px;z-index:9999;background:#071b33;color:#fff;border:1px solid rgba(255,255,255,.25);border-radius:16px;padding:12px;box-shadow:0 12px 32px rgba(0,0,0,.35);font-family:system-ui,-apple-system,Segoe UI,sans-serif;';
    panel.innerHTML = '<div style="display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:8px;"><strong>AI Guided Form Interview</strong><button type="button" data-guided-close style="background:transparent;color:#fff;border:1px solid rgba(255,255,255,.35);border-radius:8px;padding:4px 8px;">Close</button></div><div data-guided-status style="font-size:14px;line-height:1.35;margin-bottom:8px;">Ready.</div><div style="display:flex;gap:8px;"><input data-guided-answer style="flex:1;border-radius:10px;border:0;padding:10px;" placeholder="Type answer or use voice"/><button type="button" data-guided-voice style="border:0;border-radius:10px;padding:10px;background:#d4af37;color:#071b33;font-weight:700;">Voice</button><button type="button" data-guided-next style="border:0;border-radius:10px;padding:10px;background:#fff;color:#071b33;font-weight:700;">Next</button></div><div style="margin-top:8px;font-size:12px;color:#d6e2f0;">Say or type skip for fields that do not apply. Review before Preview, Download, or Email.</div>';
    document.body.appendChild(panel);
    panel.querySelector('[data-guided-close]').addEventListener('click', function () { guidedState.active = false; panel.remove(); });
    guidedState.panel = panel;
    guidedState.input = panel.querySelector('[data-guided-answer]');
    guidedState.status = panel.querySelector('[data-guided-status]');
    panel.querySelector('[data-guided-next]').addEventListener('click', submitGuidedAnswer);
    guidedState.input.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); submitGuidedAnswer(); } });
    panel.querySelector('[data-guided-voice]').addEventListener('click', listenForGuidedAnswer);
    return panel;
  }

  function askCurrentQuestion() {
    while (guidedState.index < guidedState.fields.length && fieldHasValue(guidedState.fields[guidedState.index])) guidedState.index += 1;
    if (guidedState.index >= guidedState.fields.length) {
      guidedState.active = false;
      if (guidedState.status) guidedState.status.textContent = 'Form interview complete. Review entries, then select Preview, Download, or Email.';
      speakRadio('Form interview complete. Review entries. Then preview, download, or email.');
      return;
    }
    var field = guidedState.fields[guidedState.index];
    var q = questionFor(field);
    if (guidedState.status) guidedState.status.textContent = (guidedState.index + 1) + ' of ' + guidedState.fields.length + ': ' + q;
    if (guidedState.input) { guidedState.input.value = ''; guidedState.input.focus(); }
    speakRadio(q);
  }

  function submitGuidedAnswer() {
    if (!guidedState.active || !guidedState.fields.length) return;
    var field = guidedState.fields[guidedState.index];
    var answer = guidedState.input ? guidedState.input.value : '';
    if (/^(stop|cancel|exit|quit)$/i.test(answer)) {
      guidedState.active = false;
      if (guidedState.status) guidedState.status.textContent = 'Guided interview stopped. Current entries remain on the form.';
      speakRadio('Guided interview stopped.');
      return;
    }
    setFieldValue(field, answer);
    guidedState.index += 1;
    askCurrentQuestion();
  }

  function listenForGuidedAnswer() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { speakRadio('Voice input unavailable. Type the answer.'); return; }
    var rec = new SpeechRecognition();
    rec.lang = 'en-US';
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = function (event) {
      var text = event.results && event.results[0] && event.results[0][0] ? event.results[0][0].transcript : '';
      if (guidedState.input) guidedState.input.value = text;
      submitGuidedAnswer();
    };
    rec.onerror = function () { speakRadio('Voice not copied. Type the answer.'); };
    rec.start();
  }

  function startGuidedFormInterview() {
    if (!document.getElementById('form-fill-shell')) return false;
    var fields = collectGuidedFields();
    ensureGuidedPanel();
    if (!fields.length) {
      if (guidedState.status) guidedState.status.textContent = 'No editable PDF-backed fields found on this form.';
      speakRadio('No editable fields found on this form.');
      return true;
    }
    guidedState.active = true;
    guidedState.fields = fields;
    guidedState.index = 0;
    speakRadio('Guided form interview started. I will ask one question at a time.');
    askCurrentQuestion();
    return true;
  }

  function formQueryFromMessage(text) {
    var lower = String(text || '').toLowerCase();
    if (!/(form|sheet|statement|report|paperwork)/.test(lower)) return '';
    if (lower.indexOf('stat') !== -1) return 'stat sheet';
    var cleaned = lower.replace(/i need|open|start|fill|complete|a |an |the |form|sheet|please|for me/g, ' ').replace(/\s+/g, ' ').trim();
    return cleaned || lower;
  }

  function patchAssistantFetch() {
    var originalFetch = window.fetch;
    if (!originalFetch || originalFetch.mcpdDispatcherPatch) return;
    function patchedFetch(input, init) {
      try {
        var url = (typeof input === 'string') ? input : ((input && input.url) || '');
        if (url.indexOf('/api/assistant/ask') !== -1 && init && init.body) {
          var payload = JSON.parse(init.body);
          payload.voice = getSavedVoice();
          init.body = JSON.stringify(payload);
          var msg = payload.message || '';
          if (/fill this form|complete this form|walk me through|start guided form|ask me questions/i.test(msg) && startGuidedFormInterview()) {
            return Promise.resolve(new Response(JSON.stringify({ ok: true, reply: 'Guided form interview started.', mode: 'local_guided_form' }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
          }
          var query = formQueryFromMessage(msg);
          if (query && !document.getElementById('form-fill-shell')) {
            try { sessionStorage.setItem(FORM_INTENT_KEY, query); sessionStorage.setItem(AUTO_START_KEY, '1'); } catch (e) {}
            speakRadio('Copy. Opening forms library.');
            window.location.assign('/forms?q=' + encodeURIComponent(query));
            return Promise.resolve(new Response(JSON.stringify({ ok: true, reply: 'Opening Forms Library.', mode: 'local_form_navigation' }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
          }
          if (payload.voice === 'dispatcher') speakRadio('Copy. Stand by.');
        }
      } catch (e) {}
      return originalFetch.apply(this, arguments);
    }
    patchedFetch.mcpdDispatcherPatch = true;
    window.fetch = patchedFetch;
  }

  function autoOpenRequestedForm() {
    var intent = '';
    try { intent = sessionStorage.getItem(FORM_INTENT_KEY) || ''; } catch (e) {}
    if (!intent || document.getElementById('form-fill-shell')) return;
    var cards = Array.prototype.slice.call(document.querySelectorAll('.forms-result-card'));
    var best = null;
    var normalized = intent.toLowerCase();
    cards.some(function (card) {
      var title = (card.querySelector('h4') || {}).textContent || '';
      if (title.toLowerCase().indexOf(normalized) !== -1 || (normalized === 'stat sheet' && title.toLowerCase().indexOf('stat') !== -1)) {
        best = card.querySelector('a[href*="/forms/"][href*="/fill"], a.btn-primary');
        return true;
      }
      return false;
    });
    if (best && best.href) {
      speakRadio('Form located. Opening now.');
      window.location.assign(best.href);
    }
  }

  function autoStartIfRequested() {
    if (!document.getElementById('form-fill-shell')) return;
    var shouldStart = false;
    try { shouldStart = sessionStorage.getItem(AUTO_START_KEY) === '1'; sessionStorage.removeItem(AUTO_START_KEY); sessionStorage.removeItem(FORM_INTENT_KEY); } catch (e) {}
    if (shouldStart) setTimeout(startGuidedFormInterview, 800);
  }

  document.addEventListener('click', function () { setTimeout(addDispatcherVoiceCard, 50); });
  window.addEventListener('load', function () {
    patchAssistantFetch();
    addDispatcherVoiceCard();
    autoOpenRequestedForm();
    autoStartIfRequested();
    setInterval(addDispatcherVoiceCard, 1500);
  });
}());
