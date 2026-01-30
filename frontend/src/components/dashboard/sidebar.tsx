'use client';

/**
 * Sidebar - Menu lateral com controle de acesso por features
 * ==========================================================
 *
 * Usa o FeaturesContext para filtrar itens do menu baseado no plano do tenant.
 * Inspirado em grandes players como Salesforce, HubSpot e Intercom.
 */

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
    X,
    ChevronRight,
    LucideIcon,
    TrendingUp,
    Sparkles,
    BarChart3,
    Lock,
    Crown,
    FileText,
    Flame
} from 'lucide-react';
import { User } from '@/lib/auth';
import { useFeatures, Features } from '@/contexts/FeaturesContext';
import { cn } from '@/lib/utils';

// ============================================================================
// TIPOS
// ============================================================================

interface MenuItem {
    href: string;
    label: string;
    icon: LucideIcon;
    badge?: string;
    /**
     * Feature required to show this item.
     * If undefined, always shows.
     */
    feature?: keyof Features;
    /**
     * If true, this is a "lock" feature (enabled = blocked).
     * Used for security_export_lock_enabled.
     */
    isLockFeature?: boolean;
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

// ============================================================================
// COMPONENTE
// ============================================================================

export function Sidebar({ user, isOpen, onClose, onLogout }: SidebarProps) {
    const pathname = usePathname();
    const { features, isEnabled, isLoading } = useFeatures();

    const isSuperAdmin = user?.role === 'superadmin';
    const isGestor = user?.role === 'admin' || user?.role === 'gestor';
    const isSeller = user?.role === 'corretor' || user?.role === 'vendedor';

    /**
     * Retorna os grupos de menu baseado no role do usuário
     */
    const getMenuGroups = (): MenuGroup[] => {
        // =====================================================================
        // SUPERADMIN: Acesso total ao sistema
        // =====================================================================
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

        // =====================================================================
        // VENDEDOR: Apenas o que precisa para atender
        // =====================================================================
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
                    title: "Negociações",
                    items: [
                        { href: '/dashboard/opportunities', label: 'Oportunidades', icon: TrendingUp },
                    ]
                },
                {
                    title: "Ferramentas",
                    items: [
                        { href: '/dashboard/export', label: 'Exportar Dados', icon: FileDown, feature: 'export_enabled' },
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

        // =====================================================================
        // GESTOR: Visão gerencial completa
        // =====================================================================
        return [
            {
                title: "Operação",
                items: [
                    { href: '/dashboard', label: 'Visão Geral', icon: LayoutDashboard },
                    { href: '/dashboard/leads', label: 'Leads', icon: Users },
                    { href: '/dashboard/calendar', label: 'Calendário', icon: Calendar, feature: 'calendar_enabled' },
                ]
            },
            {
                title: "Negociações",
                items: [
                    { href: '/dashboard/opportunities', label: 'Oportunidades', icon: TrendingUp },
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
                    { href: '/dashboard/copilot', label: 'Vellarys Copilot', icon: Sparkles, badge: "AI", feature: 'copilot_enabled' },
                    { href: '/dashboard/simulator', label: 'Simulador IA', icon: Bot, badge: "Lab", feature: 'simulator_enabled' },
                    { href: '/dashboard/phoenix', label: 'Phoenix Engine', icon: Flame, badge: "Beta" },
                ]
            },
            {
                title: "Administração",
                items: [
                    { href: '/dashboard/export', label: 'Exportar Dados', icon: FileDown, feature: 'export_enabled' },
                    { href: '/dashboard/settings', label: 'Configurações', icon: Settings },
                ]
            }
        ];
    };

    /**
     * Verifica se um item deve ser exibido baseado na feature
     */
    const shouldShowItem = (item: MenuItem): boolean => {
        // Sem feature definida = sempre mostra
        if (!item.feature) return true;

        // SuperAdmin sempre vê tudo
        if (isSuperAdmin) return true;

        // Features ainda carregando = mostra (evita flicker)
        if (isLoading || !features) return true;

        // Lock features: habilitado = bloqueado
        if (item.isLockFeature) {
            // Se o lock está ATIVO, esconde o item
            return !isEnabled(item.feature);
        }

        // Features normais: habilitado = mostra
        return isEnabled(item.feature);
    };

    const menuGroups = getMenuGroups();

    return (
        <aside
            className={cn(
                "fixed left-0 top-0 h-full w-72 bg-white border-r border-slate-200 z-50 flex flex-col transition-all duration-300 ease-in-out select-none",
                isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
            )}
        >
            {/* HEADER: Logo & Brand */}
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

            {/* NAVIGATION */}
            <nav className="flex-1 px-4 space-y-7 overflow-y-auto no-scrollbar py-2">
                {menuGroups.map((group, idx) => {
                    // Filtra itens que devem ser mostrados
                    const visibleItems = group.items.filter(shouldShowItem);

                    // Se não tem itens visíveis, não mostra o grupo
                    if (visibleItems.length === 0) return null;

                    return (
                        <div key={idx} className="space-y-1.5">
                            <h3 className="px-4 text-[10px] font-bold text-slate-400 uppercase tracking-[2px]">
                                {group.title}
                            </h3>
                            <ul className="space-y-0.5">
                                {visibleItems.map((item) => {
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
                    );
                })}
            </nav>

            {/* FOOTER: Profile & Logout */}
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
