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
  var DEFAULT_VOICE     = 'coral';

  function getSavedVoice() {
    try { return localStorage.getItem(VOICE_STORAGE_KEY) || DEFAULT_VOICE; } catch (e) { return DEFAULT_VOICE; }
  }
  function saveVoice(v) {
    try { localStorage.setItem(VOICE_STORAGE_KEY, v); } catch (e) {}
  }

  // ── State ──────────────────────────────────────────────────────────────────
  var history      = [];
  var isOpen       = false;
  var isListening  = false;
  var isThinking   = false;
  var voiceMode    = false;
  var showSettings = false;
  var audioQueue   = null;
  var recognition  = null;
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
      '  <div class="ai-settings-subtitle">All voices use OpenAI high-quality TTS</div>',
      '  <div id="ai-voice-list" class="ai-voice-list"></div>',
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
    document.getElementById('ai-text-input').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(); }
    });
    document.getElementById('ai-text-input').addEventListener('input', function () {
      if (isListening) stopListening();
      voiceMode = false;
      updateUI();
    });

    setupMic();

    setTimeout(function () {
      var v = VOICES.find(function (x) { return x.id === getSavedVoice(); }) || VOICES[0];
      appendMessage('assistant', 'Hello. I\'m the MCPD AI Assistant, speaking with the ' + v.label + ' voice. Tap the mic or type to get started.');
    }, 300);
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
        var url = URL.createObjectURL(blob);
        var audio = new Audio(url);
        audioQueue = audio;
        audio.onended = function () { URL.revokeObjectURL(url); audioQueue = null; };
        audio.play().catch(function () {});
      })
      .catch(function () {
        browserSpeak(previewText, null);
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

  // ── Send ───────────────────────────────────────────────────────────────────

  function sendText() {
    var input = document.getElementById('ai-text-input');
    var text  = (input.value || '').trim();
    if (!text || isThinking) return;
    input.value = '';
    voiceMode = false;
    submitMessage(text);
  }

  function submitMessage(text) {
    if (!isOpen) openPanel();
    stopListening();
    appendMessage('user', text);
    isThinking = true;
    updateUI();
    showTyping();

    fetch('/api/assistant/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: history.slice() }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        hideTyping();
        isThinking = false;
        var reply = (data && data.reply) ? data.reply : 'Sorry, I could not get a response.';
        if (data && data.mode === 'local_fallback') {
          var label = document.getElementById('ai-status-label');
          if (label) label.textContent = 'Local assist';
        }
        appendMessage('assistant', reply);
        history.push({ role: 'user',      content: text  });
        history.push({ role: 'assistant', content: reply });
        if (history.length > 20) history = history.slice(history.length - 20);
        updateUI();
        speakText(reply);
      })
      .catch(function () {
        hideTyping();
        isThinking = false;
        updateUI();
        appendMessage('assistant', 'Connection error. Please try again.');
        if (voiceMode) scheduleAutoListen();
      });
  }

  // ── TTS ────────────────────────────────────────────────────────────────────

  function speakText(text) {
    if (!text) { if (voiceMode) scheduleAutoListen(); return; }
    stopAudio();

    fetch('/api/assistant/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text, voice: getSavedVoice() }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error('tts-unavailable');
        return r.blob();
      })
      .then(function (blob) {
        var url   = URL.createObjectURL(blob);
        var audio = new Audio(url);
        audioQueue = audio;
        audio.onended = function () {
          URL.revokeObjectURL(url);
          audioQueue = null;
          if (voiceMode) scheduleAutoListen();
        };
        audio.onerror = function () { audioQueue = null; if (voiceMode) scheduleAutoListen(); };
        audio.play().catch(function () { if (voiceMode) scheduleAutoListen(); });
      })
      .catch(function () {
        browserSpeak(text, function () { if (voiceMode) scheduleAutoListen(); });
      });
  }

  function stopAudio() {
    if (audioQueue) { try { audioQueue.pause(); } catch (e) {} audioQueue = null; }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  }

  function browserSpeak(text, onDone) {
    if (!window.speechSynthesis) { if (onDone) onDone(); return; }
    window.speechSynthesis.cancel();
    var utt = new SpeechSynthesisUtterance(text);
    utt.rate = 1.0; utt.pitch = 1.0;
    var voices = window.speechSynthesis.getVoices();
    var preferred = voices.find(function (v) {
      return /en[-_]US/i.test(v.lang) && /natural|samantha|alex|karen|daniel|zira/i.test(v.name);
    }) || voices.find(function (v) { return /en/i.test(v.lang); });
    if (preferred) utt.voice = preferred;
    utt.onend   = function () { if (onDone) onDone(); };
    utt.onerror = function () { if (onDone) onDone(); };
    window.speechSynthesis.speak(utt);
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
      if (transcript) submitMessage(transcript);
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
