(function () {
  'use strict';

  var SPEEDS = { normal: 1.0, fast: 1.18, veryfast: 1.32 };
  var STORAGE_ENABLED = 'mcpd.voice.enabled';
  var STORAGE_SPEED = 'mcpd.voice.speed';
  var queue = [];
  var speaking = false;
  var lastFullText = '';
  var lastSpokenText = '';
  var processingTimer = null;

  function supportsVoice() {
    return !!(window.speechSynthesis && window.SpeechSynthesisUtterance);
  }

  function getVoiceEnabled() {
    try {
      var saved = localStorage.getItem(STORAGE_ENABLED);
      return saved === null ? true : saved === '1';
    } catch (e) {
      return true;
    }
  }

  function toggleVoice(enabled) {
    var next = !!enabled;
    try { localStorage.setItem(STORAGE_ENABLED, next ? '1' : '0'); } catch (e) {}
    if (!next) stopVoice();
    return next;
  }

  function getVoiceSpeed() {
    try { return localStorage.getItem(STORAGE_SPEED) || 'normal'; } catch (e) { return 'normal'; }
  }

  function setVoiceSpeed(speed) {
    var next = SPEEDS[speed] ? speed : 'normal';
    try { localStorage.setItem(STORAGE_SPEED, next); } catch (e) {}
    return next;
  }

  function currentRate() {
    return SPEEDS[getVoiceSpeed()] || SPEEDS.normal;
  }

  function startVoiceStatus(text) {
    var label = document.getElementById('ai-status-label');
    if (label) label.textContent = text || '';
  }

  function unsupportedMessage() {
    var message = 'Voice playback is not supported on this device/browser.';
    var el = document.getElementById('ai-tts-status');
    if (el) el.textContent = message;
    startVoiceStatus(message);
    return message;
  }

  function splitSentences(text) {
    var clean = String(text || '').replace(/\s+/g, ' ').trim();
    if (!clean) return [];
    return (clean.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [clean]).map(function (part) {
      return part.trim();
    }).filter(Boolean);
  }

  function summaryText(text) {
    var sentences = splitSentences(text);
    if (!sentences.length) return '';
    var summary = sentences[0];
    if (summary.length < 120 && sentences[1]) summary += ' ' + sentences[1];
    if (summary.length > 260) summary = summary.slice(0, 257).replace(/\s+\S*$/, '') + '...';
    return summary;
  }

  function stopVoice() {
    queue = [];
    speaking = false;
    if (processingTimer) {
      clearTimeout(processingTimer);
      processingTimer = null;
    }
    if (supportsVoice()) window.speechSynthesis.cancel();
  }

  function speakQueued(text, options) {
    options = options || {};
    var clean = String(text || '').trim();
    if (!clean || !getVoiceEnabled()) return;
    if (!supportsVoice()) {
      unsupportedMessage();
      return;
    }
    if (options.cancel) stopVoice();
    queue.push(clean);
    lastSpokenText = clean;
    drainQueue();
  }

  function drainQueue() {
    if (speaking || !queue.length || !supportsVoice()) return;
    var sentence = queue.shift();
    speaking = true;
    var utterance = new SpeechSynthesisUtterance(sentence);
    utterance.rate = currentRate();
    utterance.pitch = 1;
    utterance.onend = function () {
      speaking = false;
      drainQueue();
    };
    utterance.onerror = function () {
      speaking = false;
      drainQueue();
    };
    window.speechSynthesis.speak(utterance);
  }

  function speakSentences(text, options) {
    var sentences = splitSentences(text);
    if (!sentences.length) return;
    if (options && options.cancel) stopVoice();
    sentences.forEach(function (sentence) { speakQueued(sentence, { cancel: false }); });
  }

  function speakProcessingIfDelayed(delayMs) {
    if (processingTimer) clearTimeout(processingTimer);
    processingTimer = setTimeout(function () {
      speakQueued('Processing request.', { cancel: false });
    }, delayMs || 1000);
    return processingTimer;
  }

  function cancelProcessing(timer) {
    if (timer) clearTimeout(timer);
    if (processingTimer) {
      clearTimeout(processingTimer);
      processingTimer = null;
    }
  }

  function speakStreamingSentence(sentence) {
    speakQueued(sentence, { cancel: false });
  }

  function speakSummary(text, onDone) {
    lastFullText = String(text || '').trim();
    var shortText = summaryText(lastFullText);
    if (!shortText) {
      if (onDone) onDone();
      return;
    }
    speakSentences(shortText, { cancel: true });
    if (onDone) {
      setTimeout(onDone, Math.min(6000, Math.max(900, shortText.length * 35)));
    }
  }

  function speakFull(text) {
    var full = String(text || lastFullText || '').trim();
    if (!full) return;
    lastFullText = full;
    speakSentences(full, { cancel: true });
  }

  function replayLastVoice() {
    var text = lastSpokenText || summaryText(lastFullText);
    if (text) speakSentences(text, { cancel: true });
  }

  window.MCPDVoiceAssistant = {
    startVoiceStatus: startVoiceStatus,
    speakProcessingIfDelayed: speakProcessingIfDelayed,
    cancelProcessing: cancelProcessing,
    speakStreamingSentence: speakStreamingSentence,
    speakSummary: speakSummary,
    speakFull: speakFull,
    stopVoice: stopVoice,
    replayLastVoice: replayLastVoice,
    setVoiceSpeed: setVoiceSpeed,
    getVoiceSpeed: getVoiceSpeed,
    getVoiceRate: currentRate,
    toggleVoice: toggleVoice,
    getVoiceEnabled: getVoiceEnabled,
    isVoiceSupported: supportsVoice,
    unsupportedMessage: unsupportedMessage,
    splitSentences: splitSentences,
  };
}());
