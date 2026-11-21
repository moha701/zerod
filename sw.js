// ZEROED offline support: the page and data refresh from the network when online, cached copies when offline.
const CACHE = "zeroed-v4";
const CORE = ["./", "./index.html", "./data.json", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting())); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", (e) => {
  const req = e.request; if (req.method !== "GET") return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;
  const cdn = /fonts\.(googleapis|gstatic)\.com|cdnjs\.cloudflare\.com/.test(url.hostname);
  if (!sameOrigin && !cdn) return;
  if (sameOrigin) {
    // network first, so new data and new versions show up straight away
    e.respondWith(fetch(req).then((r) => { const copy = r.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); return r; }).catch(() => caches.match(req).then((r) => r || caches.match("./index.html"))));
  } else {
    // fonts and three.js: cache first
    e.respondWith(caches.match(req).then((r) => r || fetch(req).then((res) => { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); return res; })));
  }
});
