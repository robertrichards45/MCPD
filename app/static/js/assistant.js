(function () {
  'use strict';

  // Don't inject on auth/landing pages (no user session)
  if (document.body.classList.contains('landing')) return;

  // ── Voice catalogue ────────────────────────────────────────────────────────
  // label, gender hint, personality description
  var VOICES = [
    { id: 'coral',   label: 'Coral',   tag: 'Female',  desc: 'Warm & natural — recommended' },
    { id: 'nova',    label: 'Nova',    tag: 'Female',  desc: 'Clear & friendly' },
    { id: 'shimmer', label: 'Shimmer', tag: 'Female',  desc: 'Expressive & bright' },
    { id: 'ash',     label: 'Ash',     tag: 'Male',    desc: 'Casual & warm' },
    { id: 'onyx',    label: 'Onyx',    tag: 'Male',    desc: 'Deep & authoritative' },
    { id: 'echo',    label: 'Echo',    tag: 'Male',    desc: 'Clear & measured' },
    { id: 'fable',   label: 'Fable',   tag: 'Male',    desc: 'Expressive & articulate' },
    { id: 'alloy',   label: 'Alloy',   tag: 'Neutral', desc: 'Neutral & versatile' },
    { id: 'verse',   label: 'Verse',   tag: 'Neutral', desc: 'Dynamic & engaging' },
  ];

  var VOICE_STORAGE_KEY = 'mcpd.assistant.voice';
  var HISTORY_STORAGE_KEY = 'mcpd.assistant.history';
  var DEFAULT_VOICE     = 'coral';
  var Voice = window.MCPDVoiceAssistant || {};

  function getSavedVoice() {
    try { return localStorage.getItem(VOICE_STORAGE_KEY) || DEFAULT_VOICE; } catch (e) { return DEFAULT_VOICE; }
  }
  function saveVoice(v) {
    try { localStorage.setItem(VOICE_STORAGE_KEY, v); } catch (e) {}
  }
  function loadHistory() {
    try {
      var saved = JSON.parse(localStorage.getItem(HISTORY_STORAGE_KEY) || '[]');
      return Array.isArray(saved) ? saved.slice(-20) : [];
    } catch (e) {
      return [];
    }
  }
  function saveHistory() {
    try { localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history.slice(-20))); } catch (e) {}
  }

  // ── State ──────────────────────────────────────────────────────────────────
  var history      = loadHistory();
  var isOpen       = false;
  var isListening  = false;
  var isThinking   = false;
  var voiceMode    = false;
  var showSettings = false;
  var audioQueue   = null;
  var recognition  = null;
  var speechRunId  = 0;
  var formInterview = { active: false, fields: [], index: 0 };
  var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  // ── Build DOM ──────────────────────────────────────────────────────────────

  function buildUI() {
    // Floating button
    var btn = document.createElement('button');
    btn.id = 'ai-fab';
    btn.className = 'ai-fab';
    btn.setAttribute('aria-label', 'Open MCPD AI Assistant');
    btn.innerHTML = [
      '<svg class="ai-fab-icon ai-fab-chat" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">',
      '  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
      '</svg>',
      '<svg class="ai-fab-icon ai-fab-mic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">',
      '  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>',
      '  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>',
      '  <line x1="12" y1="19" x2="12" y2="23"/>',
      '  <line x1="8" y1="23" x2="16" y2="23"/>',
      '</svg>',
    ].join('');
    document.body.appendChild(btn);

    // Panel
    var panel = document.createElement('div');
    panel.id = 'ai-panel';
    panel.className = 'ai-panel ai-panel-hidden';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'MCPD AI Assistant');
    panel.innerHTML = [
      '<div class="ai-panel-header">',
      '  <div class="ai-panel-title">',
      '    <span class="ai-panel-dot" id="ai-status-dot"></span>',
      '    <strong>MCPD Assistant</strong>',
      '    <span id="ai-status-label" class="ai-status-label"></span>',
      '  </div>',
      '  <div class="ai-panel-actions">',
      '    <button id="ai-settings-btn" class="ai-icon-btn" title="Voice settings" aria-label="Voice settings">',
      '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">',
      '        <circle cx="12" cy="12" r="3"/>',
      '        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
      '      </svg>',
      '    </button>',
      '    <button id="ai-clear-btn" class="ai-icon-btn" title="Clear conversation" aria-label="Clear conversation">',
      '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>',
      '    </button>',
      '    <button id="ai-close-btn" class="ai-icon-btn" title="Close" aria-label="Close assistant">',
      '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
      '    </button>',
      '  </div>',
      '</div>',
      // Settings panel (hidden by default)
      '<div id="ai-settings-panel" class="ai-settings-panel ai-settings-hidden">',
      '  <div class="ai-settings-title">Choose a Voice</div>',
      '  <div id="ai-tts-status" class="ai-settings-subtitle">Checking voice engine…</div>',
      '  <div id="ai-voice-list" class="ai-voice-list"></div>',
      '  <div class="ai-voice-controls" aria-label="Assistant voice controls">',
      '    <button id="ai-stop-voice-btn" class="btn btn-sm btn-outline" type="button">Stop</button>',
      '    <button id="ai-replay-voice-btn" class="btn btn-sm btn-outline" type="button">Replay</button>',
      '    <button id="ai-voice-toggle-btn" class="btn btn-sm btn-outline" type="button">Voice On</button>',
      '    <label class="ai-speed-label" for="ai-voice-speed">Voice Speed</label>',
      '    <select id="ai-voice-speed" class="form-control form-control-sm">',
      '      <option value="normal">Normal</option>',
      '      <option value="fast">Fast</option>',
      '      <option value="veryfast">Very Fast</option>',
      '    </select>',
      '  </div>',
      '  <div class="ai-settings-subtitle">The assistant speaks a short summary first. Use Read Full Response when needed.</div>',
      '  <button id="ai-settings-done" class="btn btn-sm btn-primary w-100 mt-2">Done</button>',
      '</div>',
      // Messages area
      '<div id="ai-messages" class="ai-messages" aria-live="polite"></div>',
      '<div class="ai-input-row">',
      '  <button id="ai-mic-btn" class="ai-mic-btn" title="Click to speak" aria-label="Voice input">',
      '    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>',
      '  </button>',
      '  <input id="ai-text-input" class="ai-text-input" type="text" placeholder="Ask anything…" autocomplete="off" />',
      '  <button id="ai-send-btn" class="ai-send-btn" aria-label="Send">',
      '    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
      '  </button>',
      '</div>',
    ].join('\n');
    document.body.appendChild(panel);

    buildVoiceList();

    // Events
    btn.addEventListener('click', onFabClick);
    document.getElementById('ai-close-btn').addEventListener('click', closePanel);
    document.getElementById('ai-clear-btn').addEventListener('click', clearHistory);
    document.getElementById('ai-send-btn').addEventListener('click', sendText);
    document.getElementById('ai-settings-btn').addEventListener('click', toggleSettings);
    document.getElementById('ai-settings-done').addEventListener('click', toggleSettings);
    document.getElementById('ai-stop-voice-btn').addEventListener('click', function () { stopAudio(); });
    document.getElementById('ai-replay-voice-btn').addEventListener('click', function () {
      if (Voice.replayLastVoice) Voice.replayLastVoice();
    });
    document.getElementById('ai-voice-toggle-btn').addEventListener('click', function () {
      var enabled = Voice.getVoiceEnabled ? !Voice.getVoiceEnabled() : false;
      if (Voice.toggleVoice) Voice.toggleVoice(enabled);
      syncVoiceControls();
    });
    document.getElementById('ai-voice-speed').addEventListener('change', function (event) {
      if (Voice.setVoiceSpeed) Voice.setVoiceSpeed(event.target.value);
      if (Voice.stopVoice) Voice.stopVoice();
      syncVoiceControls();
    });
    document.getElementById('ai-text-input').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(); }
    });
    document.getElementById('ai-text-input').addEventListener('input', function () {
      if (isListening) stopListening();
      voiceMode = false;
      updateUI();
    });

    setupMic();
    syncVoiceControls();
    if (Voice.isVoiceSupported && !Voice.isVoiceSupported()) {
      setTTSStatus('unsupported');
    }

    setTimeout(function () {
      var v = VOICES.find(function (x) { return x.id === getSavedVoice(); }) || VOICES[0];
      appendMessage('assistant', 'Hello. I\'m the MCPD AI Assistant, speaking with the ' + v.label + ' voice. Tap the mic or type to get started.');
    }, 300);
  }

  function syncVoiceControls() {
    var toggle = document.getElementById('ai-voice-toggle-btn');
    var speed = document.getElementById('ai-voice-speed');
    var enabled = Voice.getVoiceEnabled ? Voice.getVoiceEnabled() : true;
    if (toggle) toggle.textContent = enabled ? 'Voice On' : 'Voice Off';
    if (speed && Voice.getVoiceSpeed) speed.value = Voice.getVoiceSpeed();
  }

  // ── Voice picker ───────────────────────────────────────────────────────────

  function buildVoiceList() {
    var list = document.getElementById('ai-voice-list');
    if (!list) return;
    list.innerHTML = '';
    var current = getSavedVoice();
    VOICES.forEach(function (v) {
      var card = document.createElement('button');
      card.className = 'ai-voice-card' + (v.id === current ? ' ai-voice-selected' : '');
      card.setAttribute('data-voice', v.id);
      card.innerHTML = [
        '<div class="ai-voice-card-top">',
        '  <span class="ai-voice-name">' + v.label + '</span>',
        '  <span class="ai-voice-tag">' + v.tag + '</span>',
        '</div>',
        '<div class="ai-voice-desc">' + v.desc + '</div>',
      ].join('');
      card.addEventListener('click', function () {
        saveVoice(v.id);
        list.querySelectorAll('.ai-voice-card').forEach(function (c) {
          c.classList.toggle('ai-voice-selected', c.getAttribute('data-voice') === v.id);
        });
        // Play a short preview
        previewVoice(v.id);
      });
      list.appendChild(card);
    });
  }

  function previewVoice(voiceId) {
    var previewText = 'This is the ' + (VOICES.find(function (v) { return v.id === voiceId; }) || {label: voiceId}).label + ' voice.';
    stopAudio();
    fetch('/api/assistant/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: previewText, voice: voiceId }),
    })
      .then(function (r) { return r.ok ? r.blob() : Promise.reject(); })
      .then(function (blob) {
        setTTSStatus('openai');
        var url = URL.createObjectURL(blob);
        var audio = new Audio(url);
        audioQueue = audio;
        audio.onended = function () { URL.revokeObjectURL(url); audioQueue = null; };
        audio.play().catch(function () {});
      })
      .catch(function () {
        setTTSStatus('browser');
        browserSpeak(previewText, voiceId, null);
      });
  }

  function toggleSettings() {
    showSettings = !showSettings;
    var sp = document.getElementById('ai-settings-panel');
    var msgs = document.getElementById('ai-messages');
    if (showSettings) {
      buildVoiceList();
      sp.classList.remove('ai-settings-hidden');
      msgs.style.display = 'none';
    } else {
      sp.classList.add('ai-settings-hidden');
      msgs.style.display = '';
    }
    document.getElementById('ai-settings-btn').classList.toggle('ai-icon-btn-active', showSettings);
  }

  // ── FAB ────────────────────────────────────────────────────────────────────

  function onFabClick() {
    if (!isOpen) {
      openPanel();
      if (SpeechRecognition && !isThinking) {
        voiceMode = true;
        startListening();
      }
    } else {
      if (isListening) {
        voiceMode = false;
        stopListening();
      } else {
        closePanel();
      }
    }
  }

  function openPanel() {
    isOpen = true;
    document.getElementById('ai-panel').classList.remove('ai-panel-hidden');
    document.getElementById('ai-panel').classList.add('ai-panel-open');
    document.getElementById('ai-fab').classList.add('ai-fab-active');
  }

  function closePanel() {
    voiceMode = false;
    stopListening();
    stopAudio();
    isOpen = false;
    showSettings = false;
    document.getElementById('ai-panel').classList.remove('ai-panel-open');
    document.getElementById('ai-panel').classList.add('ai-panel-hidden');
    document.getElementById('ai-fab').classList.remove('ai-fab-active', 'ai-fab-listening');
    var sp = document.getElementById('ai-settings-panel');
    if (sp) sp.classList.add('ai-settings-hidden');
    var msgs = document.getElementById('ai-messages');
    if (msgs) msgs.style.display = '';
    updateUI();
  }

  function clearHistory() {
    history = [];
    saveHistory();
    document.getElementById('ai-messages').innerHTML = '';
    appendMessage('assistant', 'Conversation cleared. How can I help you?');
    if (voiceMode && !isThinking) startListening();
  }

  // ── Status UI ──────────────────────────────────────────────────────────────

  function updateUI() {
    var fab    = document.getElementById('ai-fab');
    var dot    = document.getElementById('ai-status-dot');
    var label  = document.getElementById('ai-status-label');
    var micBtn = document.getElementById('ai-mic-btn');
    if (isListening) {
      fab.classList.add('ai-fab-listening');
      if (dot)    dot.classList.add('ai-dot-listening');
      if (label)  label.textContent = 'Listening…';
      if (micBtn) micBtn.classList.add('ai-mic-active');
    } else if (isThinking) {
      fab.classList.remove('ai-fab-listening');
      if (dot)    dot.classList.remove('ai-dot-listening');
      if (label)  label.textContent = 'Thinking…';
      if (micBtn) micBtn.classList.remove('ai-mic-active');
    } else {
      fab.classList.remove('ai-fab-listening');
      if (dot)    dot.classList.remove('ai-dot-listening');
      if (label)  label.textContent = voiceMode ? 'Voice on' : '';
      if (micBtn) micBtn.classList.remove('ai-mic-active');
    }
  }

  // ── Messages ───────────────────────────────────────────────────────────────

  function appendMessage(role, text) {
    var msgs = document.getElementById('ai-messages');
    var bubble = document.createElement('div');
    bubble.className = 'ai-bubble ai-bubble-' + role;
    bubble.textContent = text;
    msgs.appendChild(bubble);
    msgs.scrollTop = msgs.scrollHeight;
    return bubble;
  }

  function updateMessage(bubble, text) {
    if (!bubble) return;
    bubble.textContent = text;
    var msgs = document.getElementById('ai-messages');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  function addReadFullControl(bubble, text) {
    if (!bubble || !text) return;
    var button = document.createElement('button');
    button.className = 'ai-read-full-btn';
    button.type = 'button';
    button.textContent = 'Read Full Response';
    button.addEventListener('click', function () {
      if (Voice.speakFull) Voice.speakFull(text);
      else browserSpeak(text, getSavedVoice(), null);
    });
    bubble.appendChild(document.createElement('br'));
    bubble.appendChild(button);
  }

  function showTyping() {
    var msgs   = document.getElementById('ai-messages');
    var bubble = document.createElement('div');
    bubble.className = 'ai-bubble ai-bubble-assistant ai-typing';
    bubble.id = 'ai-typing-indicator';
    bubble.innerHTML = '<span></span><span></span><span></span>';
    msgs.appendChild(bubble);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function hideTyping() {
    var el = document.getElementById('ai-typing-indicator');
    if (el) el.parentNode.removeChild(el);
  }

  function getPageContext() {
    var formHeading = document.querySelector('.forms-fill-page h2');
    return {
      path: window.location.pathname,
      title: document.title || '',
      formTitle: formHeading ? formHeading.textContent.trim() : '',
    };
  }

  function normalizeLabel(text) {
    return String(text || '').replace(/\*/g, '').replace(/Signature|Initials|Selected/g, '').replace(/\s+/g, ' ').trim();
  }

  function getFormInterviewFields() {
    var seen = {};
    return Array.prototype.slice.call(document.querySelectorAll('#form-fill-shell [name^="field_"]'))
      .filter(function (el) {
        if (!el.name || seen[el.name] || el.disabled || el.readOnly || el.type === 'hidden') return false;
        seen[el.name] = true;
        return true;
      })
      .map(function (el) {
        var block = el.closest('.form-field-block') || el.parentElement;
        var labelEl = block ? block.querySelector('label') : null;
        var label = normalizeLabel(labelEl ? labelEl.textContent : el.name.replace(/^field_/, ''));
        return {
          element: el,
          label: label || el.name.replace(/^field_/, ''),
          type: (el.type || el.tagName || 'text').toLowerCase(),
          required: !!el.required,
        };
      })
      .filter(function (field) { return field.label; })
      .sort(function (a, b) {
        if (a.required !== b.required) return a.required ? -1 : 1;
        return 0;
      });
  }

  function formQuestionFor(field) {
    if (field.type === 'checkbox') return field.label + '? Answer yes or no.';
    if (field.type === 'date') return 'What date should I enter for ' + field.label + '?';
    if (field.type === 'time') return 'What time should I enter for ' + field.label + '?';
    return 'What should I enter for ' + field.label + '?';
  }

  function speakAssistantLine(text) {
    appendMessage('assistant', text);
    speakText(text);
  }

  function askCurrentFormQuestion() {
    while (formInterview.index < formInterview.fields.length) {
      var field = formInterview.fields[formInterview.index];
      var value = field.element.type === 'checkbox' ? (field.element.checked ? 'yes' : '') : (field.element.value || '').trim();
      if (!value) {
        speakAssistantLine(formQuestionFor(field));
        return;
      }
      formInterview.index += 1;
    }
    formInterview.active = false;
    speakAssistantLine('The visible form questions are complete. Review the form, then use Preview, Download, Email, or Save.');
  }

  function startFormInterview() {
    var fields = getFormInterviewFields();
    if (!fields.length) {
      speakAssistantLine('I do not see editable PDF-backed fields on this page. Open a fillable form first, then ask me to help fill it out.');
      return;
    }
    formInterview = { active: true, fields: fields, index: 0 };
    speakAssistantLine('I will walk you through this form one question at a time. Say or type skip if a field does not apply.');
    askCurrentFormQuestion();
  }

  function handleFormInterviewAnswer(text) {
    var field = formInterview.fields[formInterview.index];
    if (!field) { formInterview.active = false; return false; }
    var answer = String(text || '').trim();
    appendMessage('user', answer);
    if (/^(stop|cancel|quit|exit)$/i.test(answer)) {
      formInterview.active = false;
      speakAssistantLine('Form assistant stopped. Your current entries remain on the page.');
      return true;
    }
    if (!/^(skip|na|n\/a|not applicable)$/i.test(answer)) {
      if (field.element.type === 'checkbox') {
        field.element.checked = /^(yes|y|true|check|checked|select|selected|1)$/i.test(answer);
      } else {
        field.element.value = answer;
      }
      field.element.dispatchEvent(new Event('input', { bubbles: true }));
      field.element.dispatchEvent(new Event('change', { bubbles: true }));
    }
    formInterview.index += 1;
    askCurrentFormQuestion();
    return true;
  }

  function maybeStartLocalFormInterview(text) {
    if (!document.getElementById('form-fill-shell')) return false;
    if (!/fill|complete|walk me through|ask me questions|form assistant|help me/i.test(text || '')) return false;
    appendMessage('user', text);
    startFormInterview();
    return true;
  }

  function applyAssistantAction(action) {
    if (!action || !action.type) return;
    if (action.type === 'form_interview') {
      startFormInterview();
      return;
    }
    if (action.type === 'navigate' && action.url) {
      setTimeout(function () { window.location.assign(action.url); }, 1400);
    }
  }

  function normalizedCommandText(text) {
    return String(text || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function isElementVisible(el) {
    if (!el || el.disabled || el.getAttribute('aria-disabled') === 'true') return false;
    var rect = el.getBoundingClientRect();
    var style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  }

  function labelForInteractive(el) {
    return normalizedCommandText(
      el.getAttribute('aria-label')
      || el.getAttribute('title')
      || el.textContent
      || el.value
      || ''
    );
  }

  function findInteractiveByLabel(label) {
    var wanted = normalizedCommandText(label);
    if (!wanted) return null;
    var candidates = Array.prototype.slice.call(document.querySelectorAll('a[href], button, summary, [role="button"], input[type="submit"], input[type="button"]'));
    var visible = candidates.filter(isElementVisible).map(function (el) {
      return { el: el, label: labelForInteractive(el) };
    }).filter(function (item) { return item.label; });
    var exact = visible.find(function (item) { return item.label === wanted; });
    if (exact) return exact.el;
    var contains = visible.find(function (item) { return item.label.indexOf(wanted) !== -1 || wanted.indexOf(item.label) !== -1; });
    return contains ? contains.el : null;
  }

  function tryDirectInterfaceCommand(text) {
    var match = String(text || '').match(/^(?:click|tap|press|select|choose|open)\s+(.+)$/i);
    if (!match) return false;
    var targetLabel = match[1].replace(/\b(button|link|tab|menu|page)\b/ig, '').trim();
    var target = findInteractiveByLabel(targetLabel);
    appendMessage('user', text);
    if (!target) {
      speakAssistantLine('I could not find a visible control named ' + targetLabel + ' on this screen.');
      return true;
    }
    target.focus({ preventScroll: false });
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    target.classList.add('ai-command-target');
    setTimeout(function () {
      target.classList.remove('ai-command-target');
      target.click();
    }, 250);
    speakAssistantLine('Selecting ' + targetLabel + '.');
    return true;
  }

  // ── Send ───────────────────────────────────────────────────────────────────

  function sendText() {
    var input = document.getElementById('ai-text-input');
    var text  = (input.value || '').trim();
    if (!text || isThinking) return;
    input.value = '';
    voiceMode = false;
    if (formInterview.active && handleFormInterviewAnswer(text)) return;
    if (maybeStartLocalFormInterview(text)) return;
    if (tryDirectInterfaceCommand(text)) return;
    submitMessage(text);
  }

  function submitMessage(text) {
    if (!isOpen) openPanel();
    stopListening();
    stopAudio();
    var currentSpeechRun = ++speechRunId;
    appendMessage('user', text);
    isThinking = true;
    updateUI();
    var thinkingBubble = appendMessage('assistant', 'Thinking...');
    var processingTimer = Voice.speakProcessingIfDelayed ? Voice.speakProcessingIfDelayed(1000) : setTimeout(function () {
      if (isThinking && currentSpeechRun === speechRunId) {
        browserSpeak('Processing request.', getSavedVoice(), null, { cancel: false });
      }
    }, 1000);

    fetch('/api/assistant/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: history.slice(), page: getPageContext() }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (Voice.cancelProcessing) Voice.cancelProcessing(processingTimer);
        else clearTimeout(processingTimer);
        hideTyping();
        isThinking = false;
        if (Voice.startVoiceStatus) Voice.startVoiceStatus('Answering...');
        var reply = (data && data.reply) ? data.reply : 'Sorry, I could not get a response.';
        if (data && data.mode === 'local_fallback') {
          var label = document.getElementById('ai-status-label');
          if (label) label.textContent = 'Local assist';
        }
        stopAudio();
        updateMessage(thinkingBubble, reply);
        addReadFullControl(thinkingBubble, reply);
        speakText(reply);
        history.push({ role: 'user',      content: text  });
        history.push({ role: 'assistant', content: reply });
        if (history.length > 20) history = history.slice(history.length - 20);
        saveHistory();
        updateUI();
        applyAssistantAction(data && data.action);
      })
      .catch(function () {
        if (Voice.cancelProcessing) Voice.cancelProcessing(processingTimer);
        else clearTimeout(processingTimer);
        hideTyping();
        isThinking = false;
        updateUI();
        updateMessage(thinkingBubble, 'Connection error. Please try again.');
        speakText('Connection error. Please try again.');
        if (voiceMode) scheduleAutoListen();
      });
  }

  // ── TTS ────────────────────────────────────────────────────────────────────

  function setTTSStatus(mode) {
    var el = document.getElementById('ai-tts-status');
    if (!el) return;
    if (mode === 'openai') {
      el.textContent = '✓ OpenAI TTS active — high-quality voices';
      el.style.color = '#4ade80';
    } else if (mode === 'instant') {
      el.textContent = 'Instant browser voice active';
      el.style.color = '#4ade80';
    } else if (mode === 'unsupported') {
      el.textContent = 'Voice playback is not supported on this device/browser.';
      el.style.color = '#fbbf24';
    } else {
      el.textContent = '⚠ Browser fallback — set OPENAI_API_KEY in Railway for real voices';
      el.style.color = '#fbbf24';
    }
  }

  function speakText(text) {
    if (!text) { if (voiceMode) scheduleAutoListen(); return; }
    stopAudio();
    setTTSStatus(Voice.isVoiceSupported && !Voice.isVoiceSupported() ? 'unsupported' : 'instant');
    if (Voice.speakSummary) {
      Voice.speakSummary(text, function () { if (voiceMode) scheduleAutoListen(); });
      return;
    }
    browserSpeak(text, getSavedVoice(), function () { if (voiceMode) scheduleAutoListen(); });
    return;

    fetch('/api/assistant/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text, voice: getSavedVoice() }),
    })
      .then(function (r) {
        if (!r.ok) {
          console.warn('[MCPD TTS] Server returned', r.status, '— falling back to browser voice');
          setTTSStatus('browser');
          throw new Error('tts-unavailable');
        }
        return r.blob();
      })
      .then(function (blob) {
        var url   = URL.createObjectURL(blob);
        var audio = new Audio(url);
        audioQueue = audio;
        setTTSStatus('openai');
        audio.onended = function () {
          URL.revokeObjectURL(url);
          audioQueue = null;
          if (voiceMode) scheduleAutoListen();
        };
        audio.onerror = function () { audioQueue = null; if (voiceMode) scheduleAutoListen(); };
        audio.play().catch(function (e) {
          console.warn('[MCPD TTS] Audio play blocked:', e);
          if (voiceMode) scheduleAutoListen();
        });
      })
      .catch(function () {
        setTTSStatus('browser');
        browserSpeak(text, getSavedVoice(), function () { if (voiceMode) scheduleAutoListen(); });
      });
  }

  function stopAudio() {
    if (audioQueue) { try { audioQueue.pause(); } catch (e) {} audioQueue = null; }
    if (Voice.stopVoice) { Voice.stopVoice(); return; }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  }

  var BROWSER_VOICE_PROFILES = {
    coral:   { pitch: 1.10, rate: 1.00, gender: 'female' },
    nova:    { pitch: 1.25, rate: 1.05, gender: 'female' },
    shimmer: { pitch: 1.35, rate: 1.10, gender: 'female' },
    ash:     { pitch: 0.90, rate: 0.97, gender: 'male'   },
    onyx:    { pitch: 0.70, rate: 0.90, gender: 'male'   },
    echo:    { pitch: 1.00, rate: 1.00, gender: 'male'   },
    fable:   { pitch: 1.10, rate: 1.05, gender: 'male'   },
    alloy:   { pitch: 1.00, rate: 1.00, gender: 'neutral'},
    verse:   { pitch: 0.95, rate: 1.10, gender: 'neutral'},
  };

  function splitSpeechText(text) {
    var clean = String(text || '').replace(/\s+/g, ' ').trim();
    if (!clean) return [];
    return (clean.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [clean])
      .map(function (part) { return part.trim(); })
      .filter(Boolean);
  }

  function pickBrowserVoice(voiceId) {
    var profile = BROWSER_VOICE_PROFILES[voiceId] || BROWSER_VOICE_PROFILES.coral;
    var voices = window.speechSynthesis.getVoices();
    var isFemale = profile.gender === 'female';
    var isMale   = profile.gender === 'male';
    return voices.find(function (v) {
      if (!/en/i.test(v.lang)) return false;
      var n = v.name.toLowerCase();
      if (isFemale) return /samantha|zira|susan|karen|victoria|moira|fiona|tessa/.test(n);
      if (isMale)   return /alex|daniel|david|fred|james|oliver|rishi/.test(n);
      return false;
    }) || voices.find(function (v) { return /en[-_]US/i.test(v.lang); })
      || voices.find(function (v) { return /en/i.test(v.lang); });
  }

  function browserSpeak(text, voiceId, onDone, options) {
    if (!window.speechSynthesis) { if (onDone) onDone(); return; }
    options = options || {};
    if (options.cancel !== false) window.speechSynthesis.cancel();

    var profile = BROWSER_VOICE_PROFILES[voiceId] || BROWSER_VOICE_PROFILES.coral;
    var preferred = pickBrowserVoice(voiceId);
    var parts = splitSpeechText(text);
    var index = 0;

    function speakNext() {
      if (index >= parts.length) { if (onDone) onDone(); return; }
      var utt = new SpeechSynthesisUtterance(parts[index]);
      index += 1;
      utt.rate  = options.rate || (Voice.getVoiceRate ? Voice.getVoiceRate() : profile.rate);
      utt.pitch = profile.pitch;
      if (preferred) utt.voice = preferred;
      utt.onend = speakNext;
      utt.onerror = speakNext;
      window.speechSynthesis.speak(utt);
    }

    speakNext();
  }

  // ── Auto-listen loop ───────────────────────────────────────────────────────

  function scheduleAutoListen() {
    if (!voiceMode || !isOpen || isThinking) return;
    setTimeout(function () {
      if (voiceMode && isOpen && !isThinking && !isListening) startListening();
    }, 700);
  }

  // ── Voice recognition ──────────────────────────────────────────────────────

  function setupMic() {
    var micBtn = document.getElementById('ai-mic-btn');
    if (!SpeechRecognition) { micBtn.style.display = 'none'; return; }

    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = function (event) {
      var transcript = (event.results[0][0].transcript || '').trim();
      var input = document.getElementById('ai-text-input');
      input.value = transcript;
      isListening = false;
      updateUI();
      if (transcript) {
        if (formInterview.active) handleFormInterviewAnswer(transcript);
        else if (maybeStartLocalFormInterview(transcript)) return;
        else if (tryDirectInterfaceCommand(transcript)) return;
        else submitMessage(transcript);
      }
    };
    recognition.onerror = function (e) {
      isListening = false;
      updateUI();
      if (voiceMode && e.error === 'no-speech') scheduleAutoListen();
    };
    recognition.onend = function () { isListening = false; updateUI(); };

    micBtn.addEventListener('click', function () {
      if (isListening) { voiceMode = false; stopListening(); }
      else             { voiceMode = true;  startListening(); }
    });
  }

  function startListening() {
    if (isListening || !recognition || isThinking) return;
    isListening = true;
    updateUI();
    try { recognition.start(); } catch (e) { isListening = false; updateUI(); }
  }

  function stopListening() {
    if (!isListening || !recognition) return;
    isListening = false;
    updateUI();
    try { recognition.stop(); } catch (e) {}
  }

  // ── Init ───────────────────────────────────────────────────────────────────

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', buildUI);
  } else {
    buildUI();
  }
}());
