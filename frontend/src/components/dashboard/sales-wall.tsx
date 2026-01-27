'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { createPortal } from 'react-dom';
import {
    Trophy,
    Target,
    TrendingUp,
    DollarSign,
    X,
    Maximize,
    Minimize,
    ChevronLeft,
    ChevronRight,
    TrendingDown,
    Users,
    AlertCircle,
    BarChart3,
    Activity,
    Award,
    Calendar,
    Zap,
    Flame,
    Star,
    Crown,
    Medal,
    Sparkles,
    Clock,
    TrendingDownIcon
} from 'lucide-react';
import { Card } from '@/components/ui/card';

// =============================================
// TYPES & INTERFACES
// =============================================

interface SalesWallProps {
    metrics: any;
    salesData: {
        goal: any;
        metrics: any;
    };
    onClose: () => void;
}

interface Badge {
    id: string;
    title: string;
    description: string;
    icon: any;
    color: string;
    unlocked: boolean;
    progress?: number;
    requirement?: number;
}

// =============================================
// UTILITIES
// =============================================

function formatCurrency(cents: number): string {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(cents / 100);
}

const NumberTicker = ({ value, prefix = "", suffix = "", decimalPlaces = 0 }: { value: number, prefix?: string, suffix?: string, decimalPlaces?: number }) => {
    const [displayValue, setDisplayValue] = useState(0);

    useEffect(() => {
        let start = displayValue;
        const end = value;
        const duration = 1500;
        let startTime: number | null = null;

        const animate = (timestamp: number) => {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            const current = start + (end - start) * (1 - Math.pow(1 - progress, 3)); // Ease out cubic
            setDisplayValue(current);
            if (progress < 1) requestAnimationFrame(animate);
        };

        requestAnimationFrame(animate);
    }, [value]);

    return (
        <span>
            {prefix}{displayValue.toLocaleString('pt-BR', {
                minimumFractionDigits: decimalPlaces,
                maximumFractionDigits: decimalPlaces
            })}{suffix}
        </span>
    );
};

// =============================================
// MAIN COMPONENT
// =============================================

export function SalesWall({ metrics, salesData, onClose }: SalesWallProps) {
    const [currentView, setCurrentView] = useState(0);
    const [lastDealsCount, setLastDealsCount] = useState(salesData.metrics?.total_deals || 0);
    const [showCelebration, setShowCelebration] = useState(false);
    const [direction, setDirection] = useState<'next' | 'prev'>('next');
    const [isFullscreen, setIsFullscreen] = useState(false);
    const containerRef = useRef<HTMLDivElement | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        // Desabilitar scroll no body ao abrir
        document.body.style.overflow = 'hidden';
        return () => {
            document.body.style.overflow = 'unset';
        };
    }, []);

    const views = ['goal', 'ranking', 'latest', 'badges', 'evolution'];

    // Fullscreen handlers
    const toggleFullscreen = useCallback(async () => {
        if (!containerRef.current) return;

        try {
            if (!document.fullscreenElement) {
                await containerRef.current.requestFullscreen();
                setIsFullscreen(true);
            } else {
                await document.exitFullscreen();
                setIsFullscreen(false);
            }
        } catch (err) {
            console.error('Erro ao alternar fullscreen:', err);
        }
    }, []);

    // Detecta mudanças de fullscreen (ESC ou F11)
    useEffect(() => {
        const handleFullscreenChange = () => {
            setIsFullscreen(!!document.fullscreenElement);
        };

        document.addEventListener('fullscreenchange', handleFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
    }, []);

    // Auto-rotation
    useEffect(() => {
        const timer = setInterval(() => {
            setDirection('next');
            setCurrentView((prev) => (prev + 1) % views.length);
        }, 20000); // Aumentado para 20s para dar tempo de ver mais conteúdo

        return () => clearInterval(timer);
    }, []);

    // Celebration detection
    useEffect(() => {
        const currentCount = salesData.metrics?.total_deals || 0;
        if (currentCount > lastDealsCount) {
            triggerCelebration();
        }
        setLastDealsCount(currentCount);
    }, [salesData.metrics?.total_deals]);

    const triggerCelebration = () => {
        setShowCelebration(true);
        if (audioRef.current) {
            audioRef.current.currentTime = 0;
            audioRef.current.play().catch(() => { });
        }
        setTimeout(() => setShowCelebration(false), 8000);
    };

    const nextView = () => {
        setDirection('next');
        setCurrentView((prev) => (prev + 1) % views.length);
    };

    const prevView = () => {
        setDirection('prev');
        setCurrentView((prev) => (prev - 1 + views.length) % views.length);
    };

    // Calcula badges baseado nas métricas
    const badges: Badge[] = useMemo(() => {
        const totalDeals = salesData.metrics?.total_deals || 0;
        const conversionRate = salesData.metrics?.conversion_rate || 0;
        const dealsToday = salesData.metrics?.deals_today || 0;
        const averageTicket = salesData.metrics?.average_ticket || 0;

        return [
            {
                id: 'first_sale',
                title: 'Primeira Venda',
                description: 'Realize sua primeira venda',
                icon: Star,
                color: 'from-blue-500 to-cyan-500',
                unlocked: totalDeals >= 1,
            },
            {
                id: 'hot_streak',
                title: 'Sequência Quente',
                description: '5 vendas em um único dia',
                icon: Flame,
                color: 'from-orange-500 to-red-500',
                unlocked: dealsToday >= 5,
                progress: dealsToday,
                requirement: 5,
            },
            {
                id: 'sales_master',
                title: 'Mestre das Vendas',
                description: '50 vendas no total',
                icon: Crown,
                color: 'from-yellow-500 to-amber-500',
                unlocked: totalDeals >= 50,
                progress: totalDeals,
                requirement: 50,
            },
            {
                id: 'conversion_expert',
                title: 'Expert em Conversão',
                description: 'Taxa de conversão acima de 30%',
                icon: Target,
                color: 'from-green-500 to-emerald-500',
                unlocked: conversionRate >= 30,
                progress: conversionRate,
                requirement: 30,
            },
            {
                id: 'high_ticket',
                title: 'Ticket Premium',
                description: 'Ticket médio acima de R$ 5.000',
                icon: Medal,
                color: 'from-purple-500 to-pink-500',
                unlocked: averageTicket >= 500000, // 5000 * 100 (centavos)
                progress: averageTicket / 100,
                requirement: 5000,
            },
            {
                id: 'century',
                title: 'Centenário',
                description: '100 vendas realizadas',
                icon: Trophy,
                color: 'from-indigo-500 to-violet-500',
                unlocked: totalDeals >= 100,
                progress: totalDeals,
                requirement: 100,
            },
        ];
    }, [salesData.metrics]);

    if (!mounted) return null;

    const content = (
        <div
            ref={containerRef}
            className={`fixed inset-0 z-[9999] bg-slate-950 text-white flex flex-col overflow-hidden font-sans select-none animate-in fade-in duration-500 ${isFullscreen ? 'w-screen h-screen' : ''}`}
            style={{
                width: '100vw',
                height: '100vh',
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0
            }}
        >
            {/* ADVANCED BACKGROUND */}
            <div className="absolute inset-0 pointer-events-none">
                {/* Animated Glows */}
                <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-indigo-600/30 rounded-full blur-[150px] animate-pulse" />
                <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-emerald-600/20 rounded-full blur-[150px] animate-pulse [animation-delay:2s]" />

                {/* Tech Grid */}
                <div className="absolute inset-0" style={{
                    backgroundImage: `radial-gradient(circle at 1px 1px, rgba(255,255,255,0.05) 1px, transparent 0)`,
                    backgroundSize: '40px 40px'
                }} />

                {/* Vertical Scanning Line */}
                <div className="absolute inset-y-0 w-[1px] bg-indigo-500/20 left-1/4 animate-scan-line" />
                <div className="absolute inset-y-0 w-[1px] bg-indigo-500/20 left-3/4 animate-scan-line [animation-delay:3s]" />
            </div>

            {/* HEADER */}
            <div className="relative z-10 px-6 py-3 flex items-center justify-between border-b border-white/5 bg-black/40 backdrop-blur-xl flex-shrink-0">
                <div className="flex items-center gap-4">
                    <div className="relative group">
                        <div className="absolute inset-0 bg-indigo-500 blur-xl opacity-50 group-hover:opacity-100 transition-opacity" />
                        <div className="relative w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-2xl skew-x-[-6deg]">
                            <TrendingUp className="w-7 h-7 text-slate-950" />
                        </div>
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h1 className="text-2xl font-black tracking-tighter uppercase italic bg-clip-text text-transparent bg-gradient-to-r from-white via-white to-white/50">
                                DASHBOARD <span className="text-indigo-500">REALTIME</span>
                            </h1>
                            <span className="px-1.5 py-0.5 bg-indigo-500/20 border border-indigo-500/30 text-[8px] font-black text-indigo-400 rounded-md tracking-tighter uppercase italic">v2.0</span>
                        </div>
                        <p className="text-slate-500 text-[10px] font-bold tracking-[0.2em] uppercase mt-0.5">Sincronizado com Vellarys AI Engine</p>
                    </div>
                </div>

                <div className="flex items-center gap-6">
                    <div className="hidden lg:flex gap-6">
                        <div className="text-center">
                            <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-0.5">Vendas Hoje</p>
                            <p className="text-lg font-black text-white">{salesData.metrics?.deals_today || 0}</p>
                        </div>
                        <div className="text-center">
                            <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-0.5">Taxa de Conversão</p>
                            <p className="text-lg font-black text-emerald-400">{salesData.metrics?.conversion_rate?.toFixed(1)}%</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3 border-l border-white/10 pl-6">
                        <div className="flex flex-col items-end">
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] font-black tracking-widest text-emerald-500 animate-pulse uppercase">Conectado</span>
                                <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full shadow-[0_0_15px_#10b981] animate-ping" />
                            </div>
                            <span className="text-[9px] font-bold text-slate-500 tabular-nums">LIVE SYNC: {new Date().toLocaleTimeString()}</span>
                        </div>

                        {/* Botão Fullscreen */}
                        <button
                            onClick={toggleFullscreen}
                            className="w-12 h-12 flex items-center justify-center bg-white/5 hover:bg-indigo-500/20 hover:text-indigo-500 rounded-2xl border border-white/10 transition-all active:scale-90 group"
                            title={isFullscreen ? 'Sair da Tela Cheia' : 'Tela Cheia'}
                        >
                            {isFullscreen ? (
                                <Minimize className="w-6 h-6 transition-transform group-hover:scale-110" />
                            ) : (
                                <Maximize className="w-6 h-6 transition-transform group-hover:scale-110" />
                            )}
                        </button>

                        {/* Botão Fechar */}
                        <button
                            onClick={onClose}
                            className="w-12 h-12 flex items-center justify-center bg-white/5 hover:bg-rose-500/20 hover:text-rose-500 rounded-2xl border border-white/10 transition-all active:scale-90 group"
                            title="Fechar Modo TV"
                        >
                            <X className="w-6 h-6 transition-transform group-hover:rotate-90" />
                        </button>
                    </div>
                </div>
            </div>

            {/* CONTENT AREA WITH TRANSITIONS */}
            <div className="flex-1 relative z-10 px-4 py-4 overflow-hidden flex flex-col items-center justify-center min-h-0">
                <div key={currentView} className={`w-full h-full flex items-center justify-center animate-view-entry-${direction}`}>
                    {views[currentView] === 'goal' && <GoalView goal={salesData.goal} />}
                    {views[currentView] === 'ranking' && <RankingView metrics={salesData.metrics} />}
                    {views[currentView] === 'latest' && <InsightsView metrics={salesData.metrics} />}
                    {views[currentView] === 'badges' && <BadgesView badges={badges} />}
                    {views[currentView] === 'evolution' && <EvolutionView metrics={salesData.metrics} goal={salesData.goal} />}
                </div>
            </div>

            {/* FOOTER CONTROLS */}
            <div className="relative z-10 px-8 py-6 flex items-center justify-between bg-black/20 backdrop-blur-md flex-shrink-0">
                <div className="flex gap-3">
                    <button onClick={prevView} className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-all group active:scale-95">
                        <ChevronLeft className="w-6 h-6 text-slate-400 group-hover:text-white" />
                    </button>
                    <button onClick={nextView} className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-all group active:scale-95">
                        <ChevronRight className="w-6 h-6 text-slate-400 group-hover:text-white" />
                    </button>
                </div>

                <div className="flex flex-col items-center gap-4">
                    <div className="flex gap-3">
                        {views.map((_, i) => (
                            <div
                                key={i}
                                className={`h-1.5 rounded-full transition-all duration-700 ease-out ${i === currentView ? 'w-20 bg-indigo-500 shadow-[0_0_20px_#6366f1]' : 'w-3 bg-white/20'}`}
                            />
                        ))}
                    </div>
                    <span className="text-[10px] font-black text-slate-500 tracking-[0.4em] uppercase">
                        Módulo de Visualização {currentView + 1}/{views.length}
                    </span>
                </div>

                <div className="flex items-center gap-3 bg-white/5 border border-white/10 px-4 py-2 rounded-xl backdrop-blur-md">
                    <Activity className="w-4 h-4 text-indigo-400 animate-pulse" />
                    <div>
                        <p className="text-[9px] font-black text-slate-500 uppercase leading-none mb-0.5">Status do Ciclo</p>
                        <p className="text-[10px] font-black text-white">Transição Automática Ativa</p>
                    </div>
                </div>
            </div>

            {/* CELEBRATION OVERLAY */}
            {showCelebration && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/90 backdrop-blur-[40px] animate-in fade-in duration-500 overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-t from-indigo-950/50 to-transparent" />

                    <div className="relative z-10 text-center scale-up-center">
                        <div className="relative inline-block mb-10">
                            <div className="absolute inset-0 bg-yellow-400 blur-3xl opacity-30 animate-pulse" />
                            <Trophy className="w-56 h-56 text-yellow-400 drop-shadow-[0_0_50px_rgba(250,204,21,0.6)] animate-bounce" />
                            <Award className="absolute -bottom-4 -right-4 w-20 h-20 text-indigo-500 animate-spin-slow" />
                        </div>

                        <h2 className="text-9xl font-black text-white italic tracking-tighter mb-4 italic-custom shadow-glow-white">
                            VENDA CONFIRMADA!
                        </h2>

                        <div className="flex items-center justify-center gap-4 mb-8">
                            <Zap className="w-8 h-8 text-yellow-400 fill-yellow-400" />
                            <p className="text-3xl font-black text-white uppercase tracking-[0.2em]">
                                PERFORMANCE ACIMA DA MÉDIA
                            </p>
                            <Zap className="w-8 h-8 text-yellow-400 fill-yellow-400" />
                        </div>

                        <div className="px-12 py-4 bg-white/10 border border-white/20 rounded-full inline-block backdrop-blur-md">
                            <p className="text-xl font-bold text-slate-300">Atualizando indicadores estratégicos...</p>
                        </div>
                    </div>

                    {/* CONFETTI */}
                    <div className="absolute inset-0 pointer-events-none overflow-hidden">
                        {[...Array(60)].map((_, i) => (
                            <div
                                key={i}
                                className="absolute animate-confetti-fall"
                                style={{
                                    left: `${Math.random() * 100}%`,
                                    top: `-20px`,
                                    backgroundColor: ['#facc15', '#10b981', '#6366f1', '#ec4899', '#ffffff'][Math.floor(Math.random() * 5)],
                                    width: `${4 + Math.random() * 8}px`,
                                    height: `${8 + Math.random() * 12}px`,
                                    borderRadius: '2px',
                                    animationDelay: `${Math.random() * 3}s`,
                                    animationDuration: `${2 + Math.random() * 4}s`
                                }}
                            />
                        ))}
                    </div>
                </div>
            )}

            <audio ref={audioRef} src="https://assets.mixkit.co/active_storage/sfx/2013/2013-preview.mp3" />

            <style jsx global>{`
                @keyframes scan-line {
                    0% { transform: translateY(-100%); }
                    100% { transform: translateY(100vh); }
                }
                .animate-scan-line {
                    animation: scan-line 6s linear infinite;
                }
                @keyframes confetti-fall {
                    0% { transform: translateY(0) rotate(0); opacity: 1; }
                    100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
                }
                .animate-confetti-fall {
                    animation: confetti-fall linear forwards;
                }
                @keyframes view-entry-next {
                    from { opacity: 0; transform: translateX(100px) scale(0.95); filter: blur(10px); }
                    to { opacity: 1; transform: translateX(0) scale(1); filter: blur(0); }
                }
                @keyframes view-entry-prev {
                    from { opacity: 0; transform: translateX(-100px) scale(0.95); filter: blur(10px); }
                    to { opacity: 1; transform: translateX(0) scale(1); filter: blur(0); }
                }
                .animate-view-entry-next {
                    animation: view-entry-next 1s cubic-bezier(0.23, 1, 0.32, 1) forwards;
                }
                .animate-view-entry-prev {
                    animation: view-entry-prev 1s cubic-bezier(0.23, 1, 0.32, 1) forwards;
                }
                .italic-custom { font-style: italic; }
                .shadow-glow-white { filter: drop-shadow(0 0 20px rgba(255,255,255,0.4)); }
                @keyframes spin-slow {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                .animate-spin-slow {
                    animation: spin-slow 8s linear infinite;
                }
                .scale-up-center {
                    animation: scale-up-center 0.6s cubic-bezier(0.390, 0.575, 0.565, 1.000) both;
                }
                @keyframes scale-up-center {
                    0% { transform: scale(0.5); opacity: 0; }
                    100% { transform: scale(1); opacity: 1; }
                }
            `}</style>
        </div>
    );

    return createPortal(content, document.body);
}

// =============================================
// SUB-VIEWS
// =============================================

function GoalView({ goal }: { goal: any }) {
    const progress = goal?.revenue_progress || 0;

    // SVG Circular Chart constants - REDUZIDO para caber na tela
    const size = 320;
    const strokeWidth = 24;
    const center = size / 2;
    const radius = center - strokeWidth;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (Math.min(progress, 100) / 100) * circumference;

    return (
        <div className="flex flex-col lg:flex-row items-center justify-center gap-8 max-w-6xl mx-auto px-6">
            {/* LARGE PERCENTAGE CIRCLE */}
            <div className="relative flex items-center justify-center flex-shrink-0">
                <svg width={size} height={size} className="transform -rotate-90 drop-shadow-[0_0_30px_rgba(99,102,241,0.3)]">
                    {/* Background Circle */}
                    <circle
                        cx={center} cy={center} r={radius}
                        stroke="rgba(255,255,255,0.05)"
                        strokeWidth={strokeWidth}
                        fill="transparent"
                    />
                    {/* Progress Circle lines */}
                    <circle
                        cx={center} cy={center} r={radius}
                        stroke="url(#gradient-goal)"
                        strokeWidth={strokeWidth}
                        strokeDasharray={circumference}
                        strokeDashoffset={offset}
                        strokeLinecap="round"
                        fill="transparent"
                        className="transition-all duration-2000 ease-out"
                    />
                    <defs>
                        <linearGradient id="gradient-goal" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#6366f1" />
                            <stop offset="100%" stopColor="#10b981" />
                        </linearGradient>
                    </defs>
                </svg>

                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                    <p className="text-xs font-black text-slate-500 uppercase tracking-[0.3em] mb-1">Progresso</p>
                    <h2 className="text-[5.5rem] font-black tracking-tighter leading-none italic drop-shadow-2xl">
                        <NumberTicker value={progress} decimalPlaces={1} />
                        <span className="text-2xl text-indigo-500 font-black ml-1">%</span>
                    </h2>
                </div>
            </div>

            {/* STATS CARDS */}
            <div className="flex flex-col gap-4 w-full max-w-md flex-1">
                <div className="group bg-white/5 border-l-4 border-indigo-500 p-4 rounded-tr-xl rounded-br-xl backdrop-blur-md transition-all hover:bg-white/10 hover:translate-x-2">
                    <div className="flex items-center gap-2 mb-2">
                        <DollarSign className="w-4 h-4 text-indigo-400" />
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-wider">Receita Realizada</p>
                    </div>
                    <p className="text-3xl font-black text-white tracking-tighter tabular-nums">
                        {formatCurrency(goal?.revenue_actual || 0)}
                    </p>
                </div>

                <div className="group bg-white/5 border-l-4 border-slate-500 p-4 rounded-tr-xl rounded-br-xl backdrop-blur-md transition-all hover:bg-white/10 hover:translate-x-2">
                    <div className="flex items-center gap-2 mb-2">
                        <Target className="w-4 h-4 text-slate-400" />
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-wider">Objetivo do Mês</p>
                    </div>
                    <p className="text-3xl font-black text-slate-300 tracking-tighter tabular-nums">
                        {formatCurrency(goal?.revenue_goal || 0)}
                    </p>
                </div>

                <div className="flex items-center gap-3 bg-indigo-600 p-4 rounded-xl shadow-[0_15px_30px_rgba(99,102,241,0.4)] relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-20 h-20 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2 scale-150 blur-2xl" />
                    <Calendar className="w-8 h-8 text-white shrink-0 group-hover:scale-110 transition-transform duration-500" />
                    <div>
                        <p className="text-[9px] font-black text-white/60 uppercase tracking-widest mb-0.5">Time to Deadline</p>
                        <p className="text-3xl font-black text-white tracking-tighter italic">{goal?.days_remaining || 0} Dias</p>
                    </div>
                </div>
            </div>
        </div>
    );
}

function RankingView({ metrics }: { metrics: any }) {
    const ranking = metrics?.seller_ranking || [];

    return (
        <div className="w-full space-y-10 max-w-7xl mx-auto px-8">
            <div className="flex items-end justify-between border-b-2 border-white/5 pb-6">
                <div className="flex items-center gap-4">
                    <div className="w-16 h-16 bg-amber-500/10 border border-amber-500/30 rounded-2xl flex items-center justify-center">
                        <Trophy className="w-10 h-10 text-amber-500" />
                    </div>
                    <div>
                        <h2 className="text-5xl font-black tracking-tighter uppercase italic">LEADERBOARD</h2>
                        <p className="text-slate-500 font-bold uppercase tracking-[0.3em] text-xs">Performance Individual de Elite</p>
                    </div>
                </div>

                <div className="flex gap-3">
                    <div className="bg-white/5 px-4 py-3 rounded-xl border border-white/10 text-center">
                        <p className="text-[9px] font-black text-slate-500 uppercase tracking-wider mb-1">Top Conversão</p>
                        <p className="text-xl font-black text-amber-500">
                            {ranking.length > 0 ? Math.max(...ranking.map((s: any) => s.conversion_rate)).toFixed(1) : 0}%
                        </p>
                    </div>
                </div>
            </div>

            <div className="flex flex-col gap-3">
                {ranking.map((seller: any, index: number) => (
                    <div
                        key={seller.seller_id}
                        className={`group relative flex items-center gap-6 p-3 pl-6 rounded-[1.5rem] border transition-all duration-500
                            ${index === 0
                                ? 'bg-gradient-to-r from-amber-500/20 via-slate-900/50 to-transparent border-amber-500/40 py-6 scale-[1.02] shadow-[0_20px_40px_-12px_rgba(245,158,11,0.2)]'
                                : 'bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/20'}`}
                    >
                        {/* Rank Number */}
                        <div className={`relative w-16 h-16 shrink-0 rounded-xl flex items-center justify-center text-3xl font-black skew-x-[-8deg]
                            ${index === 0 ? 'bg-amber-500 text-slate-950 shadow-[0_0_15px_#f59e0b]' :
                                index === 1 ? 'bg-slate-300 text-slate-950' :
                                    index === 2 ? 'bg-orange-600 text-white' :
                                        'bg-white/10 text-white'}`}>
                            {index + 1}
                        </div>

                        {/* Seller Data */}
                        <div className="flex-1 min-w-0">
                            <h3 className="text-3xl font-extrabold text-white tracking-tight truncate mb-1">{seller.seller_name}</h3>
                            <div className="flex gap-6">
                                <div className="flex items-center gap-1.5">
                                    <div className="w-2 h-2 bg-emerald-500 rounded-full" />
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-wider">
                                        Conversão: <span className="text-white">{seller.conversion_rate.toFixed(1)}%</span>
                                    </p>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <div className="w-2 h-2 bg-indigo-500 rounded-full" />
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-wider">
                                        Volume: <span className="text-white">{seller.leads_assigned} Leads</span>
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Visual Progress Bar (Background) */}
                        <div className="absolute bottom-0 left-[120px] right-0 h-0.5 bg-white/5 rounded-full overflow-hidden opacity-50 group-hover:opacity-100 transition-opacity">
                            <div className={`h-full animate-grow-width ${index === 0 ? 'bg-amber-500' : 'bg-white/50'}`} style={{ width: `${(seller.deals_count / (ranking[0]?.deals_count || 1)) * 100}%` }} />
                        </div>

                        {/* Deals Count */}
                        <div className="text-right pr-6">
                            <h4 className={`text-5xl font-black leading-none italic ${index === 0 ? 'text-amber-500' : 'text-white/80'}`}>
                                <NumberTicker value={seller.deals_count} />
                            </h4>
                            <p className="text-[9px] font-black text-slate-500 uppercase tracking-[0.2em] mt-0.5">Concluídas</p>
                        </div>
                    </div>
                ))}

                {ranking.length === 0 && (
                    <div className="text-center py-20 border-2 border-dashed border-white/5 rounded-[2rem] bg-white/[0.02]">
                        <Users className="w-20 h-20 text-white/5 mx-auto mb-6 animate-pulse" />
                        <h3 className="text-2xl font-black text-white/20 uppercase tracking-[0.4em]">Processando Ranking Semanal</h3>
                    </div>
                )}
            </div>
        </div>
    );
}

function BadgesView({ badges }: { badges: Badge[] }) {
    const unlockedCount = badges.filter(b => b.unlocked).length;

    return (
        <div className="w-full flex flex-col gap-8 max-w-7xl mx-auto px-8">
            {/* Header */}
            <div className="flex items-center justify-between border-b-2 border-white/5 pb-6">
                <div className="flex items-center gap-4">
                    <div className="w-16 h-16 bg-indigo-500/10 border border-indigo-500/30 rounded-2xl flex items-center justify-center">
                        <Sparkles className="w-10 h-10 text-indigo-500" />
                    </div>
                    <div>
                        <h2 className="text-5xl font-black tracking-tighter uppercase italic">CONQUISTAS</h2>
                        <p className="text-slate-500 font-bold uppercase tracking-[0.3em] text-xs">
                            {unlockedCount}/{badges.length} Desbloqueadas
                        </p>
                    </div>
                </div>

                <div className="bg-white/5 px-6 py-3 rounded-xl border border-white/10">
                    <p className="text-[9px] font-black text-slate-500 uppercase tracking-wider mb-1">Progresso Geral</p>
                    <p className="text-3xl font-black text-indigo-500">
                        {((unlockedCount / badges.length) * 100).toFixed(0)}%
                    </p>
                </div>
            </div>

            {/* Badges Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-5">
                {badges.map((badge) => {
                    const Icon = badge.icon;
                    return (
                        <div
                            key={badge.id}
                            className={`group relative bg-white/[0.03] border rounded-[1.5rem] p-5 transition-all duration-500
                                ${badge.unlocked
                                    ? 'border-white/20 hover:bg-white/10 hover:scale-105 hover:shadow-[0_15px_30px_rgba(99,102,241,0.3)]'
                                    : 'border-white/5 grayscale opacity-40'
                                }`}
                        >
                            {/* Glow Effect */}
                            {badge.unlocked && (
                                <div className={`absolute inset-0 bg-gradient-to-br ${badge.color} opacity-0 group-hover:opacity-10 blur-xl transition-opacity duration-500 rounded-[1.5rem]`} />
                            )}

                            {/* Icon */}
                            <div className={`relative w-16 h-16 rounded-xl flex items-center justify-center mb-4 transition-all duration-500
                                ${badge.unlocked
                                    ? `bg-gradient-to-br ${badge.color} shadow-lg group-hover:scale-110`
                                    : 'bg-white/5'
                                }`}
                            >
                                <Icon className={`w-8 h-8 ${badge.unlocked ? 'text-white' : 'text-white/20'}`} />
                            </div>

                            {/* Content */}
                            <h3 className={`text-lg font-black mb-1 ${badge.unlocked ? 'text-white' : 'text-white/30'}`}>
                                {badge.title}
                            </h3>
                            <p className="text-xs text-slate-400 font-medium mb-3">
                                {badge.description}
                            </p>

                            {/* Progress Bar */}
                            {!badge.unlocked && badge.progress !== undefined && badge.requirement && (
                                <div className="mt-3">
                                    <div className="flex justify-between text-[10px] font-bold text-slate-500 mb-1.5">
                                        <span>{badge.progress.toFixed(0)}</span>
                                        <span>{badge.requirement}</span>
                                    </div>
                                    <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full bg-gradient-to-r ${badge.color} transition-all duration-1000`}
                                            style={{ width: `${Math.min((badge.progress / badge.requirement) * 100, 100)}%` }}
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Unlocked Badge */}
                            {badge.unlocked && (
                                <div className="absolute top-3 right-3">
                                    <div className="bg-emerald-500 px-2 py-0.5 rounded-full flex items-center gap-1">
                                        <Star className="w-2.5 h-2.5 text-white fill-white" />
                                        <span className="text-[8px] font-black text-white uppercase">Conquistado</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function EvolutionView({ metrics, goal }: { metrics: any; goal: any }) {
    const dealsToday = metrics?.deals_today || 0;
    const dealsThisWeek = metrics?.deals_this_week || 0;
    const dealsThisMonth = metrics?.total_deals || 0;
    const daysRemaining = goal?.days_remaining || 0;
    const dailyTarget = daysRemaining > 0 ? Math.ceil((goal?.revenue_goal - goal?.revenue_actual) / 100 / daysRemaining) : 0;

    return (
        <div className="w-full flex flex-col gap-8 max-w-7xl mx-auto px-8">
            {/* Header */}
            <div className="flex items-center justify-center gap-4">
                <div className="w-12 h-1 bg-emerald-500 rounded-full" />
                <h2 className="text-2xl font-black tracking-tighter uppercase italic px-4">
                    EVOLUÇÃO & PERFORMANCE
                </h2>
                <div className="w-12 h-1 bg-emerald-500 rounded-full" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Daily Performance */}
                <div className="bg-white/[0.03] border border-white/5 rounded-[1.5rem] p-6 relative overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />

                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center">
                            <Clock className="w-7 h-7 text-emerald-400" />
                        </div>
                        <div>
                            <p className="text-xs font-black text-slate-400 uppercase tracking-wide">Vendas Hoje</p>
                            <p className="text-[10px] font-bold text-slate-500">Performance Diária</p>
                        </div>
                    </div>

                    <div className="flex items-end gap-3 mb-4">
                        <h3 className="text-[5rem] font-black italic tracking-tighter text-emerald-500 leading-none drop-shadow-2xl">
                            <NumberTicker value={dealsToday} />
                        </h3>
                        <div className="pb-3">
                            <p className="text-lg font-black text-white mb-0.5">vendas</p>
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">concluídas</p>
                        </div>
                    </div>

                    {/* Meta Diária */}
                    <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                        <div className="flex items-center justify-between mb-3">
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-wider">Meta Diária Recomendada</p>
                            <Target className="w-4 h-4 text-indigo-400" />
                        </div>
                        <p className="text-3xl font-black text-white">
                            R$ {dailyTarget.toLocaleString('pt-BR')}
                        </p>
                        <p className="text-[10px] text-slate-500 mt-1.5">
                            Para atingir meta mensal em {daysRemaining} dias
                        </p>
                    </div>
                </div>

                {/* Weekly & Monthly */}
                <div className="flex flex-col gap-4">
                    {/* This Week */}
                    <div className="flex-1 bg-white/[0.03] border border-white/5 rounded-[1.5rem] p-6 relative overflow-hidden group">
                        <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />

                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 bg-indigo-500/20 rounded-xl flex items-center justify-center">
                                <Calendar className="w-6 h-6 text-indigo-400" />
                            </div>
                            <span className="text-xs font-black text-slate-400 uppercase tracking-wide">Esta Semana</span>
                        </div>

                        <div className="flex items-baseline gap-3">
                            <p className="text-6xl font-black text-white tracking-tighter">
                                <NumberTicker value={dealsThisWeek} />
                            </p>
                            <div>
                                <TrendingUp className="w-6 h-6 text-emerald-500 mb-1" />
                                <p className="text-[10px] font-black text-slate-500 uppercase">Vendas</p>
                            </div>
                        </div>

                        {/* Progress Bar */}
                        <div className="mt-4 h-2.5 bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full bg-indigo-500 rounded-full shadow-[0_0_15px_rgba(99,102,241,0.5)]"
                                style={{ width: `${Math.min((dealsThisWeek / 20) * 100, 100)}%` }}
                            />
                        </div>
                    </div>

                    {/* This Month */}
                    <div className="flex-1 bg-white/[0.03] border border-white/5 rounded-[1.5rem] p-6 relative overflow-hidden group">
                        <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />

                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 bg-purple-500/20 rounded-xl flex items-center justify-center">
                                <BarChart3 className="w-6 h-6 text-purple-400" />
                            </div>
                            <span className="text-xs font-black text-slate-400 uppercase tracking-wide">Este Mês</span>
                        </div>

                        <div className="flex items-baseline gap-3">
                            <p className="text-6xl font-black text-white tracking-tighter">
                                <NumberTicker value={dealsThisMonth} />
                            </p>
                            <div>
                                <Trophy className="w-6 h-6 text-amber-500 mb-1" />
                                <p className="text-[10px] font-black text-slate-500 uppercase">Total</p>
                            </div>
                        </div>

                        {/* Comparison */}
                        <div className="mt-4 flex items-center gap-2 py-1.5 px-3 bg-white/5 rounded-full border border-white/5">
                            <Activity className="w-3.5 h-3.5 text-purple-400" />
                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider">
                                Crescimento: <span className="text-emerald-500">+{metrics?.growth_percentage?.toFixed(0) || 0}%</span>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function InsightsView({ metrics }: { metrics: any }) {
    return (
        <div className="w-full flex flex-col gap-6 max-w-7xl mx-auto px-6">
            <div className="flex items-center justify-center gap-4">
                <div className="w-12 h-1 bg-indigo-500 rounded-full" />
                <h2 className="text-2xl font-black tracking-tighter uppercase italic px-4">INSIGHTS ESTRATÉGICOS</h2>
                <div className="w-12 h-1 bg-indigo-500 rounded-full" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* LARGE METRIC - CLOSED DEALS */}
                <div className="bg-white/[0.03] border border-white/5 rounded-[1.5rem] p-6 relative overflow-hidden group">
                    <div className="absolute -top-8 -right-8 w-48 h-48 bg-emerald-500/10 blur-[60px] rounded-full group-hover:bg-emerald-500/20 transition-all duration-700" />

                    <div className="flex items-center gap-3 mb-3">
                        <Award className="w-8 h-8 text-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.5)]" />
                        <span className="text-base font-black text-slate-500 uppercase tracking-wide">Total Conversões Mês</span>
                    </div>

                    <div className="flex items-baseline gap-3">
                        <h3 className="text-[5.5rem] font-black italic tracking-tighter text-white drop-shadow-2xl leading-none">
                            <NumberTicker value={metrics?.total_deals || 0} />
                        </h3>
                        <div>
                            <div className="flex items-center gap-2 text-emerald-500 mb-1">
                                <TrendingUp className="w-5 h-5" />
                                <span className="text-2xl font-black tabular-nums">+{metrics?.deals_this_week || 0}</span>
                            </div>
                            <p className="text-[10px] font-black text-slate-500 uppercase tracking-wider">Novas essa semana</p>
                        </div>
                    </div>

                    {/* Progress indicator bar at bottom */}
                    <div className="mt-8 h-3 bg-white/5 rounded-full overflow-hidden p-0.5 border border-white/10">
                        <div className="h-full bg-emerald-500 rounded-full animate-shine" style={{ width: '75%' }} />
                    </div>
                </div>

                {/* TWO MEDIUM CARDS */}
                <div className="flex flex-col gap-4">
                    <div className="flex-1 bg-white/[0.03] border border-white/5 rounded-[1.5rem] p-6 relative overflow-hidden group">
                        <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />

                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 bg-indigo-500/20 rounded-xl flex items-center justify-center">
                                <DollarSign className="w-6 h-6 text-indigo-400" />
                            </div>
                            <span className="text-xs font-black text-slate-400 uppercase tracking-wide">Ticket Médio por Operação</span>
                        </div>

                        <p className="text-5xl font-black text-white tracking-tighter tabular-nums mb-3">
                            <NumberTicker value={metrics?.average_ticket || 0} prefix="R$ " />
                        </p>
                        <div className="flex items-center gap-2 py-1.5 px-4 bg-white/5 rounded-full inline-flex border border-white/5">
                            <Activity className="w-3.5 h-3.5 text-indigo-400" />
                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider">Estabilidade: <span className="text-emerald-500">Alta</span></p>
                        </div>
                    </div>

                    <div className="flex-1 bg-white/[0.03] border border-white/5 rounded-[1.5rem] p-6 relative overflow-hidden group">
                        <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />

                        <div className="flex items-center gap-2 mb-3">
                            <div className="w-8 h-8 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                                <BarChart3 className="w-5 h-5 text-emerald-400" />
                            </div>
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-wide">Eficiência Global do Funil</span>
                        </div>

                        <div className="flex items-end gap-2 mb-3">
                            <p className="text-5xl font-black text-emerald-500 tracking-tighter leading-none italic">
                                <NumberTicker value={metrics?.conversion_rate || 0} decimalPlaces={1} />
                            </p>
                            <span className="text-2xl font-black text-emerald-700 pb-1">%</span>
                        </div>

                        <div className="w-full h-2.5 bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full bg-emerald-500 rounded-full shadow-[0_0_15px_rgba(16,185,129,0.5)]" style={{ width: `${(metrics?.conversion_rate || 0) * 2}%` }} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
