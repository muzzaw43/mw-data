/* Offline shell for the glossary. Network-first so updates show up; falls back to cache offline. */
const V = "g2", FILES = ["./", "index.html", "manifest.json", "icon-192.png"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(V).then((c) => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== V).map((k) => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;
  if (!FILES.concat(["apple-touch-icon.png", "icon-512.png"]).some((f) => u.pathname.endsWith(f === "./" ? "/" : f))) return;
  e.respondWith(fetch(new Request(e.request, { cache: "no-cache" })).then((r) => { const cp = r.clone(); caches.open(V).then((c) => c.put(e.request, cp)); return r; }).catch(() => caches.match(e.request)));
});
