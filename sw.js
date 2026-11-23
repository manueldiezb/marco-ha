// Arranque instantáneo cuando iOS ha cerrado la app web en segundo plano: dashboard.html sale de la caché del
// dispositivo y se renueva por detrás. checkUpdate() (fetch normal, no navegación) va siempre a la red y de paso
// deja la caché al día, así que una versión nueva entra como antes: recarga una vez y ya sale la nueva.
// ponytail: solo cachea dashboard.html; fondos, logos e iconos ya los guarda la caché HTTP (max-age 31 días).
const C = 'marco';
self.addEventListener('install', e => { self.skipWaiting(); e.waitUntil(caches.open(C).then(c => c.add('dashboard.html'))); });
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin || !u.pathname.endsWith('/dashboard.html')) return;
  const red = fetch(u.pathname, { cache: 'no-cache' }).then(async r => {
    if (r.ok) await (await caches.open(C)).put(u.pathname, r.clone());
    return r;
  });
  if (e.request.mode !== 'navigate') return e.respondWith(red);
  e.waitUntil(red.catch(() => {}));
  e.respondWith(caches.match(u.pathname).then(c => c || red));
});
