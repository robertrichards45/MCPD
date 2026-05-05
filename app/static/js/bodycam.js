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
  var transcriptActive = false;
  var transcriptManuallyEdited = false;

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
      setTranscriptMode('Live transcription not supported here. Type or edit transcript notes manually.');
      return;
    }
    try {
      recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';
      transcriptActive = true;
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
          transcriptManuallyEdited = true;
        }
        setTranscriptMode(interimText ? 'Listening...' : 'Transcribing');
      };
      recognition.onerror = function (event) {
        var reason = event && event.error ? event.error : 'unavailable';
        setTranscriptMode('Transcription paused (' + reason + '). Video recording continues; type notes manually if needed.');
      };
      recognition.onend = function () {
        if (!transcriptActive) return;
        try {
          recognition.start();
        } catch (e) {
          setTranscriptMode('Transcription paused. Video recording continues; type notes manually if needed.');
        }
      };
      recognition.start();
      setTranscriptMode('Transcribing');
    } catch (e) {
      setTranscriptMode('Transcription unavailable. Video recording continues; type notes manually if needed.');
    }
  }

  function stopTranscript() {
    transcriptActive = false;
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
      setTranscriptMode(SpeechRecognition ? 'Live transcript ready. Verify before saving.' : 'Live transcription not supported here. Manual transcript notes are still supported.');
    } catch (e) {
      setStatus('Camera permission denied or unavailable. Check browser permissions and HTTPS.');
    }
  }

  function startRecording() {
    if (!stream) return;
    chunks = [];
    if (!window.MediaRecorder) {
      setStatus('Recording is not supported on this browser. Try Android Chrome, desktop Chrome/Edge, or use another approved capture method.');
      return;
    }
    var supportsType = typeof MediaRecorder.isTypeSupported === 'function';
    var mimeType = supportsType && MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus') ? 'video/webm;codecs=vp8,opus' : 'video/webm';
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
      setStatus(chunks.length ? 'Recording stopped. Review or type transcript notes, then save footage.' : 'No video data was recorded.');
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
    if (transcriptEl && !transcriptEl.value.trim()) {
      setTranscriptMode('No transcript text entered. Video will save without transcript unless you add notes.');
    }
    setStatus('Saving footage and transcript notes...');
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
      setTranscriptMode((transcriptEl && transcriptEl.value.trim()) ? 'Transcript saved with footage.' : 'Footage saved without transcript text.');
      if (openSaved) {
        openSaved.hidden = false;
        openSaved.href = data.detailUrl || openSaved.href;
      }
    } catch (e) {
      setStatus(e.message || 'Could not save footage.');
      saveBtn.disabled = false;
    }
  }

  if (transcriptEl) {
    transcriptEl.addEventListener('input', function () {
      transcriptManuallyEdited = true;
      if (transcriptEl.value.trim()) {
        setTranscriptMode(SpeechRecognition ? 'Transcript text ready. Verify before saving.' : 'Manual transcript text ready. Verify before saving.');
      }
    });
  }
  setTranscriptMode(SpeechRecognition ? 'Live transcript supported when recording starts.' : 'Live transcription not supported here. Manual transcript notes are supported.');

  startCameraBtn.addEventListener('click', startCamera);
  recordBtn.addEventListener('click', startRecording);
  stopBtn.addEventListener('click', stopRecording);
  saveBtn.addEventListener('click', saveRecording);
  window.addEventListener('pagehide', function () {
    stopTranscript();
    if (stream) stream.getTracks().forEach(function (track) { track.stop(); });
  });
}());
