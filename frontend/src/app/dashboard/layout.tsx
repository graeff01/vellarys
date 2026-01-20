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
  Database
} from 'lucide-react';
import { getToken, getUser, logout, User } from '@/lib/auth';
import { NotificationBell } from '@/components/dashboard/notification-bell';
import { ServiceWorkerRegistration } from '@/components/pwa/service-worker-registration';

// Menus para GESTOR (cliente normal)
const gestorMenuItems = [
  { href: '/dashboard', label: 'Visão Geral', icon: LayoutDashboard },
  { href: '/dashboard/leads', label: 'Leads', icon: Users },
  { href: '/dashboard/sellers', label: 'Vendedores', icon: UserCheck },
  { href: '/dashboard/simulator', label: 'Simulador IA', icon: Bot },
  { href: '/dashboard/export', label: 'Relatórios', icon: FileDown },
];

// Menus para SUPERADMIN (você)
const superadminMenuItems = [
  { href: '/dashboard', label: 'Visão Geral', icon: LayoutDashboard },
  { href: '/dashboard/clients', label: 'Clientes', icon: Building2 },
  { href: '/dashboard/plans', label: 'Planos', icon: CreditCard },
  { href: '/dashboard/niches', label: 'Nichos', icon: Layers },
  { href: '/dashboard/datasources', label: 'Fontes de Dados', icon: Database },
  { href: '/dashboard/settings', label: 'Configurações', icon: Settings },
  { href: '/dashboard/export', label: 'Relatórios', icon: FileDown },
  { href: '/dashboard/logs', label: 'Logs', icon: ScrollText },
];

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
            new Notification('🔔 Velaris', {
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
  const menuItems = isSuperAdmin ? superadminMenuItems : gestorMenuItems;

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

  return (
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
      <aside
        className={`
          fixed left-0 top-0 h-full w-64 bg-white shadow-lg z-50
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:translate-x-0
        `}
      >
        {/* Header do Sidebar */}
        <div className="p-6 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isSuperAdmin && <Shield className="w-6 h-6 text-purple-600" />}
            <div>
              <h1 className="text-2xl font-bold text-blue-600">vellarys</h1>
              <p className="text-sm text-gray-500">
                {isSuperAdmin ? (
                  <span className="text-purple-600 font-medium">Admin Master</span>
                ) : (
                  user?.tenant?.name || 'IA Atendente'
                )}
              </p>
            </div>
          </div>
          {/* Botão fechar - só mobile */}
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Menu */}
        <nav className="p-4 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 220px)' }}>
          <ul className="space-y-2">
            {menuItems.map((item) => {
              const isActive = pathname === item.href ||
                (item.href !== '/dashboard' && pathname.startsWith(item.href));

              // Destaque especial para o Simulador
              const isSimulator = item.href === '/dashboard/simulator';

              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${isActive
                      ? isSuperAdmin
                        ? 'bg-purple-50 text-purple-600'
                        : isSimulator
                          ? 'bg-gradient-to-r from-purple-50 to-blue-50 text-purple-600'
                          : 'bg-blue-50 text-blue-600'
                      : isSimulator
                        ? 'text-purple-600 hover:bg-purple-50'
                        : 'text-gray-600 hover:bg-gray-50'
                      }`}
                  >
                    <item.icon className={`w-5 h-5 ${isSimulator && !isActive ? 'text-purple-500' : ''}`} />
                    <span className={isSimulator ? 'font-medium' : ''}>{item.label}</span>
                    {isSimulator && !isActive && (
                      <span className="ml-auto text-xs bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full">
                        Novo
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* User Info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t bg-white">
          <div className="px-4 py-2 mb-2">
            <p className="text-sm font-medium text-gray-900 truncate">{user?.name}</p>
            <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            {isSuperAdmin && (
              <span className="inline-block mt-1 px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">
                SuperAdmin
              </span>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-3 w-full text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
          >
            <LogOut className="w-5 h-5" />
            Sair
          </button>
        </div>
      </aside>

      {/* CORRIGIDO: Header - z-index 30 (abaixo do overlay) */}
      <div className="lg:ml-64 bg-white border-b px-4 lg:px-8 py-4 flex justify-between items-center sticky top-0 z-30">
        {/* Botão hamburguer - só mobile */}
        <button
          onClick={() => setSidebarOpen(true)}
          className="lg:hidden p-2 hover:bg-gray-100 rounded-lg mr-4 transition-colors"
        >
          <Menu className="w-6 h-6 text-gray-600" />
        </button>

        {isSuperAdmin && (
          <span className="text-sm text-purple-600 font-medium hidden sm:flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Modo Administrador
          </span>
        )}
        <div className="flex-1" />
        <NotificationBell />
      </div>

      {/* CORRIGIDO: Conteúdo principal - z-index 10 (abaixo do overlay) */}
      <main className="lg:ml-64 p-4 lg:p-8 relative z-10">{children}</main>
    </div>
  );
}