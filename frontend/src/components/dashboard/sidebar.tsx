'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
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
    Bot,
    MessageCircle,
    Calendar,
    Sliders,
    X,
    ChevronRight,
    LucideIcon,
    Sparkles
} from 'lucide-react';
import { User, getToken } from '@/lib/auth';
import { cn } from '@/lib/utils';

interface MenuItem {
    href: string;
    label: string;
    icon: LucideIcon;
    badge?: string;
    feature?: string;
}

interface MenuGroup {
    title: string;
    items: MenuItem[];
}

interface SidebarProps {
    user: User | null;
    isOpen: boolean;
    onClose: () => void;
    onLogout: () => void;
}

export function Sidebar({ user, isOpen, onClose, onLogout }: SidebarProps) {
    const pathname = usePathname();
    const isSuperAdmin = user?.role === 'superadmin';
    const isSeller = user?.role === 'corretor';

    const [features, setFeatures] = useState<Record<string, boolean>>({});

    useEffect(() => {
        const fetchFeatures = async () => {
            try {
                const token = getToken(); // Assuming getToken is imported or available via context/props if not imported.
                // If getToken is not imported, I need to import it. It IS imported in previous files but maybe not here.
                // Checking imports... "import { User } from '@/lib/auth';" 
                // I need to update imports to include getToken.
                if (!token) return;

                const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'}/v1/settings/features`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (response.ok) {
                    const data = await response.json();
                    setFeatures(data.final_features || data);
                }
            } catch (error) {
                console.error('Failed to load features:', error);
            }
        };

        fetchFeatures();
    }, []);

    // Definição de grupos de menu
    const getMenuGroups = (): MenuGroup[] => {
        if (isSuperAdmin) {
            return [
                {
                    title: "Principal",
                    items: [
                        { href: '/dashboard', label: 'Visão Geral', icon: LayoutDashboard },
                        { href: '/dashboard/clients', label: 'Clientes', icon: Building2 },
                    ]
                },
                {
                    title: "Sistema",
                    items: [
                        { href: '/dashboard/plans', label: 'Planos', icon: CreditCard },
                        { href: '/dashboard/niches', label: 'Nichos', icon: Layers },
                        { href: '/dashboard/logs', label: 'Logs do Sistema', icon: ScrollText },
                        { href: '/dashboard/settings', label: 'Configurações', icon: Settings },
                    ]
                },
                {
                    title: "Laboratório",
                    items: [
                        { href: '/dashboard/copilot', label: 'Vellarys Copilot', icon: Sparkles, badge: "AI" },
                        { href: '/dashboard/simulator', label: 'Simulador IA', icon: Bot, badge: "Lab" },
                    ]
                }
            ];
        }

        if (isSeller) {
            return [
                {
                    title: "Atendimento",
                    items: [
                        { href: '/dashboard/inbox', label: 'Inbox Omnichannel', icon: MessageCircle },
                        { href: '/dashboard/leads', label: 'Meus Leads', icon: Users },
                        { href: '/dashboard/calendar', label: 'Minha Agenda', icon: Calendar, feature: 'calendar_enabled' },
                    ]
                },
                {
                    title: "Performance",
                    items: [
                        { href: '/dashboard', label: 'Meus Resultados', icon: LayoutDashboard, feature: 'metrics_enabled' },
                    ]
                }
            ];
        }

        // GESTOR (Default)
        return [
            {
                title: "Operação",
                items: [
                    { href: '/dashboard', label: 'Visão Geral', icon: LayoutDashboard },
                    { href: '/dashboard/leads', label: 'Leads', icon: Users },
                    { href: '/dashboard/calendar', label: 'Agenda Equipe', icon: Calendar, feature: 'calendar_enabled' },
                ]
            },
            {
                title: "Equipe",
                items: [
                    { href: '/dashboard/sellers', label: 'Vendedores', icon: UserCheck },
                ]
            },
            {
                title: "Inteligência",
                items: [
                    { href: '/dashboard/copilot', label: 'Vellarys Copilot', icon: Sparkles, badge: "AI" },
                    { href: '/dashboard/simulator', label: 'Simulador IA', icon: Bot },
                    { href: '/dashboard/export', label: 'Exportar Dados', icon: FileDown, feature: 'security_export_lock_enabled' },
                ]
            }
        ];
    };

    const menuGroups = getMenuGroups();

    return (
        <aside
            className={cn(
                "fixed left-0 top-0 h-full w-72 bg-white border-r border-slate-200 z-50 flex flex-col transition-all duration-300 ease-in-out select-none",
                isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
            )}
        >
            {/* 🚀 HEADER: Logo & Brand */}
            <div className="p-8 flex items-center justify-between group">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:rotate-6 transition-transform">
                        <Bot className="w-6 h-6 text-white" />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-xl font-bold text-slate-900 tracking-tight leading-none">vellarys</span>
                        <span className="text-[10px] uppercase tracking-widest text-indigo-600 font-bold mt-0.5 truncate max-w-[140px]">
                            {isSuperAdmin ? "Admin Master" : (user?.tenant?.name || "Enterprise")}
                        </span>
                    </div>
                </div>
                <button
                    onClick={onClose}
                    className="lg:hidden p-2 hover:bg-slate-100 rounded-lg text-slate-400 transition-colors"
                >
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* 🧭 NAVIGATION: Scrolled area (sem barra visível) */}
            <nav className="flex-1 px-4 space-y-7 overflow-y-auto no-scrollbar py-2">
                {menuGroups.map((group, idx) => (
                    <div key={idx} className="space-y-1.5">
                        <h3 className="px-4 text-[10px] font-bold text-slate-400 uppercase tracking-[2px]">
                            {group.title}
                        </h3>
                        <ul className="space-y-0.5">
                            {group.items.map((item) => {
                                // 🔒 Feature Gating Logic
                                if (item.feature) {
                                    // Caso especial: Lock Feature (Enable = Bloqueado)
                                    if (item.feature === 'security_export_lock_enabled') {
                                        // Se o bloqueio está ATIVO e NÃO é superadmin, esconde
                                        if (features[item.feature] === true && !isSuperAdmin) return null;
                                    } else {
                                        // Casos normais: Feature Flag (False = Esconde)
                                        // Se a feature está explicitamente FALSE no objeto, esconde.
                                        // Se undefined (ainda não carregou ou não existe), mostra por padrão para evitar layout shift agressivo ou assume false?
                                        // Assumindo que o backend retorna o set completo. Se não vier, assume false para segurança (opt-in)?
                                        // No código SubscriptionSettings, features padrão do plano vêm. 
                                        // Vamos assumir: se features já carregou (tem chaves) e a chave é false/undefined, esconde.
                                        if (Object.keys(features).length > 0 && !features[item.feature]) return null;
                                    }
                                }

                                const isActive = pathname === item.href ||
                                    (item.href !== '/dashboard' && pathname.startsWith(item.href));

                                return (
                                    <li key={item.href}>
                                        <Link
                                            href={item.href}
                                            className={cn(
                                                "group flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all relative overflow-hidden",
                                                isActive
                                                    ? "bg-indigo-50 text-indigo-700 shadow-sm"
                                                    : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
                                            )}
                                        >
                                            {/* Active Indicator Bar */}
                                            {isActive && (
                                                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-indigo-600 rounded-r-full" />
                                            )}

                                            <item.icon className={cn(
                                                "w-5 h-5 transition-transform group-hover:scale-105",
                                                isActive ? "text-indigo-600" : "text-slate-400 group-hover:text-indigo-500"
                                            )} />

                                            <span className="text-sm font-semibold flex-1">{item.label}</span>

                                            {item.badge && (
                                                <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-100 text-indigo-600 border border-indigo-200">
                                                    {item.badge}
                                                </span>
                                            )}

                                            {!isActive && (
                                                <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all text-slate-300" />
                                            )}
                                        </Link>
                                    </li>
                                );
                            })}
                        </ul>
                    </div>
                ))}
            </nav>

            {/* 👤 FOOTER: Profile & Logout */}
            <div className="p-4 border-t border-slate-100 bg-slate-50/50">
                <div className="flex items-center gap-3 p-3 rounded-2xl bg-white border border-slate-200 shadow-sm mb-3">
                    <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold text-sm shadow-inner">
                        {user?.name?.charAt(0) || 'U'}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-bold text-slate-900 truncate">{user?.name}</p>
                        <p className="text-[10px] font-medium text-slate-400 truncate">{user?.email}</p>
                    </div>
                    {isSuperAdmin && (
                        <Shield className="w-4 h-4 text-indigo-500 flex-shrink-0" />
                    )}
                </div>

                <button
                    onClick={onLogout}
                    className="flex items-center gap-3 px-4 py-2.5 w-full text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all font-bold text-sm"
                >
                    <LogOut className="w-4 h-4" />
                    Sair da Conta
                </button>
            </div>

            <style jsx global>{`
        .no-scrollbar::-webkit-scrollbar {
          display: none;
        }
        .no-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
        </aside>
    );
}
