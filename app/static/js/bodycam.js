(function () {
  'use strict';

  var preview = document.getElementById('bodycam-preview');
  var startCameraBtn = document.getElementById('bodycam-start-camera');
  var recordBtn = document.getElementById('bodycam-record');
  var stopBtn = document.getElementById('bodycam-stop');
  var saveBtn = document.getElementById('bodycam-save');
  var statusEl = document.getElementById('bodycam-status');
  var transcriptEl = document.getElementById('bodycam-transcript');
  var transcriptMode = document.getElementById('bodycam-transcript-mode');
  var openSaved = document.getElementById('bodycam-open-saved');

  if (!preview || !startCameraBtn || !recordBtn || !stopBtn || !saveBtn) return;

  var stream = null;
  var recorder = null;
  var chunks = [];
  var startedAt = null;
  var durationSeconds = 0;
  var recognition = null;
  var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  function setTranscriptMode(text) {
    if (transcriptMode) transcriptMode.textContent = text;
  }

  function getValue(id) {
    var el = document.getElementById(id);
    return el ? el.value || '' : '';
  }

  function startTranscript() {
    if (!SpeechRecognition) {
      setTranscriptMode('Transcription not supported on this browser.');
      return;
    }
    try {
      recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';
      recognition.onresult = function (event) {
        var finalText = '';
        var interimText = '';
        for (var i = event.resultIndex; i < event.results.length; i += 1) {
          var text = event.results[i][0].transcript;
          if (event.results[i].isFinal) finalText += text + ' ';
          else interimText += text;
        }
        if (finalText && transcriptEl) {
          transcriptEl.value = (transcriptEl.value + ' ' + finalText).replace(/\s+/g, ' ').trim();
        }
        setTranscriptMode(interimText ? 'Listening...' : 'Transcribing');
      };
      recognition.onerror = function () {
        setTranscriptMode('Transcription paused. Video recording continues.');
      };
      recognition.start();
      setTranscriptMode('Transcribing');
    } catch (e) {
      setTranscriptMode('Transcription unavailable. Video recording continues.');
    }
  }

  function stopTranscript() {
    if (recognition) {
      try { recognition.stop(); } catch (e) {}
      recognition = null;
    }
  }

  async function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setStatus('Camera recording is not supported on this browser. Use a supported mobile browser over HTTPS.');
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: true,
      });
      preview.srcObject = stream;
      await preview.play();
      recordBtn.disabled = false;
      startCameraBtn.disabled = true;
      setStatus('Camera ready. Turn on Do Not Disturb / Focus before recording.');
      setTranscriptMode(SpeechRecognition ? 'Transcript ready' : 'Transcription not supported on this browser.');
    } catch (e) {
      setStatus('Camera permission denied or unavailable. Check browser permissions and HTTPS.');
    }
  }

  function startRecording() {
    if (!stream) return;
    chunks = [];
    var mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus') ? 'video/webm;codecs=vp8,opus' : 'video/webm';
    try {
      recorder = new MediaRecorder(stream, { mimeType: mimeType });
    } catch (e) {
      setStatus('Recording is not supported on this browser.');
      return;
    }
    recorder.ondataavailable = function (event) {
      if (event.data && event.data.size > 0) chunks.push(event.data);
    };
    recorder.onstop = function () {
      durationSeconds = startedAt ? Math.max(1, Math.round((Date.now() - startedAt) / 1000)) : 0;
      saveBtn.disabled = !chunks.length;
      setStatus(chunks.length ? 'Recording stopped. Review transcript, then save footage.' : 'No video data was recorded.');
    };
    recorder.start(1000);
    startedAt = Date.now();
    recordBtn.disabled = true;
    stopBtn.disabled = false;
    saveBtn.disabled = true;
    setStatus('Recording active.');
    startTranscript();
  }

  function stopRecording() {
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    stopTranscript();
    stopBtn.disabled = true;
    recordBtn.disabled = false;
  }

  async function saveRecording() {
    if (!chunks.length) {
      setStatus('Record video before saving.');
      return;
    }
    saveBtn.disabled = true;
    setStatus('Saving footage...');
    var blob = new Blob(chunks, { type: 'video/webm' });
    var form = new FormData();
    form.append('video', blob, 'bodycam-recording.webm');
    form.append('title', getValue('bodycam-title'));
    form.append('incident_number', getValue('bodycam-incident'));
    form.append('location', getValue('bodycam-location'));
    form.append('notes', getValue('bodycam-notes'));
    form.append('duration_seconds', String(durationSeconds || 0));
    form.append('transcript_text', transcriptEl ? transcriptEl.value : '');
    try {
      var response = await fetch('/bodycam/upload', { method: 'POST', body: form });
      var data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Save failed.');
      setStatus('Footage saved.');
      if (openSaved) {
        openSaved.hidden = false;
        openSaved.href = data.detailUrl || openSaved.href;
      }
    } catch (e) {
      setStatus(e.message || 'Could not save footage.');
      saveBtn.disabled = false;
    }
  }

  startCameraBtn.addEventListener('click', startCamera);
  recordBtn.addEventListener('click', startRecording);
  stopBtn.addEventListener('click', stopRecording);
  saveBtn.addEventListener('click', saveRecording);
  window.addEventListener('pagehide', function () {
    stopTranscript();
    if (stream) stream.getTracks().forEach(function (track) { track.stop(); });
  });
}());
