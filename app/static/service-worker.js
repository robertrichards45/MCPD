const MCPD_CACHE = 'mcpd-portal-shell-v5';
const MCPD_ASSETS = [
  '/manifest.webmanifest',
  '/static/icons/mcpd-icon-192.png',
  '/static/icons/mcpd-icon-512.png',
  '/static/icons/mcpd-apple-touch-icon.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(MCPD_CACHE)
      .then((cache) => cache.addAll(MCPD_ASSETS))
      .catch(() => undefined)
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((key) => key !== MCPD_CACHE).map((key) => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => new Response('MCPD Portal is offline. Reconnect and refresh.', {
        status: 503,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      }))
    );
    return;
  }

  if (url.pathname.startsWith('/static/js/') || url.pathname.startsWith('/static/css/')) {
    event.respondWith(fetch(request));
    return;
  }

  if (url.pathname.startsWith('/static/icons/') || url.pathname === '/manifest.webmanifest') {
    event.respondWith(
      fetch(request).then((response) => {
        const copy = response.clone();
        caches.open(MCPD_CACHE).then((cache) => cache.put(request, copy));
        return response;
      }).catch(() => caches.match(request))
    );
  }
});
