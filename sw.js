/* Moppi · trabajador de la app instalada.
   - La página se pide primero a la red: así cada versión nueva llega sola. Sin conexión, se usa la última guardada.
   - Íconos y manifiesto: desde la copia guardada.
   - Mascotas (imágenes): se guardan la primera vez que se usan y quedan disponibles sin conexión.
   - Los servicios externos (Google, TripGo, Mapillary) nunca pasan por aquí: siempre van a la red. */
const VERSION = 'moppi-1.9.19';
const CORE = ['./', './index.html', './manifest.webmanifest', './icons/icon-192.png', './icons/icon-512.png', './icons/maskable-512.png', './icons/apple-touch-icon.png'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(VERSION).then(cache => cache.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(key => key.startsWith('moppi-') && key !== VERSION).map(key => caches.delete(key))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  const isPage = request.mode === 'navigate' || url.pathname.endsWith('/') || url.pathname.endsWith('/index.html');
  if (isPage) {
    event.respondWith(fetch(request, { cache: 'no-cache' })
      .then(response => {
        if (response.ok) { const copy = response.clone(); caches.open(VERSION).then(cache => cache.put('./index.html', copy)); }
        return response;
      })
      .catch(() => caches.match('./index.html').then(hit => hit || caches.match('./'))));
    return;
  }
  event.respondWith(caches.match(request).then(hit => hit || fetch(request).then(response => {
    if (response.ok) { const copy = response.clone(); caches.open(VERSION).then(cache => cache.put(request, copy)); }
    return response;
  })));
});
