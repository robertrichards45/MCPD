(function () {
  'use strict';

  if (document.body.classList.contains('landing')) return;

  var Voice = window.MCPDVoiceAssistant || {};
  var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  var HISTORY_STORAGE_KEY = 'mcpd.assistant.history';
  var history = loadHistory();
  var isOpen = false;
  var isListening = false;
  var isThinking = false;
  var voiceMode = false;
  var recognition = null;
  var formInterview = { active: false, fields: [], index: 0 };

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

  function buildUI() {
    if (document.getElementById('ai-fab')) return;

    var btn = document.createElement('button');
    btn.id = 'ai-fab';
    btn.className = 'ai-fab';
    btn.setAttribute('aria-label', 'Open MCPD AI Assistant');
    btn.innerHTML = '<span class="ai-fab-symbol">AI</span>';
    document.body.appendChild(btn);

    var panel = document.createElement('div');
    panel.id = 'ai-panel';
    panel.className = 'ai-panel ai-panel-hidden';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'MCPD AI Assistant');
    panel.innerHTML = [
      '<div class="ai-panel-header">',
      '  <div class="ai-panel-title"><span class="ai-panel-dot" id="ai-status-dot"></span><strong>MCPD Assistant</strong><span id="ai-status-label" class="ai-status-label"></span></div>',
      '  <div class="ai-panel-actions">',
      '    <button id="ai-settings-btn" class="ai-icon-btn" title="Voice controls" aria-label="Voice controls">Voice</button>',
      '    <button id="ai-clear-btn" class="ai-icon-btn" title="Clear conversation" aria-label="Clear conversation">Clear</button>',
      '    <button id="ai-close-btn" class="ai-icon-btn" title="Close" aria-label="Close assistant">X</button>',
      '  </div>',
      '</div>',
      '<div id="ai-settings-panel" class="ai-settings-panel ai-settings-hidden">',
      '  <div class="ai-settings-title">Voice Controls</div>',
      '  <div id="ai-tts-status" class="ai-settings-subtitle">Instant browser voice active.</div>',
      '  <div class="ai-voice-controls">',
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
      '  <p class="ai-settings-subtitle">The assistant speaks a short summary first. Use Read Full Response when needed.</p>',
      '</div>',
      '<div id="ai-messages" class="ai-messages" aria-live="polite"></div>',
      '<div class="ai-input-row">',
      '  <button id="ai-mic-btn" class="ai-mic-btn" title="Click to speak" aria-label="Voice input">Mic</button>',
      '  <input id="ai-text-input" class="ai-text-input" type="text" placeholder="Ask MCPD Assistant..." autocomplete="off" />',
      '  <button id="ai-send-btn" class="ai-send-btn" aria-label="Send">Send</button>',
      '</div>',
    ].join('\n');
    document.body.appendChild(panel);

    btn.addEventListener('click', onFabClick);
    document.getElementById('ai-close-btn').addEventListener('click', closePanel);
    document.getElementById('ai-clear-btn').addEventListener('click', clearHistory);
    document.getElementById('ai-send-btn').addEventListener('click', sendText);
    document.getElementById('ai-settings-btn').addEventListener('click', toggleSettings);
    document.getElementById('ai-stop-voice-btn').addEventListener('click', stopAudio);
    document.getElementById('ai-replay-voice-btn').addEventListener('click', function () {
      if (Voice.replayLastVoice) Voice.replayLastVoice();
    });
    document.getElementById('ai-voice-toggle-btn').addEventListener('click', function () {
      var next = Voice.getVoiceEnabled ? !Voice.getVoiceEnabled() : false;
      if (Voice.toggleVoice) Voice.toggleVoice(next);
      syncVoiceControls();
    });
    document.getElementById('ai-voice-speed').addEventListener('change', function (event) {
      if (Voice.setVoiceSpeed) Voice.setVoiceSpeed(event.target.value);
    });
    document.getElementById('ai-text-input').addEventListener('keydown', function (event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendText();
      }
    });

    setupMic();
    syncVoiceControls();
    if (Voice.isVoiceSupported && !Voice.isVoiceSupported()) {
      setTTSStatus('unsupported');
    }
    appendMessage('assistant', 'MCPD Assistant is ready. Tap the mic or type what you need.');
  }

  function onFabClick() {
    if (!isOpen) {
      openPanel();
      return;
    }
    if (isListening) {
      voiceMode = false;
      stopListening();
    } else {
      closePanel();
    }
  }

  function openPanel() {
    isOpen = true;
    document.getElementById('ai-panel').classList.remove('ai-panel-hidden');
    document.getElementById('ai-panel').classList.add('ai-panel-open');
    document.getElementById('ai-fab').classList.add('ai-fab-active');
    updateUI();
  }

  function closePanel() {
    voiceMode = false;
    stopListening();
    stopAudio();
    isOpen = false;
    document.getElementById('ai-panel').classList.remove('ai-panel-open');
    document.getElementById('ai-panel').classList.add('ai-panel-hidden');
    document.getElementById('ai-fab').classList.remove('ai-fab-active', 'ai-fab-listening');
    updateUI();
  }

  function clearHistory() {
    history = [];
    saveHistory();
    document.getElementById('ai-messages').innerHTML = '';
    appendMessage('assistant', 'Conversation cleared. How can I help?');
  }

  function toggleSettings() {
    var panel = document.getElementById('ai-settings-panel');
    if (!panel) return;
    panel.classList.toggle('ai-settings-hidden');
    syncVoiceControls();
  }

  function syncVoiceControls() {
    var toggle = document.getElementById('ai-voice-toggle-btn');
    var speed = document.getElementById('ai-voice-speed');
    var enabled = Voice.getVoiceEnabled ? Voice.getVoiceEnabled() : true;
    if (toggle) toggle.textContent = enabled ? 'Voice On' : 'Voice Off';
    if (speed && Voice.getVoiceSpeed) speed.value = Voice.getVoiceSpeed();
  }

  function setTTSStatus(mode) {
    var el = document.getElementById('ai-tts-status');
    if (!el) return;
    if (mode === 'unsupported') {
      el.textContent = 'Voice playback is not supported on this device/browser.';
    } else {
      el.textContent = 'Instant browser voice active.';
    }
  }

  function updateUI() {
    var fab = document.getElementById('ai-fab');
    var dot = document.getElementById('ai-status-dot');
    var label = document.getElementById('ai-status-label');
    var micBtn = document.getElementById('ai-mic-btn');
    if (!fab) return;
    if (isListening) {
      fab.classList.add('ai-fab-listening');
      if (dot) dot.classList.add('ai-dot-listening');
      if (label) label.textContent = 'Listening...';
      if (micBtn) micBtn.classList.add('ai-mic-active');
      if (Voice.startVoiceStatus) Voice.startVoiceStatus('Listening...');
    } else if (isThinking) {
      fab.classList.remove('ai-fab-listening');
      if (dot) dot.classList.remove('ai-dot-listening');
      if (label) label.textContent = 'Thinking...';
      if (micBtn) micBtn.classList.remove('ai-mic-active');
      if (Voice.startVoiceStatus) Voice.startVoiceStatus('Thinking...');
    } else {
      fab.classList.remove('ai-fab-listening');
      if (dot) dot.classList.remove('ai-dot-listening');
      if (label) label.textContent = voiceMode ? 'Voice on' : '';
      if (micBtn) micBtn.classList.remove('ai-mic-active');
    }
  }

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
    var control = document.createElement('button');
    control.className = 'ai-read-full-btn';
    control.type = 'button';
    control.textContent = 'Read Full Response';
    control.addEventListener('click', function () {
      if (Voice.speakFull) Voice.speakFull(text);
      else browserSpeak(text);
    });
    bubble.appendChild(document.createElement('br'));
    bubble.appendChild(control);
  }

  function getPageContext() {
    var formHeading = document.querySelector('.forms-fill-page h2, .form-title, h1, h2');
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
    return Array.prototype.slice.call(document.querySelectorAll('#form-fill-shell [name^="field_"], form [name^="field_"]'))
      .filter(function (el) {
        if (!el.name || seen[el.name] || el.disabled || el.readOnly || el.type === 'hidden') return false;
        seen[el.name] = true;
        return true;
      })
      .map(function (el) {
        var block = el.closest('.form-field-block, .field-row, .form-group') || el.parentElement;
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
    var bubble = appendMessage('assistant', text);
    speakText(text);
    return bubble;
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
    speakAssistantLine('The visible form questions are complete. Review the form, then preview, download, email, or save it.');
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
    if (!field) {
      formInterview.active = false;
      return false;
    }
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
    if (!document.querySelector('#form-fill-shell, form [name^="field_"]')) return false;
    if (!/fill|complete|walk me through|ask me questions|form assistant|help me/i.test(text || '')) return false;
    appendMessage('user', text);
    startFormInterview();
    return true;
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
    return normalizedCommandText(el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || el.value || '');
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

  function sendText() {
    var input = document.getElementById('ai-text-input');
    var text = (input.value || '').trim();
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
    appendMessage('user', text);
    isThinking = true;
    updateUI();
    var thinkingBubble = appendMessage('assistant', 'Thinking...');
    var processingTimer = Voice.speakProcessingIfDelayed ? Voice.speakProcessingIfDelayed(1000) : setTimeout(function () {
      browserSpeak('Processing request.');
    }, 1000);

    fetch('/api/assistant/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: history.slice(), page: getPageContext() }),
    })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        if (Voice.cancelProcessing) Voice.cancelProcessing(processingTimer);
        else clearTimeout(processingTimer);
        isThinking = false;
        if (Voice.startVoiceStatus) Voice.startVoiceStatus('Answering...');
        var reply = (data && data.reply) ? data.reply : 'Sorry, I could not get a response.';
        updateMessage(thinkingBubble, reply);
        addReadFullControl(thinkingBubble, reply);
        speakText(reply);
        history.push({ role: 'user', content: text });
        history.push({ role: 'assistant', content: reply });
        if (history.length > 20) history = history.slice(history.length - 20);
        saveHistory();
        updateUI();
        applyAssistantAction(data && data.action);
      })
      .catch(function () {
        if (Voice.cancelProcessing) Voice.cancelProcessing(processingTimer);
        else clearTimeout(processingTimer);
        isThinking = false;
        updateUI();
        updateMessage(thinkingBubble, 'Connection error. Please try again.');
        speakText('Connection error. Please try again.');
      });
  }

  function applyAssistantAction(action) {
    if (!action || !action.type) return;
    if (action.type === 'form_interview') {
      startFormInterview();
      return;
    }
    if (action.type === 'navigate' && action.url) {
      setTimeout(function () { window.location.assign(action.url); }, 1200);
    }
  }

  function speakText(text) {
    if (!text) {
      if (voiceMode) scheduleAutoListen();
      return;
    }
    setTTSStatus(Voice.isVoiceSupported && !Voice.isVoiceSupported() ? 'unsupported' : 'instant');
    if (Voice.speakSummary) {
      Voice.speakSummary(text, function () {
        if (voiceMode) scheduleAutoListen();
      });
      return;
    }
    browserSpeak(text, function () {
      if (voiceMode) scheduleAutoListen();
    });
  }

  function stopAudio() {
    if (Voice.stopVoice) Voice.stopVoice();
    else if (window.speechSynthesis) window.speechSynthesis.cancel();
  }

  function browserSpeak(text, onDone) {
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) {
      setTTSStatus('unsupported');
      if (onDone) onDone();
      return;
    }
    window.speechSynthesis.cancel();
    var parts = (String(text || '').match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [text]).map(function (part) { return part.trim(); }).filter(Boolean);
    var index = 0;
    function next() {
      if (index >= parts.length) {
        if (onDone) onDone();
        return;
      }
      var utt = new SpeechSynthesisUtterance(parts[index++]);
      utt.rate = 1.4;
      utt.onend = next;
      utt.onerror = next;
      window.speechSynthesis.speak(utt);
    }
    next();
  }

  function scheduleAutoListen() {
    if (!voiceMode || !isOpen || isThinking) return;
    setTimeout(function () {
      if (voiceMode && isOpen && !isThinking && !isListening) startListening();
    }, 700);
  }

  function setupMic() {
    var micBtn = document.getElementById('ai-mic-btn');
    if (!SpeechRecognition) {
      micBtn.addEventListener('click', function () {
        speakAssistantLine('Voice input is not supported on this device/browser.');
      });
      return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = function (event) {
      var transcript = (event.results[0][0].transcript || '').trim();
      isListening = false;
      updateUI();
      if (!transcript) return;
      if (formInterview.active) handleFormInterviewAnswer(transcript);
      else if (maybeStartLocalFormInterview(transcript)) return;
      else if (tryDirectInterfaceCommand(transcript)) return;
      else submitMessage(transcript);
    };
    recognition.onerror = function (event) {
      isListening = false;
      updateUI();
      if (voiceMode && event.error === 'no-speech') scheduleAutoListen();
    };
    recognition.onend = function () {
      isListening = false;
      updateUI();
    };

    micBtn.addEventListener('click', function () {
      if (isListening) {
        voiceMode = false;
        stopListening();
      } else {
        voiceMode = true;
        startListening();
      }
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', buildUI);
  } else {
    buildUI();
  }
}());
