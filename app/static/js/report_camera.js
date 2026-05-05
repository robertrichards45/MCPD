(function () {
  'use strict';

  var video = document.getElementById('report-camera-preview');
  var canvas = document.getElementById('report-camera-canvas');
  var capturePreview = document.getElementById('report-camera-capture-preview');
  var startBtn = document.getElementById('report-camera-start');
  var captureBtn = document.getElementById('report-camera-capture');
  var saveBtn = document.getElementById('report-camera-save');
  var statusEl = document.getElementById('report-camera-status');
  var labelEl = document.getElementById('report-camera-label');
  var pageKeyEl = document.getElementById('report-camera-page-key');
  var openReport = document.getElementById('report-camera-open-report');
  var stream = null;
  var photoBlob = null;

  if (!video || !canvas || !startBtn || !captureBtn || !saveBtn) return;

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  async function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setStatus('Camera is not supported on this browser. Open this page over HTTPS on the phone or upload photos from desktop.');
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      startBtn.disabled = true;
      captureBtn.disabled = false;
      setStatus('Camera ready. Capture will stay inside MCPD Portal storage after you save.');
    } catch (e) {
      setStatus('Camera permission denied or unavailable. Check browser permissions and HTTPS.');
    }
  }

  function capturePhoto() {
    if (!stream || !video.videoWidth) {
      setStatus('Camera is not ready yet.');
      return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(function (blob) {
      if (!blob) {
        setStatus('Could not capture photo.');
        return;
      }
      photoBlob = blob;
      capturePreview.src = URL.createObjectURL(blob);
      capturePreview.hidden = false;
      saveBtn.disabled = false;
      setStatus('Photo captured. Tap Save to Report to store it in the app.');
    }, 'image/jpeg', 0.9);
  }

  async function savePhoto() {
    if (!photoBlob) {
      setStatus('Capture a photo before saving.');
      return;
    }
    saveBtn.disabled = true;
    setStatus('Saving photo to report...');
    var form = new FormData();
    form.append('photo', photoBlob, 'report-photo.jpg');
    form.append('label', labelEl ? labelEl.value : 'Report Photo');
    form.append('page_key', pageKeyEl ? pageKeyEl.value : 'report-photo');
    try {
      var response = await fetch(window.MCPD_REPORT_CAMERA_UPLOAD_URL, { method: 'POST', body: form });
      var data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Photo save failed.');
      setStatus('Photo saved to report.');
      if (openReport) {
        openReport.hidden = false;
        openReport.href = data.detailUrl || openReport.href;
      }
      photoBlob = null;
    } catch (e) {
      setStatus(e.message || 'Could not save photo.');
      saveBtn.disabled = false;
    }
  }

  startBtn.addEventListener('click', startCamera);
  captureBtn.addEventListener('click', capturePhoto);
  saveBtn.addEventListener('click', savePhoto);
  window.addEventListener('pagehide', function () {
    if (stream) stream.getTracks().forEach(function (track) { track.stop(); });
  });
}());
