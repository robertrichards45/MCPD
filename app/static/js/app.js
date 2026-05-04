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

function registerMcpdServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  if (!window.isSecureContext && !['localhost', '127.0.0.1'].includes(window.location.hostname)) return;
  navigator.serviceWorker.register('/service-worker.js', { scope: '/' }).catch(() => {
    // PWA install support is helpful, but it should never block field workflow.
  });
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
  registerMcpdServiceWorker();
});
