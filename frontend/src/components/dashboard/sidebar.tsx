'use client';

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
    Bot,
    MessageCircle,
    Calendar,
    Sliders,
    X,
    ChevronRight
} from 'lucide-react';
import { User } from '@/lib/auth';
import { cn } from '@/lib/utils';

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

    // Definição de grupos de menu
    const getMenuGroups = () => {
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
                        { href: '/dashboard/simulator', label: 'Simulador IA', icon: Bot, badge: "Lab" },
                        { href: '/dashboard/control-center', label: 'Centro de Controle', icon: Sliders },
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
                        { href: '/dashboard/calendar', label: 'Minha Agenda', icon: Calendar },
                    ]
                },
                {
                    title: "Performance",
                    items: [
                        { href: '/dashboard', label: 'Meus Resultados', icon: LayoutDashboard },
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
                    { href: '/dashboard/calendar', label: 'Agenda Equipe', icon: Calendar },
                ]
            },
            {
                title: "Equipe",
                items: [
                    { href: '/dashboard/sellers', label: 'Vendedores', icon: UserCheck },
                    { href: '/dashboard/control-center', label: 'Regras de Negócio', icon: Sliders },
                ]
            },
            {
                title: "Inteligência",
                items: [
                    { href: '/dashboard/simulator', label: 'Simulador IA', icon: Bot },
                    { href: '/dashboard/export', label: 'Exportar Dados', icon: FileDown },
                ]
            }
        ];
    };

    const menuGroups = getMenuGroups();

    return (
        <aside
            className={cn(
                "fixed left-0 top-0 h-full w-72 bg-slate-950 border-r border-slate-800 z-50 flex flex-col transition-all duration-300 ease-in-out select-none",
                isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
            )}
        >
            {/* 🚀 HEADER: Logo & Brand */}
            <div className="p-8 flex items-center justify-between group">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
                        <Bot className="w-6 h-6 text-white" />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-xl font-bold text-white tracking-tight">vellarys</span>
                        <span className="text-[10px] uppercase tracking-widest text-indigo-400 font-bold -mt-1">Intelligence</span>
                    </div>
                </div>
                <button
                    onClick={onClose}
                    className="lg:hidden p-2 hover:bg-slate-800 rounded-lg text-slate-400 transition-colors"
                >
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* 🧭 NAVIGATION: Scrolled area (sem barra visível) */}
            <nav className="flex-1 px-4 space-y-8 overflow-y-auto no-scrollbar py-4">
                {menuGroups.map((group, idx) => (
                    <div key={idx} className="space-y-2">
                        <h3 className="px-4 text-[11px] font-bold text-slate-500 uppercase tracking-[2px]">
                            {group.title}
                        </h3>
                        <ul className="space-y-1">
                            {group.items.map((item) => {
                                const isActive = pathname === item.href ||
                                    (item.href !== '/dashboard' && pathname.startsWith(item.href));

                                return (
                                    <li key={item.href}>
                                        <Link
                                            href={item.href}
                                            className={cn(
                                                "group flex items-center gap-3 px-4 py-3 rounded-xl transition-all relative overflow-hidden",
                                                isActive
                                                    ? "bg-indigo-600/10 text-white shadow-sm ring-1 ring-white/10"
                                                    : "text-slate-400 hover:text-white hover:bg-white/[0.03]"
                                            )}
                                        >
                                            {/* Active Indicator Bar */}
                                            {isActive && (
                                                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-indigo-500 rounded-r-full shadow-lg shadow-indigo-500/50" />
                                            )}

                                            <item.icon className={cn(
                                                "w-5 h-5 transition-transform group-hover:scale-110",
                                                isActive ? "text-indigo-400" : "text-slate-500 group-hover:text-indigo-300"
                                            )} />

                                            <span className="text-sm font-medium flex-1">{item.label}</span>

                                            {item.badge && (
                                                <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                                                    {item.badge}
                                                </span>
                                            )}

                                            {!isActive && (
                                                <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all text-slate-600" />
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
            <div className="p-4 border-t border-slate-800 bg-slate-900/50">
                <div className="flex items-center gap-3 p-3 rounded-2xl bg-slate-800/40 border border-white/5 mb-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm shadow-inner">
                        {user?.name?.charAt(0) || 'U'}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white truncate">{user?.name}</p>
                        <p className="text-[10px] text-slate-500 truncate">{user?.email}</p>
                    </div>
                    {isSuperAdmin && (
                        <Shield className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                    )}
                </div>

                <button
                    onClick={onLogout}
                    className="flex items-center gap-3 px-4 py-3 w-full text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-all font-medium text-sm"
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
