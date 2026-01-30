'use client';

import { useEffect, useState } from 'react';
import { Lightbulb, X, Zap, ChevronUp, ChevronDown, Sparkles } from 'lucide-react';
import { getToken } from '@/lib/auth';
import { cn } from '@/lib/utils';

interface AIInsight {
    sentiment: 'positive' | 'neutral' | 'negative';
    key_topic: string;
    tip: string;
    action: string;
}

export function FloatingIntelligenceCard({ leadId }: { leadId: number }) {
    const [insight, setInsight] = useState<AIInsight | null>(null);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(false);
    const [dismissed, setDismissed] = useState(false);

    useEffect(() => {
        fetchInsight();
        setDismissed(false);
        setExpanded(false);
    }, [leadId]);

    const fetchInsight = async () => {
        try {
            setLoading(true);
            const token = getToken();
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/leads/${leadId}/ai-insights`, {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            });
            if (res.ok) {
                const data = await res.json();
                setInsight(data);
                // Expand potentially for hot leads or first load
                if (data.sentiment === 'positive') setExpanded(true);
            }
        } catch (error) {
            console.error("Failed to fetch AI insights", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading || dismissed || !insight) return null;

    return (
        <div
            className={cn(
                "absolute bottom-4 right-4 z-50 transition-all duration-500 ease-in-out",
                expanded ? "w-80" : "w-12 h-12"
            )}
        >
            {!expanded ? (
                <button
                    onClick={() => setExpanded(true)}
                    className="w-12 h-12 bg-yellow-400 rounded-full shadow-lg flex items-center justify-center hover:scale-110 transition-transform animate-bounce-slow"
                    title="Ver Insight da IA"
                >
                    <Sparkles className="w-6 h-6 text-yellow-900" />
                    <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full border-2 border-white animate-pulse" />
                </button>
            ) : (
                <div className="bg-white border-2 border-yellow-300 rounded-2xl shadow-xl overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-300">
                    {/* Header */}
                    <div className="bg-yellow-400 p-2 px-4 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Lightbulb className="w-4 h-4 text-yellow-900" />
                            <span className="text-[10px] font-black text-yellow-900 uppercase tracking-widest">
                                AI Advisor
                            </span>
                        </div>
                        <div className="flex items-center gap-1">
                            <button
                                onClick={() => setExpanded(false)}
                                className="p-1 hover:bg-black/10 rounded-full transition-colors"
                            >
                                <ChevronDown className="w-4 h-4 text-yellow-900" />
                            </button>
                            <button
                                onClick={() => setDismissed(true)}
                                className="p-1 hover:bg-black/10 rounded-full transition-colors"
                            >
                                <X className="w-4 h-4 text-yellow-900" />
                            </button>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="p-4 space-y-3">
                        <div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase">Contexto: {insight.key_topic}</span>
                            <p className="text-sm font-semibold text-slate-800 leading-tight mt-1 animate-in slide-in-from-left-2 duration-500">
                                "{insight.tip}"
                            </p>
                        </div>

                        <div className="bg-yellow-50 p-2.5 rounded-xl border border-yellow-200 flex items-start gap-2">
                            <Zap className="w-4 h-4 text-orange-500 shrink-0 mt-0.5" />
                            <div>
                                <span className="text-[9px] font-black text-orange-600 uppercase">Ação sugerida:</span>
                                <p className="text-xs font-bold text-slate-700 leading-tight">
                                    {insight.action}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
