'use client';

import { useState, useEffect, useCallback } from 'react';

// =============================================================================
// TIPOS
// =============================================================================

interface NotificationState {
  supported: boolean;
  permission: NotificationPermission | 'unsupported';
  loading: boolean;
}

interface UseNotificationsReturn extends NotificationState {
  requestPermission: () => Promise<boolean>;
  showNotification: (title: string, body?: string) => Promise<void>;
  playSound: () => void;
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
// EXTENSÃO DE TIPOS (DOM)
// =============================================================================

type ExtendedNotificationOptions = NotificationOptions & {
  vibrate?: number[];
};


// =============================================================================
// HOOK PRINCIPAL
// =============================================================================

export function useNotifications(): UseNotificationsReturn {
  const [state, setState] = useState<NotificationState>({
    supported: false,
    permission: 'unsupported',
    loading: true,
  });

  // Verifica suporte e permissão inicial
  useEffect(() => {
    if (typeof window === 'undefined') {
      setState((prev) => ({ ...prev, loading: false }));
      return;
    }

    const supported = 'Notification' in window && 'serviceWorker' in navigator;

    if (!supported) {
      setState({
        supported: false,
        permission: 'unsupported',
        loading: false,
      });
      return;
    }

    setState({
      supported: true,
      permission: Notification.permission,
      loading: false,
    });
  }, []);

  // Solicita permissão
  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (typeof window === 'undefined' || !('Notification' in window)) {
      return false;
    }

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

  // Mostra notificação local
  const showNotification = useCallback(
    async (title: string, body?: string): Promise<void> => {
      if (typeof window === 'undefined' || !('Notification' in window)) {
        return;
      }

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
        
        // Fallback: usa Notification API direta
        try {
          new Notification(title, {
            body,
            icon: '/icons/icon-192x192.png',
          });
        } catch (e) {
          console.error('Fallback também falhou:', e);
        }
      }
    },
    [requestPermission]
  );

  // Toca som de notificação
  const playSound = useCallback(() => {
    try {
      const audio = getNotificationAudio();
      if (audio) {
        audio.currentTime = 0;
        audio.play().catch((e) => {
          console.warn('Não foi possível tocar som:', e);
        });
      }
    } catch (e) {
      console.warn('Erro ao tocar som de notificação:', e);
    }
  }, []);

  return {
    ...state,
    requestPermission,
    showNotification,
    playSound,
  };
}

// =============================================================================
// HOOK PARA POLLING DE NOTIFICAÇÕES
// =============================================================================

interface UseNotificationPollingOptions {
  enabled?: boolean;
  interval?: number;
  onNewNotification?: (count: number) => void;
}

export function useNotificationPolling(options: UseNotificationPollingOptions = {}) {
  const { enabled = true, interval = 30000, onNewNotification } = options;
  const [unreadCount, setUnreadCount] = useState(0);
  const { playSound } = useNotifications();

  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return;

    let isMounted = true;
    let previousCount = 0;

    async function checkNotifications() {
      try {
        const token = localStorage.getItem('auth_token');
        if (!token) return;

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        
        const response = await fetch(`${apiUrl}/notifications/count`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) return;

        const data = await response.json();

        if (isMounted) {
          const newCount = data.count || 0;
          
          // Se tem mais notificações que antes, toca som e callback
          if (newCount > previousCount && previousCount > 0) {
            playSound();
            onNewNotification?.(newCount);
          }
          
          previousCount = newCount;
          setUnreadCount(newCount);
        }
      } catch (e) {
        console.warn('Erro ao verificar notificações:', e);
      }
    }

    // Verifica imediatamente
    checkNotifications();

    // Configura intervalo
    const timer = setInterval(checkNotifications, interval);

    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, [enabled, interval, onNewNotification, playSound]);

  return { unreadCount };
}