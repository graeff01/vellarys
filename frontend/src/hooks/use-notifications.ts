'use client';

import { useState, useEffect, useCallback } from 'react';
import { getToken } from '@/lib/auth';

// =============================================================================
// TIPOS
// =============================================================================

interface NotificationState {
  supported: boolean;
  permission: NotificationPermission | 'unsupported';
  loading: boolean;
  subscribed: boolean;
}

interface UseNotificationsReturn extends NotificationState {
  requestPermission: () => Promise<boolean>;
  showNotification: (title: string, body?: string) => Promise<void>;
  playSound: () => void;
  subscribeToPush: () => Promise<boolean>;
  unsubscribeFromPush: () => Promise<boolean>;
}

// =============================================================================
// SOM DE NOTIFICAÇÃO
// =============================================================================

let notificationAudio: HTMLAudioElement | null = null;

function getNotificationAudio(): HTMLAudioElement | null {
  if (typeof window === 'undefined') return null;

  if (!notificationAudio) {
    notificationAudio = new Audio('/sounds/notification.mp3');
    notificationAudio.volume = 0.5;
  }

  return notificationAudio;
}

// =============================================================================
// EXTENSÃO DE TIPOS
// =============================================================================

type ExtendedNotificationOptions = NotificationOptions & {
  vibrate?: number[];
};

// =============================================================================
// HELPER VAPID (CORRETO + TS SAFE)
// =============================================================================

function getApplicationServerKey(vapidPublicKey: string): ArrayBuffer {
  const padding = '='.repeat((4 - (vapidPublicKey.length % 4)) % 4);
  const base64 = (vapidPublicKey + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const buffer = new ArrayBuffer(rawData.length);
  const view = new Uint8Array(buffer);

  for (let i = 0; i < rawData.length; i++) {
    view[i] = rawData.charCodeAt(i);
  }

  return buffer;
}

// =============================================================================
// HOOK PRINCIPAL
// =============================================================================

export function useNotifications(): UseNotificationsReturn {
  const [state, setState] = useState<NotificationState>({
    supported: false,
    permission: 'unsupported',
    loading: true,
    subscribed: false,
  });

  // ---------------------------------------------------------------------------
  // Verificação inicial
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (typeof window === 'undefined') {
      setState((prev) => ({ ...prev, loading: false }));
      return;
    }

    const supported =
      'Notification' in window &&
      'serviceWorker' in navigator &&
      'PushManager' in window;

    if (!supported) {
      setState({
        supported: false,
        permission: 'unsupported',
        loading: false,
        subscribed: false,
      });
      return;
    }

    navigator.serviceWorker.ready.then(async (registration) => {
      const subscription = await registration.pushManager.getSubscription();

      setState({
        supported: true,
        permission: Notification.permission,
        loading: false,
        subscribed: !!subscription,
      });
    });
  }, []);

  // ---------------------------------------------------------------------------
  // Solicitar permissão
  // ---------------------------------------------------------------------------

  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (!('Notification' in window)) return false;

    setState((prev) => ({ ...prev, loading: true }));

    try {
      const permission = await Notification.requestPermission();

      setState((prev) => ({
        ...prev,
        permission,
        loading: false,
      }));

      return permission === 'granted';
    } catch (error) {
      console.error('Erro ao solicitar permissão:', error);
      setState((prev) => ({ ...prev, loading: false }));
      return false;
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Criar Push Subscription
  // ---------------------------------------------------------------------------

  const subscribeToPush = useCallback(async (): Promise<boolean> => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      console.error('Service Worker não suportado');
      return false;
    }

    setState((prev) => ({ ...prev, loading: true }));

    try {
      if (Notification.permission !== 'granted') {
        const granted = await requestPermission();
        if (!granted) {
          setState((prev) => ({ ...prev, loading: false }));
          return false;
        }
      }

      const registration = await navigator.serviceWorker.ready;

      let subscription = await registration.pushManager.getSubscription();

      if (!subscription) {
        const vapidPublicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
        if (!vapidPublicKey) {
          console.error('VAPID public key não configurada');
          setState((prev) => ({ ...prev, loading: false }));
          return false;
        }

        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: getApplicationServerKey(vapidPublicKey),
        });

        console.log('✅ Push subscription criada');
      }

      const token = localStorage.getItem('auth_token');
      if (!token) {
        console.error('Token não encontrado');
        setState((prev) => ({ ...prev, loading: false }));
        return false;
      }

      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

      const response = await fetch(`${apiUrl}/notifications/subscribe`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          endpoint: subscription.endpoint,
          keys: {
            p256dh: btoa(
              String.fromCharCode(
                ...new Uint8Array(subscription.getKey('p256dh')!)
              )
            ),
            auth: btoa(
              String.fromCharCode(
                ...new Uint8Array(subscription.getKey('auth')!)
              )
            ),
          },
        }),
      });

      if (!response.ok) {
        console.error(await response.text());
        setState((prev) => ({ ...prev, loading: false }));
        return false;
      }

      setState((prev) => ({
        ...prev,
        loading: false,
        subscribed: true,
      }));

      return true;
    } catch (error) {
      console.error('Erro ao criar subscription:', error);
      setState((prev) => ({ ...prev, loading: false }));
      return false;
    }
  }, [requestPermission]);

  // ---------------------------------------------------------------------------
  // Remover Push Subscription
  // ---------------------------------------------------------------------------

  const unsubscribeFromPush = useCallback(async (): Promise<boolean> => {
    if (typeof window === 'undefined') return false;

    setState((prev) => ({ ...prev, loading: true }));

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();

      if (subscription) {
        await subscription.unsubscribe();
      }

      setState((prev) => ({
        ...prev,
        loading: false,
        subscribed: false,
      }));

      return true;
    } catch (error) {
      console.error('Erro ao remover subscription:', error);
      setState((prev) => ({ ...prev, loading: false }));
      return false;
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Mostrar notificação local
  // ---------------------------------------------------------------------------

  const showNotification = useCallback(
    async (title: string, body?: string) => {
      if (!('Notification' in window)) return;

      if (Notification.permission !== 'granted') {
        const granted = await requestPermission();
        if (!granted) return;
      }

      try {
        const registration = await navigator.serviceWorker.ready;

        await registration.showNotification(title, {
          body,
          icon: '/icons/icon-192x192.png',
          badge: '/icons/icon-72x72.png',
          vibrate: [200, 100, 200],
          tag: 'velaris-notification',
          renotify: true,
        } as ExtendedNotificationOptions);
      } catch (error) {
        console.error('Erro ao mostrar notificação:', error);
      }
    },
    [requestPermission]
  );

  // ---------------------------------------------------------------------------
  // Som
  // ---------------------------------------------------------------------------

  const playSound = useCallback(() => {
    const audio = getNotificationAudio();
    if (!audio) return;

    audio.currentTime = 0;
    audio.play().catch(() => {});
  }, []);

  return {
    ...state,
    requestPermission,
    showNotification,
    playSound,
    subscribeToPush,
    unsubscribeFromPush,
  };
}

// =============================================================================
// POLLING
// =============================================================================

interface UseNotificationPollingOptions {
  enabled?: boolean;
  interval?: number;
  onNewNotification?: (count: number) => void;
}

export function useNotificationPolling(
  options: UseNotificationPollingOptions = {}
) {
  const { enabled = true, interval = 30000, onNewNotification } = options;
  const [unreadCount, setUnreadCount] = useState(0);
  const { playSound } = useNotifications();

  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return;

    let prev = 0;

    const check = async () => {
      const token = localStorage.getItem('auth_token');
      if (!token) return;

      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

      const res = await fetch(`${apiUrl}/notifications/count`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) return;

      const { count = 0 } = await res.json();

      if (count > prev && prev > 0) {
        playSound();
        onNewNotification?.(count);
      }

      prev = count;
      setUnreadCount(count);
    };

    check();
    const timer = setInterval(check, interval);
    return () => clearInterval(timer);
  }, [enabled, interval, onNewNotification, playSound]);

  return { unreadCount };
}
