/* Aurum Terminal — service worker (PWA offline shell) */
try {
  importScripts("sw-version.js"); // do npm prebuild sinh ra
} catch {
  /* dev chưa build: dùng bản mặc định */
}
const VERSION = `aurum-${self.AURUM_SW_VERSION || "v1"}`;
const SHELL = `${VERSION}-shell`;
const DATA = `${VERSION}-data`;

const SHELL_FILES = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/icons/icon.svg",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL)
      // cache: "reload" để bỏ qua HTTP cache — tránh precache index.html cũ
      // trỏ tới asset hash đã bị xoá sau khi build lại.
      .then((cache) =>
        Promise.all(
          SHELL_FILES.map((url) =>
            fetch(new Request(url, { cache: "reload" }))
              .then((res) => (res.ok ? cache.put(url, res) : undefined))
              .catch(() => undefined),
          ),
        ),
      )
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // API: network trước, cache làm nền tảng khi offline.
  // Chỉ cache response OK — không cache 4xx/5xx để khỏi phục vụ lỗi cũ.
  if (url.origin === self.location.origin && url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(DATA).then((cache) => cache.put(request, copy)).catch(() => undefined);
          }
          return res;
        })
        .catch(() => caches.match(request)),
    );
    return;
  }

  // HTML (điều hướng): network trước để index.html luôn khớp asset hash mới,
  // fallback cache khi offline. Asset tĩnh có hash nên vẫn cache-first bên dưới.
  if (request.mode === "navigate" || url.pathname === "/" || url.pathname === "/index.html") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(SHELL).then((cache) => cache.put(request, copy)).catch(() => undefined);
          }
          return res;
        })
        .catch(() =>
          caches.match(request).then((cached) => cached || caches.match("/index.html")),
        ),
    );
    return;
  }

  // Tài nguyên tĩnh: cache trước, network để làm mới.
  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.match(request).then((cached) => {
        const network = fetch(request)
          .then((res) => {
            if (res.ok) {
              const copy = res.clone();
              caches.open(SHELL).then((cache) => cache.put(request, copy)).catch(() => undefined);
            }
            return res;
          })
          .catch(() => cached);
        return cached || network;
      }),
    );
  }
});
