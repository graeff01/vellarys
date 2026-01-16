'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { MetricsCards } from '@/components/dashboard/metrics-cards';
import { QualificationDonut } from '@/components/dashboard/qualification-donut';
import { ROICard } from '@/components/dashboard/roi-card';
import { LeadsTable } from '@/components/dashboard/leads-table';
import { PlanUsageCard } from '@/components/dashboard/plan-usage-card';
import { CEODashboard } from '@/components/ceo/ceo-dashboard';
import { getMetrics, getLeads } from '@/lib/api';
import { getSellers } from '@/lib/sellers';
import { getUser } from '@/lib/auth';
import {
  Flame,
  Clock,
  DollarSign,
  Zap,
  ArrowRight,
  TrendingUp,
  AlertCircle,
  RefreshCw,
  Sparkles,
  ChevronRight,
  Filter,
  BarChart3,
  MessageSquare,
  Users
} from 'lucide-react';

interface TimeSaved {
  hours_saved: number;
  cost_saved_brl: number;
  leads_handled: number;
}

interface Metrics {
  total_leads: number;
  leads_today: number;
  leads_this_week: number;
  leads_this_month: number;
  conversion_rate: number;
  avg_qualification_time_hours: number;
  avg_response_time_minutes: number;
  engagement_rate: number;
  by_qualification: Record<string, number>;
  by_status: Record<string, number>;
  time_saved: TimeSaved;
  after_hours_leads: number;
  growth_percentage: number;
  hot_leads_waiting: number;
  funnel?: {
    total: number;
    engaged: number;
    qualified: number;
    converted: number;
  };
  top_topics?: { topic: string; count: number }[];
}

interface Lead {
  id: number;
  name: string | null;
  phone: string | null;
  qualification: string;
  status: string;
  created_at: string;
  assigned_seller?: { id: number; name: string; whatsapp: string } | null;
}

interface Seller {
  id: number;
  name: string;
  whatsapp: string;
  available: boolean;
  active: boolean;
}

function ErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-6">
      <div className="p-5 bg-rose-50 rounded-2xl border border-rose-100 shadow-xl shadow-rose-100/20">
        <AlertCircle className="w-12 h-12 text-rose-600" />
      </div>
      <div className="text-center max-w-sm">
        <h3 className="text-xl font-extrabold text-slate-900 mb-2">
          Houve um contratempo
        </h3>
        <p className="text-slate-500 font-medium mb-6 leading-relaxed">{error}</p>
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-8 py-3.5 bg-slate-900 text-white rounded-xl font-bold shadow-lg shadow-slate-200 hover:scale-[1.02] active:scale-[0.98] transition-all mx-auto"
        >
          <RefreshCw className="w-5 h-5" />
          Tentar Novamente
        </button>
      </div>
    </div>
  );
}

function GestorDashboard() {
  const router = useRouter();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [metricsData, leadsData, sellersData] = await Promise.all([
        getMetrics(),
        getLeads({ page: 1 }),
        getSellers(),
      ]);
      if (!metricsData) throw new Error('Métricas não disponíveis');
      setMetrics(metricsData as Metrics);
      setLeads((leadsData as { items: Lead[] }).items || []);
      setSellers((sellersData as { sellers: Seller[] }).sellers || []);
    } catch (err: unknown) {
      console.error('Erro dashboard:', err);
      const errorMessage = err instanceof Error ? err.message : 'Erro ao carregar dados';
      if (errorMessage.includes('401')) {
        setError('Sessão expirada. Redirecionando...');
        setTimeout(() => router.push('/login'), 2000);
      } else {
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <div className="w-12 h-12 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin"></div>
        <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px]">Sincronizando Dashboard...</p>
      </div>
    );
  }

  if (error) return <ErrorState error={error} onRetry={loadData} />;
  if (!metrics) return null;

  const leadsHot = metrics.by_qualification?.quente || metrics.by_qualification?.hot || 0;
  const leadsCold = metrics.by_qualification?.frio || metrics.by_qualification?.cold || 0;
  const timeSaved = metrics.time_saved || { hours_saved: 0, cost_saved_brl: 0, leads_handled: 0 };
  const hotLeadsWaiting = metrics.hot_leads_waiting || 0;
  const avgResponseTime = metrics.avg_response_time_minutes || 0;

  return (
    <div className="space-y-4 animate-in fade-in duration-700">
      {/* Header Premium */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Visão Geral</h1>
          <p className="text-slate-500 font-medium">Análise estratégica de desempenho do Velaris AI</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="bg-white border border-slate-200 rounded-xl px-4 py-2 shadow-sm flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">Sistema Operante</span>
          </div>
        </div>
      </div>

      {/* Métricas Principais Consolidadas */}
      <MetricsCards metrics={metrics} />

      {/* CTA Leads Quentes (Destaque Crítico) */}
      {hotLeadsWaiting > 0 && (
        <div className="relative group overflow-hidden rounded-3xl">
          <div className="absolute inset-0 bg-gradient-to-r from-rose-600 to-orange-500 animate-gradient-x"></div>
          <div className="relative p-6 flex flex-col md:flex-row items-center justify-between gap-6 backdrop-blur-sm bg-black/10">
            <div className="flex items-center gap-5">
              <div className="w-16 h-16 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center shadow-2xl">
                <Flame className="w-8 h-8 text-white animate-bounce" />
              </div>
              <div className="text-white">
                <h3 className="text-2xl font-extrabold tracking-tight">
                  {hotLeadsWaiting} Lead{hotLeadsWaiting !== 1 ? 's' : ''} Quente{hotLeadsWaiting !== 1 ? 's' : ''} Aguardando!
                </h3>
                <p className="text-white/80 font-medium">Momentum ideal para fechamento detectado pela IA.</p>
              </div>
            </div>
            <button
              onClick={() => router.push('/dashboard/leads?qualification=quente')}
              className="px-8 py-4 bg-white text-rose-600 rounded-2xl font-extrabold shadow-xl hover:scale-105 active:scale-95 transition-all flex items-center gap-3 group/btn"
            >
              Atender Agora
              <ArrowRight className="w-5 h-5 group-hover/btn:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      )}

      {/* Seção Impacto Velaris (IA Value) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8 space-y-4">
          <Card className="bg-white border-slate-200 shadow-sm overflow-hidden rounded-3xl">
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center border border-blue-100">
                  <Sparkles className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-extrabold text-sm text-slate-900 uppercase tracking-widest">Impacto Velaris IA</h3>
                  <p className="text-[10px] text-slate-400 font-bold uppercase">ROI e Eficiência Operacional</p>
                </div>
              </div>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Tempo */}
              <div className="relative p-5 rounded-2xl bg-slate-50 border border-slate-100 hover:border-blue-200 transition-all cursor-default">
                <div className="absolute top-4 right-4 text-emerald-500 flex items-center gap-1 font-bold text-[10px] uppercase">
                  <TrendingUp className="w-3.5 h-3.5" />
                  Ativo
                </div>
                <Clock className="w-5 h-5 text-slate-400 mb-3" />
                <p className="text-3xl font-extrabold text-slate-900 leading-none mb-1">{timeSaved.hours_saved.toFixed(1)}h</p>
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest leading-relaxed">Tempo Economizado</p>
              </div>

              {/* ROI Financeiro */}
              <div className="relative p-5 rounded-2xl bg-white border-2 border-indigo-100 shadow-md shadow-indigo-50 hover:scale-[1.02] transition-all cursor-default overflow-hidden group">
                <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:scale-110 transition-transform">
                  <DollarSign className="w-10 h-10 text-indigo-600" />
                </div>
                <DollarSign className="w-5 h-5 text-indigo-500 mb-3" />
                <p className="text-3xl font-extrabold text-indigo-600 leading-none mb-1">R$ {timeSaved.cost_saved_brl.toFixed(0)}</p>
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest leading-relaxed">Economia em Salários</p>
              </div>

              {/* Resposta */}
              <div className="relative p-5 rounded-2xl bg-slate-50 border border-slate-100 hover:border-amber-200 transition-all cursor-default">
                <Zap className="w-5 h-5 text-amber-500 mb-3" />
                <p className="text-3xl font-extrabold text-slate-900 leading-none mb-1">{avgResponseTime.toFixed(1)}m</p>
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest leading-relaxed">Tempo de Resposta</p>
              </div>
            </div>
          </Card>

          {/* NOVO: FUNIL DE CONVERSÃO */}
          <Card className="bg-white border-slate-200 shadow-sm overflow-hidden rounded-3xl">
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-indigo-50 rounded-xl flex items-center justify-center border border-indigo-100">
                  <Filter className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <h3 className="font-extrabold text-sm text-slate-900 uppercase tracking-widest">Funil de Atendimento</h3>
                  <p className="text-[10px] text-slate-400 font-bold uppercase">Conversão em tempo real</p>
                </div>
              </div>
            </div>
            <div className="p-5">
              <div className="flex flex-col gap-2.5">
                {[
                  { label: 'Leads Captados', value: metrics.funnel?.total || 0, icon: Users, color: 'bg-slate-200' },
                  { label: 'Engajados (2+ msgs)', value: metrics.funnel?.engaged || 0, icon: MessageSquare, color: 'bg-blue-400' },
                  { label: 'Qualificados (Quentes)', value: metrics.funnel?.qualified || 0, icon: Flame, color: 'bg-orange-500' },
                  { label: 'Oportunidades (Handoff)', value: metrics.funnel?.converted || 0, icon: Zap, color: 'bg-emerald-500' },
                ].map((item, idx, arr) => {
                  const percentage = arr[0].value > 0 ? (item.value / arr[0].value) * 100 : 0;
                  return (
                    <div key={item.label} className="relative">
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <item.icon className="w-3.5 h-3.5 text-slate-400" />
                          <span className="text-xs font-bold text-slate-600 tracking-tight">{item.label}</span>
                        </div>
                        <span className="text-sm font-black text-slate-800">{item.value}</span>
                      </div>
                      <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${item.color} transition-all duration-1000 ease-out`}
                          style={{ width: `${Math.max(percentage, 2)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-4 space-y-4">
          {/* NOVO: HEATMAP DE INTERESSES */}
          <Card className="bg-white border-slate-200 shadow-sm rounded-3xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50">
              <div className="flex items-center gap-3">
                <BarChart3 className="w-5 h-5 text-slate-600" />
                <h3 className="font-extrabold text-sm text-slate-900 uppercase tracking-widest">Interesses / Dúvidas</h3>
              </div>
            </div>
            <div className="p-5">
              <div className="flex flex-wrap gap-1.5">
                {metrics.top_topics && metrics.top_topics.length > 0 ? (
                  metrics.top_topics.map((topic, i) => (
                    <div
                      key={topic.topic}
                      className="px-4 py-2 rounded-xl border border-slate-100 font-bold text-sm transition-all hover:scale-105 cursor-default bg-slate-50 text-slate-600"
                      style={{
                        opacity: 1 - (i * 0.08),
                        fontSize: `${Math.max(14 - i, 10)}px`
                      }}
                    >
                      {topic.topic}
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 italic">Analisando primeiras interações...</p>
                )}
              </div>
              <div className="mt-4 pt-4 border-t border-slate-50">
                <p className="text-[10px] text-slate-400 font-bold uppercase mb-3">Qualificação</p>
                <QualificationDonut data={metrics.by_qualification} />
              </div>
            </div>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-4">
          <PlanUsageCard />
        </div>
        <div className="lg:col-span-8">
          <Card className="bg-white border-slate-200 shadow-sm rounded-3xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
              <div>
                <h3 className="font-extrabold text-sm text-slate-900 uppercase tracking-widest">Leads Recentes</h3>
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Últimas interações</p>
              </div>
              <button
                onClick={() => router.push('/dashboard/leads')}
                className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                Ver Todos
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            <div className="p-0">
              <LeadsTable
                leads={leads.slice(0, 5)}
                sellers={sellers}
              />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [userRole, setUserRole] = useState<string | undefined>(undefined);

  useEffect(() => {
    const user = getUser();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUserRole(user?.role || 'guest');
  }, []);

  if (userRole === undefined) return null;

  const isSuperAdmin = userRole === 'superadmin';
  return (
    <div className="p-4 md:p-6 max-w-screen-2xl mx-auto">
      {isSuperAdmin ? <CEODashboard /> : <GestorDashboard />}
    </div>
  );
}