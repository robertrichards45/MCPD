(function () {
  'use strict';

  // Don't inject on mobile-foundation pages (field incident shell)
  if (document.body.classList.contains('mobile-foundation')) return;

  var CSRF_TOKEN = '';
  var history = [];
  var isOpen = false;
  var isListening = false;
  var isThinking = false;
  var audioQueue = null;

  // ── Build DOM ──────────────────────────────────────────────────────────────

  function buildUI() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    CSRF_TOKEN = meta ? (meta.getAttribute('content') || '') : '';

    // Floating button
    var btn = document.createElement('button');
    btn.id = 'ai-fab';
    btn.className = 'ai-fab';
    btn.setAttribute('aria-label', 'Open MCPD AI Assistant');
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
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
      '    <span class="ai-panel-dot"></span>',
      '    <strong>MCPD Assistant</strong>',
      '  </div>',
      '  <div class="ai-panel-actions">',
      '    <button id="ai-clear-btn" class="ai-icon-btn" title="Clear conversation" aria-label="Clear conversation">',
      '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>',
      '    </button>',
      '    <button id="ai-close-btn" class="ai-icon-btn" title="Close" aria-label="Close assistant">',
      '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
      '    </button>',
      '  </div>',
      '</div>',
      '<div id="ai-messages" class="ai-messages" aria-live="polite"></div>',
      '<div class="ai-input-row">',
      '  <button id="ai-mic-btn" class="ai-mic-btn" title="Hold to speak" aria-label="Voice input">',
      '    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>',
      '  </button>',
      '  <input id="ai-text-input" class="ai-text-input" type="text" placeholder="Ask anything..." autocomplete="off" />',
      '  <button id="ai-send-btn" class="ai-send-btn" aria-label="Send">',
      '    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
      '  </button>',
      '</div>',
    ].join('\n');
    document.body.appendChild(panel);

    // Wire events
    btn.addEventListener('click', togglePanel);
    document.getElementById('ai-close-btn').addEventListener('click', closePanel);
    document.getElementById('ai-clear-btn').addEventListener('click', clearHistory);
    document.getElementById('ai-send-btn').addEventListener('click', sendText);
    document.getElementById('ai-text-input').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(); }
    });
    setupMic();

    // Show welcome after slight delay
    setTimeout(function () {
      appendMessage('assistant', 'Hello. I\'m the MCPD AI Assistant. Ask me about law, policy, report writing, or any field question.');
    }, 300);
  }

  // ── Panel open/close ───────────────────────────────────────────────────────

  function togglePanel() {
    isOpen ? closePanel() : openPanel();
  }

  function openPanel() {
    isOpen = true;
    var panel = document.getElementById('ai-panel');
    var btn = document.getElementById('ai-fab');
    panel.classList.remove('ai-panel-hidden');
    panel.classList.add('ai-panel-open');
    btn.classList.add('ai-fab-active');
    document.getElementById('ai-text-input').focus();
  }

  function closePanel() {
    isOpen = false;
    var panel = document.getElementById('ai-panel');
    var btn = document.getElementById('ai-fab');
    panel.classList.remove('ai-panel-open');
    panel.classList.add('ai-panel-hidden');
    btn.classList.remove('ai-fab-active');
  }

  function clearHistory() {
    history = [];
    var msgs = document.getElementById('ai-messages');
    msgs.innerHTML = '';
    appendMessage('assistant', 'Conversation cleared. How can I help you?');
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
    var msgs = document.getElementById('ai-messages');
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
    var text = (input.value || '').trim();
    if (!text || isThinking) return;
    input.value = '';
    submitMessage(text);
  }

  function submitMessage(text) {
    if (!isOpen) openPanel();
    appendMessage('user', text);
    isThinking = true;
    showTyping();

    var payload = { message: text, history: history.slice() };

    fetch('/api/assistant/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        hideTyping();
        isThinking = false;
        var reply = (data && data.reply) ? data.reply : 'Sorry, I could not get a response.';
        appendMessage('assistant', reply);
        history.push({ role: 'user', content: text });
        history.push({ role: 'assistant', content: reply });
        if (history.length > 20) history = history.slice(history.length - 20);
        speakText(reply);
      })
      .catch(function () {
        hideTyping();
        isThinking = false;
        appendMessage('assistant', 'Connection error. Please try again.');
      });
  }

  // ── TTS ────────────────────────────────────────────────────────────────────

  function speakText(text) {
    if (!text) return;
    // Stop any prior audio
    if (audioQueue) {
      try { audioQueue.pause(); } catch (e) {}
      audioQueue = null;
    }

    fetch('/api/assistant/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error('tts-unavailable');
        return r.blob();
      })
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        var audio = new Audio(url);
        audioQueue = audio;
        audio.onended = function () { URL.revokeObjectURL(url); audioQueue = null; };
        audio.play().catch(function () {});
      })
      .catch(function () {
        // Fallback to browser speechSynthesis
        browserSpeak(text);
      });
  }

  function browserSpeak(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    var utt = new SpeechSynthesisUtterance(text);
    utt.rate = 1.0;
    utt.pitch = 1.0;

    // Prefer a natural-sounding English voice if available
    var voices = window.speechSynthesis.getVoices();
    var preferred = voices.find(function (v) {
      return /en[-_]US/i.test(v.lang) && /natural|samantha|alex|karen|daniel|zira/i.test(v.name);
    }) || voices.find(function (v) {
      return /en/i.test(v.lang);
    });
    if (preferred) utt.voice = preferred;
    window.speechSynthesis.speak(utt);
  }

  // ── Voice input ────────────────────────────────────────────────────────────

  function setupMic() {
    var micBtn = document.getElementById('ai-mic-btn');
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      micBtn.style.display = 'none';
      return;
    }

    var recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = function (event) {
      var transcript = event.results[0][0].transcript;
      var input = document.getElementById('ai-text-input');
      input.value = transcript;
      stopListening();
      submitMessage(transcript);
    };

    recognition.onerror = function () { stopListening(); };
    recognition.onend = function () { if (isListening) stopListening(); };

    micBtn.addEventListener('mousedown', function (e) { e.preventDefault(); startListening(recognition); });
    micBtn.addEventListener('touchstart', function (e) { e.preventDefault(); startListening(recognition); }, { passive: false });
    micBtn.addEventListener('mouseup', function () { stopRecognition(recognition); });
    micBtn.addEventListener('touchend', function () { stopRecognition(recognition); });
    micBtn.addEventListener('click', function (e) {
      // Toggle on desktop click (in case mousedown/mouseup already fired submit)
      if (!isListening) startListening(recognition);
    });
  }

  function startListening(recognition) {
    if (isListening) return;
    isListening = true;
    document.getElementById('ai-mic-btn').classList.add('ai-mic-active');
    try { recognition.start(); } catch (e) {}
  }

  function stopListening() {
    isListening = false;
    var btn = document.getElementById('ai-mic-btn');
    if (btn) btn.classList.remove('ai-mic-active');
  }

  function stopRecognition(recognition) {
    if (!isListening) return;
    try { recognition.stop(); } catch (e) {}
  }

  // ── Init ───────────────────────────────────────────────────────────────────

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', buildUI);
  } else {
    buildUI();
  }
}());
