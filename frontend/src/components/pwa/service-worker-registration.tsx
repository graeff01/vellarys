'use client';

import { useEffect } from 'react';

// =============================================================================
// EXTENSÃO DE TIPOS (DOM)
// =============================================================================

type ExtendedNotificationOptions = NotificationOptions & {
  vibrate?: number[];
};

// =============================================================================
// SERVICE WORKER REGISTRATION
// =============================================================================

export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      registerServiceWorker();
    }
  }, []);

  return null;
}

async function registerServiceWorker() {
  try {
    const registration = await navigator.serviceWorker.register('/sw.js', {
      scope: '/',
    });

    console.log('✅ Service Worker registrado com sucesso:', registration.scope);

    // Verifica atualizações
    registration.addEventListener('updatefound', () => {
      const newWorker = registration.installing;
      console.log('🔄 Nova versão do Service Worker encontrada...');

      if (newWorker) {
        newWorker.addEventListener('statechange', () => {
          if (
            newWorker.state === 'installed' &&
            navigator.serviceWorker.controller
          ) {
            console.log('📦 Nova versão disponível! Recarregue para atualizar.');

            if (window.confirm('Nova versão disponível! Deseja atualizar?')) {
              newWorker.postMessage({ type: 'SKIP_WAITING' });
              window.location.reload();
            }
          }
        });
      }
    });

    // Escuta mensagens do service worker
    navigator.serviceWorker.addEventListener('message', (event) => {
      console.log('📩 Mensagem do Service Worker:', event.data);
    });
  } catch (error) {
    console.error('❌ Erro ao registrar Service Worker:', error);
  }
}

// =============================================================================
// PUSH NOTIFICATIONS HELPER
// =============================================================================

export async function requestNotificationPermission(): Promise<boolean> {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    console.warn('Este navegador não suporta notificações');
    return false;
  }

  if (Notification.permission === 'granted') {
    return true;
  }

  if (Notification.permission === 'denied') {
    console.warn('Notificações foram bloqueadas pelo usuário');
    return false;
  }

  const permission = await Notification.requestPermission();
  return permission === 'granted';
}

export async function subscribeToPush(): Promise<PushSubscription | null> {
  try {
    const registration = await navigator.serviceWorker.ready;

    let vapidPublicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;

    if (!vapidPublicKey) {
      console.warn('VAPID public key não encontrada no env, buscando do backend...');
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        const response = await fetch(`${API_URL}/notifications/vapid-public-key`);
        const data = await response.json();
        vapidPublicKey = data.public_key;
        console.log('🔑 Key obtida do backend:', vapidPublicKey?.substring(0, 10) + '...');
      } catch (error) {
        console.error('Erro ao buscar VAPID key do backend:', error);
      }
    }

    if (!vapidPublicKey) {
      console.warn('VAPID public key não configurada');
      return null;
    }

    // Limpa a chave de possíveis aspas ou espaços que o usuário possa ter colado no Railway
    const cleanKey = vapidPublicKey.trim().replace(/['"]/g, '');
    console.log(`📏 VAPID Key Length: ${cleanKey.length}`);

    const applicationServerKey = urlBase64ToUint8Array(cleanKey);

    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: applicationServerKey as BufferSource,
    });

    console.log('✅ Inscrito para push notifications:', subscription);
    return subscription;
  } catch (error) {
    console.error('❌ Erro ao inscrever para push:', error);
    return null;
  }
}

export async function unsubscribeFromPush(): Promise<boolean> {
  try {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();

    if (subscription) {
      await subscription.unsubscribe();
      console.log('✅ Desinscrito das push notifications');
      return true;
    }

    return false;
  } catch (error) {
    console.error('❌ Erro ao desinscrever do push:', error);
    return false;
  }
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }

  return outputArray;
}

// =============================================================================
// LOCAL NOTIFICATION
// =============================================================================

interface LocalNotificationOptions {
  body?: string;
  icon?: string;
  badge?: string;
  tag?: string;
  data?: Record<string, unknown>;
  vibrate?: number[];
  renotify?: boolean;
  requireInteraction?: boolean;
  silent?: boolean;
}

export async function showLocalNotification(
  title: string,
  options?: LocalNotificationOptions
): Promise<void> {
  const hasPermission = await requestNotificationPermission();

  if (!hasPermission) {
    console.warn('Sem permissão para mostrar notificações');
    return;
  }

  const registration = await navigator.serviceWorker.ready;

  await registration.showNotification(
    title,
    {
      icon: '/icons/icon-192x192.png',
      badge: '/icons/icon-72x72.png',
      vibrate: [200, 100, 200],
      tag: 'velaris-local',
      renotify: true,
      ...options,
    } as ExtendedNotificationOptions
  );
}
