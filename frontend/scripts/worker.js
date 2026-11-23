// build-worker.mjs supplies cacheName and assets for this exact production build.
self.addEventListener('install', event => {
  event.waitUntil(caches.open(cacheName).then(cache =>
    cache.addAll(assets.map(url => new Request(url, { cache: 'reload' })))
  ))
})

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const previous = (await caches.keys()).filter(key =>
      key.startsWith('signbridge-shell-') && key !== cacheName
    )
    await Promise.all(previous.map(key => caches.delete(key)))
    await self.clients.claim()
  })())
})

self.addEventListener('fetch', event => {
  const request = event.request
  const url = new URL(request.url)
  if (request.method !== 'GET' || url.origin !== self.location.origin) return

  const key = request.mode === 'navigate' ? '/index.html' : url.pathname
  if (!assets.includes(key)) return
  event.respondWith((async () => {
    const cache = await caches.open(cacheName)
    return await cache.match(key) || fetch(request)
  })())
})
