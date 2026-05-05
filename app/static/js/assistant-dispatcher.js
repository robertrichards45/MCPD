(function () {
  'use strict';

  var VOICE_STORAGE_KEY = 'mcpd.assistant.voice';

  function getSavedVoice() {
    try { return localStorage.getItem(VOICE_STORAGE_KEY) || 'coral'; } catch (e) { return 'coral'; }
  }

  function saveVoice(value) {
    try { localStorage.setItem(VOICE_STORAGE_KEY, value); } catch (e) {}
  }

  function radioPreview() {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    var utt = new SpeechSynthesisUtterance('Dispatcher mode selected. Standing by.');
    utt.rate = 1.32;
    utt.pitch = 0.78;
    window.speechSynthesis.speak(utt);
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
      radioPreview();
    });
    list.insertBefore(card, list.firstChild);
  }

  document.addEventListener('click', function () {
    setTimeout(addDispatcherVoiceCard, 50);
  });
  window.addEventListener('load', function () {
    addDispatcherVoiceCard();
    setInterval(addDispatcherVoiceCard, 1500);
  });
}());
