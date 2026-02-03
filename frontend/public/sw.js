// Service Worker - Vellarys PWA
const CACHE_NAME = 'vellarys-v1.2.0';

// Recursos essenciais para funcionamento offline
const PRECACHE_ASSETS = [
  '/offline.html',
  '/icons/icon-192x192.png',
  '/manifest.json',
  '/sounds/notification.mp3'
];

// Instalação - Precache de ativos críticos
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Ativação - Limpeza de caches obsoletos
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Estratégia de Fetch
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 1. Ignorar o que não é GET ou é de extensões/APIs externas
  if (request.method !== 'GET' || url.protocol !== self.location.protocol) return;

  // 2. APIs: Network Only (sempre fresco)
  if (url.pathname.startsWith('/api/')) return;

  // 3. Ativos Estáticos (Fontes, Imagens, Scripts): Cache First / Stale While Revalidate
  if (
    request.destination === 'font' ||
    request.destination === 'image' ||
    request.destination === 'style' ||
    request.destination === 'script'
  ) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        const fetchPromise = fetch(request).then((networkResponse) => {
          if (networkResponse.ok) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
          }
          return networkResponse;
        });
        return cachedResponse || fetchPromise;
      })
    );
    return;
  }

  // 4. Navegação (Páginas HTML): Network First com Fallback para Offline
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .catch(() => {
          return caches.match(request).then((response) => {
            return response || caches.match('/offline.html');
          });
        })
    );
  }
});

// ======================
// Push Notifications
// ======================
self.addEventListener('push', (event) => {
  console.log('📩 Push recebido:', event);

  let data = {
    title: 'Vellarys',
    body: 'Nova atualização disponível',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    data: { url: '/dashboard' },
    tag: 'vellarys-notification',
    requireInteraction: false,
  };

  if (event.data) {
    try {
      const payload = event.data.json();
      console.log('📦 Payload recebido:', payload);
      data = { ...data, ...payload };
    } catch (e) {
      console.warn('⚠️ Erro ao parsear JSON, usando texto:', e);
      data.body = event.data.text();
    }
  }

  // iOS requer que a notificação seja mostrada imediatamente
  const notificationPromise = self.registration.showNotification(data.title, {
    body: data.body,
    icon: data.icon,
    badge: data.badge,
    tag: data.tag,
    requireInteraction: data.requireInteraction,
    vibrate: [200, 100, 200], // Padrão de vibração mais perceptível
    data: data.data,
    // Actions são suportadas apenas em alguns navegadores (Chrome, Edge)
    // iOS não suporta actions em notificações
    actions: typeof data.actions !== 'undefined' ? data.actions : [
      { action: 'open', title: 'Ver Agora', icon: '/icons/icon-96x96.png' },
      { action: 'close', title: 'Fechar' }
    ],
    silent: false,
    renotify: true,
  });

  event.waitUntil(notificationPromise);
});

self.addEventListener('notificationclick', (event) => {
  console.log('👆 Notificação clicada:', event);

  event.notification.close();

  // Processa ação específica se tiver (não suportado no iOS)
  if (event.action === 'close') {
    console.log('✖️ Notificação fechada pelo usuário');
    return;
  }

  const urlToOpen = event.notification.data?.url || '/dashboard';
  console.log('🔗 Abrindo URL:', urlToOpen);

  event.waitUntil(
    clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    }).then((windowClients) => {
      console.log('🪟 Clientes encontrados:', windowClients.length);

      // Procura por uma janela/aba já aberta com a URL
      for (let client of windowClients) {
        const clientUrl = new URL(client.url);
        const targetUrl = new URL(urlToOpen, self.location.origin);

        if (clientUrl.pathname === targetUrl.pathname && 'focus' in client) {
          console.log('✅ Focando cliente existente');
          return client.focus();
        }
      }

      // Se não encontrou, abre uma nova janela
      if (clients.openWindow) {
        const fullUrl = urlToOpen.startsWith('http') ? urlToOpen : self.location.origin + urlToOpen;
        console.log('🆕 Abrindo nova janela:', fullUrl);
        return clients.openWindow(fullUrl);
      }
    }).catch(err => {
      console.error('❌ Erro ao abrir janela:', err);
    })
  );
});