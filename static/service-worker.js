self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open("trading-cache").then((cache) => {
      return cache.addAll([
        "/",
        "/static/css/styles.css",
        "/static/js/app.js",
        "/static/manifest.json"
      ]);
    })
  );
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((resp) => {
      return resp || fetch(event.request);
    })
  );
});
