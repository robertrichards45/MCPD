let drawing = false;
let lastX = 0;
let lastY = 0;
let scannerStream = null;

function getCanvas() {
  return document.getElementById('sig-pad');
}

function startDraw(e) {
  drawing = true;
  const { x, y } = getPos(e);
  lastX = x;
  lastY = y;
}

function endDraw() {
  drawing = false;
}

function draw(e) {
  if (!drawing) return;
  const canvas = getCanvas();
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const { x, y } = getPos(e);
  ctx.strokeStyle = '#111';
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(lastX, lastY);
  ctx.lineTo(x, y);
  ctx.stroke();
  lastX = x;
  lastY = y;
}

function getPos(e) {
  const canvas = getCanvas();
  const rect = canvas.getBoundingClientRect();
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;
  return { x: clientX - rect.left, y: clientY - rect.top };
}

function clearSig() {
  const canvas = getCanvas();
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function submitSig() {
  const canvas = getCanvas();
  if (!canvas) return false;
  const data = canvas.toDataURL('image/png');
  document.getElementById('signature_data').value = data;
  return true;
}

async function openModuleScanner() {
  const video = document.querySelector('[data-scanner-video]');
  const status = document.querySelector('[data-scanner-status]');
  if (!video || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    if (status) status.textContent = 'Camera access is not available in this browser.';
    return;
  }
  try {
    scannerStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' },
      audio: false,
    });
    video.srcObject = scannerStream;
    await video.play();
    if (status) status.textContent = 'Scanner active. Ready for QR input in this station context.';
  } catch (err) {
    if (status) status.textContent = 'Camera permission denied or unavailable.';
  }
}

function stopModuleScanner() {
  const video = document.querySelector('[data-scanner-video]');
  const status = document.querySelector('[data-scanner-status]');
  if (scannerStream) {
    scannerStream.getTracks().forEach((track) => track.stop());
    scannerStream = null;
  }
  if (video) {
    video.pause();
    video.srcObject = null;
  }
  if (status) status.textContent = 'Scanner stopped.';
}

function bindModuleScanner() {
  const openButton = document.querySelector('[data-scanner-open]');
  const stopButton = document.querySelector('[data-scanner-stop]');
  const manualInput = document.querySelector('[data-scanner-manual]');
  const status = document.querySelector('[data-scanner-status]');
  if (!openButton || !stopButton || !manualInput) return;

  openButton.addEventListener('click', openModuleScanner);
  stopButton.addEventListener('click', stopModuleScanner);
  manualInput.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    const rawValue = (manualInput.value || '').trim();
    if (!rawValue) return;
    const context = openButton.dataset.scannerContext || 'UNKNOWN';
    const allowedPrefix = `${context}:`;
    if (!rawValue.startsWith(allowedPrefix)) {
      if (status) status.textContent = 'Invalid card for this station.';
      manualInput.value = '';
      return;
    }
    if (status) status.textContent = `Accepted token for ${context} at ${new Date().toLocaleTimeString()}.`;
    manualInput.value = '';
  });
}

async function refreshModuleFeed(feed) {
  const url = feed.dataset.feedUrl;
  if (!url) return;
  try {
    const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    if (!res.ok) return;
    const json = await res.json();
    const items = json.entries || [];
    const timestamp = json.last_updated || '';
    const label = document.querySelector('[data-live-refresh-label]');
    if (label && timestamp) label.textContent = timestamp;
    if (!items.length) {
      feed.innerHTML = '<div class="list-group-item">No activity yet.</div>';
      return;
    }
    feed.innerHTML = items.map((item) => `<div class="list-group-item">${item}</div>`).join('');
  } catch (err) {
    return;
  }
}

function bindModuleFeed() {
  const feed = document.querySelector('[data-module-feed]');
  if (!feed) return;
  refreshModuleFeed(feed);
  window.setInterval(() => refreshModuleFeed(feed), 15000);
}

function buildReportNarrative(factsText) {
  const facts = (factsText || '').trim();
  if (!facts) {
    return '';
  }
  return [
    'On the listed date and time, I documented the following facts based on the officer-entered account.',
    facts,
    'This narrative is officer-reviewed and should be edited to include only verified facts, actions taken, and final disposition before submission.',
  ].join('\n\n');
}

function buildReportBlotter(factsText) {
  const facts = (factsText || '').replace(/\s+/g, ' ').trim();
  if (!facts) {
    return '';
  }
  return facts.length > 220 ? `${facts.slice(0, 217)}...` : facts;
}

function bindReportWorkspace() {
  const root = document.querySelector('[data-report-workflow]');
  if (!root) return;
  const facts = root.querySelector('[data-report-facts]');
  const narrative = root.querySelector('[data-report-narrative]');
  const blotter = root.querySelector('[data-report-blotter]');
  const narrativeButton = root.querySelector('[data-generate-narrative]');
  const blotterButton = root.querySelector('[data-generate-blotter]');
  const voiceButton = root.querySelector('[data-voice-target]');
  const voiceStatus = root.querySelector('[data-voice-status]');

  if (narrativeButton && facts && narrative) {
    narrativeButton.addEventListener('click', () => {
      const draft = buildReportNarrative(facts.value);
      if (!draft) {
        if (voiceStatus) voiceStatus.textContent = 'Enter facts before generating a narrative.';
        facts.focus();
        return;
      }
      narrative.value = draft;
      if (voiceStatus) voiceStatus.textContent = 'Narrative generated. Review and edit before saving.';
    });
  }

  if (blotterButton && facts && blotter) {
    blotterButton.addEventListener('click', () => {
      const draft = buildReportBlotter(facts.value);
      if (!draft) {
        if (voiceStatus) voiceStatus.textContent = 'Enter facts before generating a blotter entry.';
        facts.focus();
        return;
      }
      blotter.value = draft;
      if (voiceStatus) voiceStatus.textContent = 'Blotter draft generated. Review before use.';
    });
  }

  if (voiceButton && facts) {
    voiceButton.addEventListener('click', () => {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        if (voiceStatus) voiceStatus.textContent = 'Voice input is not supported in this browser. Type the facts instead.';
        facts.focus();
        return;
      }
      const recognition = new SpeechRecognition();
      recognition.lang = 'en-US';
      recognition.interimResults = false;
      recognition.continuous = false;
      recognition.onstart = () => {
        if (voiceStatus) voiceStatus.textContent = 'Listening. Speak the facts clearly.';
      };
      recognition.onerror = () => {
        if (voiceStatus) voiceStatus.textContent = 'Voice input stopped. Typed entry is still available.';
      };
      recognition.onresult = (event) => {
        const transcript = Array.from(event.results || [])
          .map((result) => result[0] && result[0].transcript ? result[0].transcript : '')
          .join(' ')
          .trim();
        if (transcript) {
          facts.value = `${facts.value ? `${facts.value.trim()}\n` : ''}${transcript}`;
        }
        if (voiceStatus) voiceStatus.textContent = 'Voice text added. Review and correct it before saving.';
      };
      recognition.start();
    });
  }
}

window.addEventListener('load', () => {
  const canvas = getCanvas();
  if (canvas) {
    canvas.addEventListener('mousedown', startDraw);
    canvas.addEventListener('mouseup', endDraw);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseleave', endDraw);
    canvas.addEventListener('touchstart', (e) => { e.preventDefault(); startDraw(e); });
    canvas.addEventListener('touchend', (e) => { e.preventDefault(); endDraw(); });
    canvas.addEventListener('touchmove', (e) => { e.preventDefault(); draw(e); });
  }

  const nav = document.querySelector('.top-nav');
  const navToggle = document.querySelector('[data-nav-toggle]');
  if (nav && navToggle) {
    navToggle.addEventListener('click', () => {
      const isOpen = nav.classList.toggle('nav-open');
      navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    const navLinks = nav.querySelectorAll('.nav-links a');
    navLinks.forEach((link) => {
      link.addEventListener('click', () => {
        nav.classList.remove('nav-open');
        navToggle.setAttribute('aria-expanded', 'false');
      });
    });

    document.addEventListener('click', (event) => {
      if (window.innerWidth > 820) return;
      if (!nav.classList.contains('nav-open')) return;
      if (nav.contains(event.target)) return;
      nav.classList.remove('nav-open');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  }

  bindModuleScanner();
  bindModuleFeed();
  bindReportWorkspace();
});
