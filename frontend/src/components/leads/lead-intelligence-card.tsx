'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Lightbulb, Zap, TrendingUp, AlertCircle, RefreshCw } from 'lucide-react';
import { getToken } from '@/lib/auth'; // Ensure this exists or use appropriate auth method
// import { Skeleton } from '@/components/ui/skeleton';

interface AIInsight {
    sentiment: 'positive' | 'neutral' | 'negative';
    key_topic: string;
    tip: string;
    action: string;
}

export function LeadIntelligenceCard({ leadId }: { leadId: number }) {
    const [insight, setInsight] = useState<AIInsight | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchInsight();
    }, [leadId]);

    const fetchInsight = async () => {
        try {
            setLoading(true);
            const token = getToken();
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/leads/${leadId}/ai-insights`, {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            });
            if (res.ok) {
                const data = await res.json();
                setInsight(data);
            }
        } catch (error) {
            console.error("Failed to fetch AI insights", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) { // Correct usage of Skeleton
        return (
            <div className="mb-4 space-y-2">
                <div className="h-24 w-full bg-yellow-50/50 rounded-xl animate-pulse border border-yellow-100" />
            </div>
        );
    }

    if (!insight) return null;

    return (
        <div className="mb-4 relative group">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-yellow-400 to-orange-400 rounded-xl blur opacity-30 group-hover:opacity-50 transition duration-1000"></div>
            <Card className="relative border-l-4 border-l-yellow-500 bg-yellow-50/80 backdrop-blur-sm border-yellow-200/50 shadow-sm overflow-hidden">
                <div className="p-4 flex items-start gap-4">
                    {/* Icon Box */}
                    <div className="p-2 bg-yellow-100 rounded-lg shrink-0 shadow-inner">
                        <Lightbulb className="w-5 h-5 text-yellow-600 animate-pulse" />
                    </div>

                    <div className="flex-1 space-y-2">
                        {/* Header: Topic & Sentiment */}
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] font-black text-yellow-600 uppercase tracking-widest bg-yellow-200/50 px-2 py-0.5 rounded text-xs">
                                    Intelligence Injection
                                </span>
                                <span className="text-xs font-bold text-slate-700 flex items-center gap-1">
                                    Tema: <span className="text-slate-900">{insight.key_topic}</span>
                                </span>
                            </div>

                            {/* Sentiment Badge */}
                            <div className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide flex items-center gap-1
                                ${insight.sentiment === 'positive' ? 'bg-green-100 text-green-700' :
                                    insight.sentiment === 'negative' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'}`}>
                                <TrendingUp className="w-3 h-3" />
                                {insight.sentiment === 'positive' ? 'Positivo' : insight.sentiment === 'negative' ? 'Crítico' : 'Neutro'}
                            </div>
                        </div>

                        {/* Main Tip */}
                        <p className="text-sm font-medium text-slate-800 leading-relaxed italic">
                            "{insight.tip}"
                        </p>

                        {/* Action Box */}
                        <div className="flex items-center gap-2 bg-white/60 p-2 rounded-lg border border-yellow-200/60 mt-2">
                            <Zap className="w-4 h-4 text-orange-500 fill-orange-500" />
                            <p className="text-xs font-bold text-slate-700">
                                <span className="text-orange-600 uppercase tracking-wider text-[9px] mr-1">Ação Sugerida:</span>
                                {insight.action}
                            </p>

                            <button
                                onClick={fetchInsight}
                                className="ml-auto p-1 hover:bg-black/5 rounded-full transition-colors"
                                title="Atualizar Análise"
                            >
                                <RefreshCw className="w-3 h-3 text-slate-400" />
                            </button>
                        </div>
                    </div>
                </div>
            </Card>
        </div>
    );
}
