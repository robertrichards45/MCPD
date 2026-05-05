(function () {
  'use strict';

  var VOICE_STORAGE_KEY = 'mcpd.assistant.voice';

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
      utt.rate = 1.32;
      utt.pitch = 0.78;
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
          if (payload.voice === 'dispatcher') {
            speakRadio('Copy. Stand by.');
          }
        }
      } catch (e) {}
      return originalFetch.apply(this, arguments);
    }

    patchedFetch.mcpdDispatcherPatch = true;
    window.fetch = patchedFetch;
  }

  document.addEventListener('click', function () {
    setTimeout(addDispatcherVoiceCard, 50);
  });
  window.addEventListener('load', function () {
    patchAssistantFetch();
    addDispatcherVoiceCard();
    setInterval(addDispatcherVoiceCard, 1500);
  });
}());
