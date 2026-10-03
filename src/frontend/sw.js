/* BillBhasha service worker — app shell cached for home-screen use. */
const CACHE = "billbhasha-v4";
const SHELL = ["/", "/assets/css/styles.css", "/assets/js/app.js",
  "/assets/js/api.js", "/assets/js/speech.js",
  "/assets/js/animations.js", "/assets/js/three-hero.js"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // Never cache API or audio — always fresh from the server.
  if (url.pathname.startsWith("/api/")) return;
  e.respondWith(
    caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
      const copy = res.clone();
      if (e.request.method === "GET" && res.ok) {
        caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
      }
      return res;
    }).catch(() => hit || Response.error()))
  );
});
