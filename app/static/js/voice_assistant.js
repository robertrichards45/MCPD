(function () {
  'use strict';

  var SPEEDS = { normal: 0.86, fast: 1.05, veryfast: 1.18 };
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
