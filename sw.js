/* Cache sederhana agar aplikasi & mesin penilai (±30 MB) tidak diunduh ulang. */
const APP = "vmi-app-v1";
const CDN = "vmi-cdn-v1";
const SHELL = ["./", "index.html", "app.css", "app.js", "worker.js", "manifest.webmanifest", "icon.svg",
  "py/runner.py", ...["__init__", "vertical_line", "horizontal_line", "circle", "cross", "right_oblique", "square",
  "left_oblique", "oblique_cross", "triangle", "open_square_circle", "three_line_cross", "directional_arrows"].map((n) => `py/symbols/${n}.py`)];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(APP).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => ![APP, CDN].includes(k)).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // Pyodide & font dari CDN: versi tetap → cache dulu
  if (url.hostname === "cdn.jsdelivr.net" || url.hostname.endsWith("gstatic.com") || url.hostname === "fonts.googleapis.com") {
    e.respondWith(caches.open(CDN).then(async (c) => {
      const hit = await c.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res.ok || res.type === "opaque") c.put(req, res.clone());
      return res;
    }));
    return;
  }
  // File aplikasi sendiri: ambil versi terbaru, kalau offline pakai cache
  if (url.origin === location.origin) {
    e.respondWith(fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(APP).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: true }).then((r) => r || caches.match("index.html"))));
  }
});
