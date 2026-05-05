const MCPD_CACHE = 'mcpd-portal-shell-v2';
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

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/mobile/home').then((cached) => cached || Response.error()))
    );
    return;
  }

  if (url.pathname.startsWith('/static/icons/') || url.pathname === '/manifest.webmanifest') {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request).then((response) => {
        const copy = response.clone();
        caches.open(MCPD_CACHE).then((cache) => cache.put(request, copy));
        return response;
      }))
    );
  }
});
