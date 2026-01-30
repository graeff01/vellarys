'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Users,
  Settings,
  LogOut,
  UserCheck,
  FileDown,
  Building2,
  Layers,
  ScrollText,
  Shield,
  CreditCard,
  Menu,
  X,
  Bot,
  Database,
  MessageCircle,
  Calendar,
  Sliders,
  ChevronRight
} from 'lucide-react';
import { getToken, getUser, logout, User } from '@/lib/auth';
import { NotificationBell } from '@/components/dashboard/notification-bell';
import { ServiceWorkerRegistration } from '@/components/pwa/service-worker-registration';
import { Sidebar } from '@/components/dashboard/sidebar';
import { FeaturesProvider } from '@/contexts/FeaturesContext';
import { cn } from '@/lib/utils';

declare const process: any;

// Menus logic moved to Sidebar component

// =============================================================================
// HOOK DE NOTIFICAÇÃO COM SOM
// =============================================================================

function useNotificationSound() {
  const [audio, setAudio] = useState<HTMLAudioElement | null>(null);
  const [lastCount, setLastCount] = useState<number>(0);
  const [isFirstLoad, setIsFirstLoad] = useState(true);

  // Inicializa o áudio
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const newAudio = new Audio('/sounds/notification.mp3');
      newAudio.volume = 0.5;
      setAudio(newAudio);
    }
  }, []);

  // Função para tocar som
  const playSound = useCallback(() => {
    if (audio) {
      audio.currentTime = 0;
      audio.play().catch((e) => {
        console.warn('Não foi possível tocar som:', e);
      });
    }
  }, [audio]);

  // Polling de notificações
  useEffect(() => {
    const checkNotifications = async () => {
      try {
        const token = getToken();
        if (!token) return;

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://hopeful-purpose-production-3a2b.up.railway.app/api/v1';

        const response = await fetch(`${apiUrl}/notifications/count`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) return;

        const data = await response.json();
        const newCount = data.count || data.unread_count || 0;

        // Se não é a primeira carga e tem mais notificações que antes
        if (!isFirstLoad && newCount > lastCount) {
          console.log('🔔 Nova notificação detectada! Tocando som...');
          playSound();

          // Mostrar notificação do navegador também
          if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('🔔 Vellarys', {
              body: 'Você tem uma nova notificação!',
              icon: '/icons/icon-192x192.png',
            });
          }
        }

        setLastCount(newCount);
        setIsFirstLoad(false);
      } catch (e) {
        console.warn('Erro ao verificar notificações:', e);
      }
    };

    // Verifica imediatamente
    checkNotifications();

    // Configura intervalo de 15 segundos
    const timer = setInterval(checkNotifications, 15000);

    return () => clearInterval(timer);
  }, [lastCount, isFirstLoad, playSound]);

  return { playSound };
}

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Hook de notificação com som
  useNotificationSound();

  const isSuperAdmin = user?.role === 'superadmin';

  useEffect(() => {
    const token = getToken();
    const userData = getUser();

    if (!token || !userData) {
      router.push('/login');
      return;
    }

    setUser(userData);
    setLoading(false);
  }, [router]);

  // Fecha sidebar ao mudar de página (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  // NOVO: Bloqueia scroll do body quando menu aberto no mobile
  useEffect(() => {
    if (sidebarOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [sidebarOpen]);

  function handleLogout() {
    logout();
    router.push('/login');
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-gray-500">Carregando...</div>
      </div>
    );
  }

  // Detecta se está na página do inbox para remover padding
  const isInboxPage = pathname === '/dashboard/inbox';

  return (
    <FeaturesProvider>
    <div className="min-h-screen bg-gray-100">
      <ServiceWorkerRegistration />
      {/* CORRIGIDO: Overlay para mobile - z-index 40 */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* CORRIGIDO: Sidebar - z-index 50 (acima do overlay) */}
      <Sidebar
        user={user}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onLogout={handleLogout}
      />

      {/* CORRIGIDO: Header - Oculto no inbox - Mobile Optimized */}
      {!isInboxPage && (
        <div className="lg:ml-72 bg-white/80 backdrop-blur-md border-b px-3 sm:px-4 lg:px-8 py-3 lg:py-4 flex justify-between items-center sticky top-0 z-30">
          {/* Botão hamburguer - só mobile */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 hover:bg-slate-100 rounded-lg transition-colors -ml-2"
            aria-label="Abrir menu"
          >
            <Menu className="w-5 h-5 sm:w-6 sm:h-6 text-slate-600" />
          </button>

          <div className="flex items-center gap-2 sm:gap-3">
            {isSuperAdmin && (
              <span className="text-[10px] sm:text-xs bg-indigo-50 text-indigo-600 px-2 sm:px-3 py-1 rounded-full font-bold flex items-center gap-1 sm:gap-2 border border-indigo-100">
                <Shield className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
                <span className="hidden sm:inline">MODO ADMIN MASTER</span>
                <span className="sm:hidden">ADMIN</span>
              </span>
            )}
          </div>

          <div className="flex-1" />
          <NotificationBell />
        </div>
      )}

      {/* CORRIGIDO: Conteúdo principal - Mobile Optimized */}
      <main className={cn(
        "lg:ml-72 relative z-10 transition-all duration-300",
        isInboxPage ? "h-screen" : "p-3 sm:p-4 lg:p-8"
      )}>
        {children}
      </main>
    </div>
    </FeaturesProvider>
  );
}