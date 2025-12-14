// Service Worker - Velaris PWA
// Versão do cache (atualizar ao fazer deploy)
const CACHE_VERSION = 'velaris-v1.0.0';

// Arquivos para cachear (shell do app)
const STATIC_CACHE = [
  '/',
  '/dashboard',
  '/dashboard/leads',
  '/dashboard/settings',
  '/offline.html',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
];

// Instalação do Service Worker
self.addEventListener('install', (event) => {
  console.log('[SW] Instalando Service Worker...');
  
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then((cache) => {
        console.log('[SW] Cache aberto, adicionando arquivos estáticos...');
        return cache.addAll(STATIC_CACHE);
      })
      .then(() => {
        console.log('[SW] Arquivos cacheados com sucesso!');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Erro ao cachear arquivos:', error);
      })
  );
});

// Ativação - limpa caches antigos
self.addEventListener('activate', (event) => {
  console.log('[SW] Ativando Service Worker...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_VERSION)
            .map((name) => {
              console.log('[SW] Removendo cache antigo:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        console.log('[SW] Service Worker ativado!');
        return self.clients.claim();
      })
  );
});

// Intercepta requisições (Network First, fallback to Cache)
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Ignora requisições que não são GET
  if (request.method !== 'GET') {
    return;
  }
  
  // Ignora requisições de API (sempre busca da rede)
  if (url.pathname.startsWith('/api/')) {
    return;
  }
  
  // Ignora websockets e outras requisições especiais
  if (url.protocol === 'chrome-extension:' || url.protocol === 'ws:' || url.protocol === 'wss:') {
    return;
  }
  
  event.respondWith(
    // Tenta buscar da rede primeiro
    fetch(request)
      .then((response) => {
        // Se sucesso, salva no cache e retorna
        if (response.ok) {
          const responseClone = response.clone();
          caches.open(CACHE_VERSION)
            .then((cache) => {
              cache.put(request, responseClone);
            });
        }
        return response;
      })
      .catch(() => {
        // Se falhar, busca do cache
        return caches.match(request)
          .then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            
            // Se não estiver no cache e for navegação, mostra página offline
            if (request.mode === 'navigate') {
              return caches.match('/offline.html');
            }
            
            // Retorna erro para outros recursos
            return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
          });
      })
  );
});

// =============================================================================
// PUSH NOTIFICATIONS
// =============================================================================

// Recebe notificação push
self.addEventListener('push', (event) => {
  console.log('[SW] Push recebido:', event);
  
  let data = {
    title: 'Velaris',
    body: 'Nova notificação',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    tag: 'velaris-notification',
    data: {},
  };
  
  // Tenta parsear dados do push
  if (event.data) {
    try {
      const pushData = event.data.json();
      data = { ...data, ...pushData };
    } catch (e) {
      data.body = event.data.text();
    }
  }
  
  const options = {
    body: data.body,
    icon: data.icon || '/icons/icon-192x192.png',
    badge: data.badge || '/icons/icon-72x72.png',
    tag: data.tag || 'velaris-notification',
    vibrate: [200, 100, 200, 100, 200], // Padrão de vibração
    requireInteraction: data.requireInteraction || false,
    renotify: true,
    data: data.data || {},
    actions: data.actions || [
      { action: 'open', title: 'Abrir' },
      { action: 'dismiss', title: 'Dispensar' },
    ],
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Clique na notificação
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notificação clicada:', event);
  
  event.notification.close();
  
  const action = event.action;
  const data = event.notification.data || {};
  
  if (action === 'dismiss') {
    return;
  }
  
  // URL para abrir (padrão: dashboard de leads)
  let targetUrl = '/dashboard/leads';
  
  if (data.url) {
    targetUrl = data.url;
  } else if (data.lead_id) {
    targetUrl = `/dashboard/leads?lead=${data.lead_id}`;
  }
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Se já tem uma janela aberta, foca nela
        for (const client of clientList) {
          if (client.url.includes('/dashboard') && 'focus' in client) {
            client.navigate(targetUrl);
            return client.focus();
          }
        }
        
        // Se não, abre nova janela
        if (clients.openWindow) {
          return clients.openWindow(targetUrl);
        }
      })
  );
});

// Fechar notificação
self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notificação fechada:', event);
});

// =============================================================================
// BACKGROUND SYNC (para enviar dados quando voltar online)
// =============================================================================

self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);
  
  if (event.tag === 'sync-notifications') {
    event.waitUntil(syncNotifications());
  }
});

async function syncNotifications() {
  // Implementar sincronização de notificações pendentes
  console.log('[SW] Sincronizando notificações...');
}

// =============================================================================
// MENSAGENS DO APP
// =============================================================================

self.addEventListener('message', (event) => {
  console.log('[SW] Mensagem recebida:', event.data);
  
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_VERSION });
  }
});