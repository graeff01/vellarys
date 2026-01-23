'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
    Trophy,
    Target,
    TrendingUp,
    DollarSign,
    X,
    Maximize,
    ChevronLeft,
    ChevronRight,
    TrendingDown,
    Users,
    AlertCircle
} from 'lucide-react';
import { Card } from '@/components/ui/card';

// =============================================
// TIPOS
// =============================================

interface SalesWallProps {
    metrics: any;
    salesData: {
        goal: any;
        metrics: any;
    };
    onClose: () => void;
}

// =============================================
// FORMATADORES
// =============================================

function formatCurrency(cents: number): string {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(cents / 100);
}

// =============================================
// COMPONENT
// =============================================

export function SalesWall({ metrics, salesData, onClose }: SalesWallProps) {
    const [currentView, setCurrentView] = useState(0);
    const [lastDealsCount, setLastDealsCount] = useState(salesData.metrics?.total_deals || 0);
    const [showCelebration, setShowCelebration] = useState(false);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    // Views para rotacionar
    const views = ['goal', 'ranking', 'latest'];

    // 1. Efeito de rotação automática
    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentView((prev) => (prev + 1) % views.length);
        }, 15000); // 15 segundos por view

        return () => clearInterval(timer);
    }, []);

    // 2. Detecção de nova venda (celebração!)
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
            audioRef.current.play().catch(e => console.log('Audio error:', e));
        }
        setTimeout(() => setShowCelebration(false), 10000);
    };

    const nextView = () => setCurrentView((prev) => (prev + 1) % views.length);
    const prevView = () => setCurrentView((prev) => (prev - 1 + views.length) % views.length);

    // 3. Renderização de cada Visão
    const renderView = () => {
        const view = views[currentView];

        switch (view) {
            case 'goal':
                return <GoalView goal={salesData.goal} metrics={salesData.metrics} />;
            case 'ranking':
                return <RankingView metrics={salesData.metrics} />;
            case 'latest':
                return <LatestDealsView metrics={salesData.metrics} />;
            default:
                return null;
        }
    };

    return (
        <div className="fixed inset-0 z-[100] bg-slate-950 text-white flex flex-col overflow-hidden font-sans select-none">
            {/* Background Decor */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-20">
                <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-indigo-600 rounded-full blur-[150px]" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-emerald-600 rounded-full blur-[150px]" />
            </div>

            {/* Header */}
            <div className="relative z-10 px-8 py-6 flex items-center justify-between border-b border-white/10 bg-black/20 backdrop-blur-md">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(255,255,255,0.3)]">
                        <TrendingUp className="w-8 h-8 text-slate-900" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-black tracking-tighter uppercase italic">MODO TV <span className="text-indigo-500">· VELLARIS SALES</span></h1>
                        <p className="text-slate-400 text-xs font-bold tracking-widest uppercase">Performance em Tempo Real</p>
                    </div>
                </div>

                <div className="flex items-center gap-6">
                    <div className="flex flex-col items-end">
                        <div className="text-xs font-bold text-slate-500 uppercase">Status</div>
                        <div className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_10px_#10b981]" />
                            <span className="text-sm font-black text-emerald-500">AO VIVO</span>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-3 hover:bg-white/10 rounded-full transition-colors"
                    >
                        <X className="w-8 h-8 text-white" />
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 relative z-10 flex flex-col items-center justify-center p-8">
                <div className="w-full max-w-7xl animate-in fade-in zoom-in duration-1000">
                    {renderView()}
                </div>
            </div>

            {/* Navigation & Progress */}
            <div className="relative z-10 p-8 flex items-center justify-between">
                <div className="flex gap-4">
                    <button onClick={prevView} className="p-4 bg-white/5 hover:bg-white/10 rounded-2xl transition-all active:scale-90 border border-white/10 group">
                        <ChevronLeft className="w-8 h-8 text-slate-400 group-hover:text-white" />
                    </button>
                    <button onClick={nextView} className="p-4 bg-white/5 hover:bg-white/10 rounded-2xl transition-all active:scale-90 border border-white/10 group">
                        <ChevronRight className="w-8 h-8 text-slate-400 group-hover:text-white" />
                    </button>
                </div>

                <div className="flex gap-2">
                    {views.map((_, i) => (
                        <div
                            key={i}
                            className={`h-2 rounded-full transition-all duration-500 ${i === currentView ? 'w-12 bg-indigo-500 shadow-[0_0_15px_#6366f1]' : 'w-2 bg-white/20'}`}
                        />
                    ))}
                </div>

                <div className="text-xs font-bold text-slate-500 tracking-[0.2em]">
                    PRÓXIMA ATUALIZAÇÃO EM 15S
                </div>
            </div>

            {/* Celebration Overlay */}
            {showCelebration && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-xl animate-in fade-in duration-500">
                    <div className="text-center animate-in zoom-in spin-in-1 duration-1000">
                        <div className="relative inline-block mb-8">
                            <Trophy className="w-48 h-48 text-yellow-400 drop-shadow-[0_0_50px_rgba(250,204,21,0.5)]" />
                            <div className="absolute inset-0 animate-ping opacity-20">
                                <Trophy className="w-48 h-48 text-yellow-400" />
                            </div>
                        </div>
                        <h2 className="text-7xl font-black text-white italic tracking-tighter mb-4 shadow-black drop-shadow-2xl">
                            VENDA CONFIRMADA!
                        </h2>
                        <p className="text-2xl font-bold text-yellow-400 uppercase tracking-[0.5em] animate-pulse">
                            META ATUALIZADA EM TEMPO REAL
                        </p>
                    </div>

                    {/* Custom CSS Confetti Fallback */}
                    <div className="absolute inset-0 pointer-events-none overflow-hidden">
                        {[...Array(50)].map((_, i) => (
                            <div
                                key={i}
                                className="absolute animate-confetti-fall"
                                style={{
                                    left: `${Math.random() * 100}%`,
                                    top: `-10px`,
                                    backgroundColor: ['#facc15', '#10b981', '#6366f1', '#ec4899'][Math.floor(Math.random() * 4)],
                                    width: '12px',
                                    height: '12px',
                                    borderRadius: Math.random() > 0.5 ? '50%' : '2px',
                                    animationDelay: `${Math.random() * 5}s`,
                                    animationDuration: `${3 + Math.random() * 3}s`
                                }}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Audio Element */}
            <audio
                ref={audioRef}
                src="https://assets.mixkit.co/active_storage/sfx/2013/2013-preview.mp3" // Coin/Success sound
            />

            <style jsx global>{`
        @keyframes confetti-fall {
          0% { transform: translateY(0) rotate(0); opacity: 1; }
          100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
        }
        .animate-confetti-fall {
          animation: confetti-fall linear forwards;
        }
      `}</style>
        </div>
    );
}

// =============================================
// SUB-VIEWS
// =============================================

function GoalView({ goal, metrics }: { goal: any, metrics: any }) {
    const hasGoal = goal?.revenue_goal && goal.revenue_goal > 0;
    const progress = goal?.revenue_progress || 0;

    return (
        <div className="space-y-12">
            <div className="text-center">
                <div className="inline-flex items-center gap-3 px-6 py-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full mb-6">
                    <Target className="w-6 h-6 text-indigo-500" />
                    <span className="text-lg font-black text-indigo-400 uppercase tracking-widest">Meta de Receita</span>
                </div>
                <h1 className="text-[12rem] font-black tracking-tighter leading-none mb-4 italic flex justify-center items-start">
                    <span className="text-white drop-shadow-[0_0_30px_rgba(255,255,255,0.2)]">
                        {progress.toFixed(0)}
                    </span>
                    <span className="text-indigo-500 text-6xl mt-8">%</span>
                </h1>
                <div className="w-full max-w-4xl mx-auto h-8 bg-white/5 rounded-full overflow-hidden border border-white/10 p-1">
                    <div
                        className="h-full bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-500 rounded-full transition-all duration-1000 shadow-[0_0_20px_rgba(99,102,241,0.5)]"
                        style={{ width: `${Math.min(progress, 100)}%` }}
                    />
                </div>
            </div>

            <div className="grid grid-cols-3 gap-8">
                <div className="bg-white/5 border border-white/10 rounded-3xl p-8 backdrop-blur-md">
                    <p className="text-slate-400 font-bold uppercase tracking-widest text-sm mb-2">Realizado</p>
                    <p className="text-5xl font-black text-white">{formatCurrency(goal?.revenue_actual || 0)}</p>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-3xl p-8 backdrop-blur-md">
                    <p className="text-slate-400 font-bold uppercase tracking-widest text-sm mb-2">Objetivo</p>
                    <p className="text-5xl font-black text-white">{formatCurrency(goal?.revenue_goal || 0)}</p>
                </div>
                <div className="bg-indigo-600 border border-white/10 rounded-3xl p-8 shadow-[0_0_30px_rgba(99,102,241,0.3)]">
                    <p className="text-white/60 font-bold uppercase tracking-widest text-sm mb-2">Dias Restantes</p>
                    <p className="text-5xl font-black text-white">{goal?.days_remaining || 0} dias</p>
                </div>
            </div>
        </div>
    );
}

function RankingView({ metrics }: { metrics: any }) {
    const ranking = metrics?.seller_ranking || [];

    return (
        <div className="space-y-8 w-full">
            <div className="text-center mb-12">
                <div className="inline-flex items-center gap-3 px-6 py-2 bg-amber-500/10 border border-amber-500/20 rounded-full mb-6">
                    <Trophy className="w-6 h-6 text-amber-500" />
                    <span className="text-lg font-black text-amber-400 uppercase tracking-widest">Ranking de Top Vendedores</span>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 max-w-4xl mx-auto">
                {ranking.map((seller: any, index: number) => (
                    <div
                        key={seller.seller_id}
                        className={`flex items-center gap-6 p-6 rounded-3xl border transition-all ${index === 0
                                ? 'bg-gradient-to-r from-amber-500/20 to-orange-500/20 border-amber-500/30 scale-105 shadow-[0_0_30px_rgba(245,158,11,0.15)]'
                                : 'bg-white/5 border-white/10'
                            }`}
                    >
                        <div className={`w-16 h-16 rounded-2xl flex items-center justify-center text-3xl font-black ${index === 0 ? 'bg-amber-500 text-slate-900' :
                                index === 1 ? 'bg-slate-300 text-slate-900' :
                                    index === 2 ? 'bg-orange-600 text-white' :
                                        'bg-white/10 text-white'
                            }`}>
                            {index + 1}
                        </div>

                        <div className="flex-1">
                            <h3 className="text-3xl font-black text-white truncate">{seller.seller_name}</h3>
                            <p className="text-slate-400 text-sm font-bold uppercase tracking-widest">
                                {seller.conversion_rate.toFixed(0)}% de Conversão | {seller.leads_assigned} Leads
                            </p>
                        </div>

                        <div className="text-right">
                            <p className={`text-5xl font-black ${index === 0 ? 'text-amber-500' : 'text-white'}`}>
                                {seller.deals_count}
                            </p>
                            <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Vendas Fechadas</p>
                        </div>
                    </div>
                ))}

                {ranking.length === 0 && (
                    <div className="text-center py-20 bg-white/5 rounded-3xl border border-dashed border-white/10">
                        <Users className="w-20 h-20 text-white/10 mx-auto mb-4" />
                        <p className="text-slate-500 font-bold uppercase tracking-[0.3em]">Aguardando resultados...</p>
                    </div>
                )}
            </div>
        </div>
    );
}

function LatestDealsView({ metrics }: { metrics: any }) {
    // Nota: metrics.latest_deals ou algo similar se existir, senão usamos deals do mês
    // Vamos simular ou carregar dados se a API permitir. Por enquanto usaremos métricas gerais
    return (
        <div className="space-y-12">
            <div className="text-center">
                <div className="inline-flex items-center gap-3 px-6 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full mb-6">
                    <DollarSign className="w-6 h-6 text-emerald-500" />
                    <span className="text-lg font-black text-emerald-400 uppercase tracking-widest">Fechamentos do Mês</span>
                </div>
                <h1 className="text-[12rem] font-black tracking-tighter leading-none mb-4 italic flex justify-center items-start">
                    <span className="text-emerald-500 mb-2 mr-4 text-6xl mt-8">#</span>
                    <span className="text-white drop-shadow-[0_0_30px_rgba(255,255,255,0.2)]">
                        {metrics?.total_deals || 0}
                    </span>
                </h1>
            </div>

            <div className="grid grid-cols-2 gap-8 max-w-5xl mx-auto">
                <div className="bg-white/5 border border-white/10 rounded-3xl p-10 backdrop-blur-md flex flex-col items-center">
                    <div className="w-16 h-16 bg-emerald-500/20 text-emerald-500 rounded-2xl flex items-center justify-center mb-4">
                        <Users className="w-8 h-8" />
                    </div>
                    <p className="text-slate-400 font-bold uppercase tracking-widest text-sm mb-1">Taxa de Conversão</p>
                    <p className="text-6xl font-black text-emerald-500">{metrics?.conversion_rate?.toFixed(1)}%</p>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-3xl p-10 backdrop-blur-md flex flex-col items-center">
                    <div className="w-16 h-16 bg-indigo-500/20 text-indigo-500 rounded-2xl flex items-center justify-center mb-4">
                        <DollarSign className="w-8 h-8" />
                    </div>
                    <p className="text-slate-400 font-bold uppercase tracking-widest text-sm mb-1">Ticket Médio</p>
                    <p className="text-6xl font-black text-indigo-500">{formatCurrency(metrics?.average_ticket || 0)}</p>
                </div>
            </div>
        </div>
    );
}
