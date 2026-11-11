const CACHE_NAME = 'vnstock-v2-cache-v6';
const STATIC_ASSETS = [
  '/',
  '/app',
  '/style.css',
  '/icon.ico',
  '/manifest.json',
  '/core.js',
  '/overview.js',
  '/screen.js',
  '/detail.js',
  '/alerts.js',
  '/portfolio.js',
  '/brief.js',
  '/watchlist.js',
  '/calculator.js',
  '/live.js',
  '/quote.js?v=2',
  '/vendor/lightweight-charts.standalone.production.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Nếu là API request (GET) -> Network first, lưu cache fallback khi offline!
  if (event.request.method === 'GET' && url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Lưu bản copy vào cache để dùng khi offline
          if (response && response.status === 200) {
            const respClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, respClone));
          }
          return response;
        })
        .catch(() => {
          // Khi mất mạng/offline -> Lấy dữ liệu đã cache gần nhất
          return caches.match(event.request);
        })
    );
    return;
  }

  // Đối với static assets (HTML, CSS, JS, Fonts...)
  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request).then((res) => {
        if (res && res.status === 200 && event.request.method === 'GET') {
          const resClone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, resClone));
        }
        return res;
      }).catch(() => caches.match('/app'));
    })
  );
});
