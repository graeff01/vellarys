'use client';

/**
 * SALES WIDGETS
 * ==============
 *
 * Widgets de vendas e metas para o dashboard customizável.
 */

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { getSalesGoal, getSalesMetrics, setSalesGoal, SalesGoal, SalesMetrics } from '@/lib/api';
import {
  Target,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  DollarSign,
  Trophy,
  Calendar,
  Percent,
  AlertTriangle,
  Edit3,
  Save,
  X,
} from 'lucide-react';

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

function formatNumber(num: number): string {
  return new Intl.NumberFormat('pt-BR').format(num);
}

// =============================================
// HOOK COMPARTILHADO
// =============================================

export function useSalesData() {
  const [goal, setGoal] = useState<SalesGoal | null>(null);
  const [metrics, setMetrics] = useState<SalesMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [goalData, metricsData] = await Promise.all([
        getSalesGoal(),
        getSalesMetrics(),
      ]);
      setGoal(goalData);
      setMetrics(metricsData);
      setError(null);
    } catch (err) {
      console.error('Erro carregando dados de vendas:', err);
      setError('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return { goal, metrics, loading, error, reload: loadData };
}

// =============================================
// WIDGET: META MENSAL
// =============================================

interface SalesGoalWidgetProps {
  goal: SalesGoal | null;
  onUpdate?: () => void;
}

export function SalesGoalWidget({ goal, onUpdate }: SalesGoalWidgetProps) {
  const [editing, setEditing] = useState(false);
  const [newGoal, setNewGoal] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!newGoal) return;

    try {
      setSaving(true);
      const value = parseFloat(newGoal.replace(/[^\d,]/g, '').replace(',', '.'));
      await setSalesGoal({ revenue_goal: Math.round(value * 100) });
      setEditing(false);
      setNewGoal('');
      onUpdate?.();
    } catch (err) {
      console.error('Erro salvando meta:', err);
    } finally {
      setSaving(false);
    }
  };

  const hasGoal = goal?.revenue_goal && goal.revenue_goal > 0;
  const progress = goal?.revenue_progress || 0;

  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-indigo-600" />
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Meta Mensal</h3>
        </div>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="p-1 hover:bg-slate-100 rounded transition-colors"
            title="Editar meta"
          >
            <Edit3 className="w-3.5 h-3.5 text-slate-400" />
          </button>
        )}
      </div>

      <div className="p-4">
        {editing ? (
          <div className="space-y-3">
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase">Nova Meta (R$)</label>
              <input
                type="text"
                value={newGoal}
                onChange={(e) => setNewGoal(e.target.value)}
                placeholder="Ex: 500000"
                className="w-full mt-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                autoFocus
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleSave}
                disabled={saving || !newGoal}
                className="flex-1 px-3 py-2 bg-indigo-600 text-white text-xs font-bold rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-1"
              >
                <Save className="w-3.5 h-3.5" />
                Salvar
              </button>
              <button
                onClick={() => { setEditing(false); setNewGoal(''); }}
                className="px-3 py-2 border border-slate-200 text-slate-600 text-xs font-bold rounded-lg hover:bg-slate-50"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ) : hasGoal ? (
          <div className="space-y-3">
            <div className="text-center">
              <p className="text-3xl font-extrabold text-slate-900">
                {formatCurrency(goal.revenue_goal!)}
              </p>
              <p className="text-xs text-slate-500 font-medium">Meta de Receita</p>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-500">Progresso</span>
                <span className={progress >= 100 ? 'text-emerald-600' : 'text-indigo-600'}>
                  {progress.toFixed(0)}%
                </span>
              </div>
              <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${progress >= 100 ? 'bg-emerald-500' : progress >= 80 ? 'bg-indigo-500' : 'bg-indigo-400'
                    }`}
                  style={{ width: `${Math.min(progress, 100)}%` }}
                />
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100">
              <p className="text-sm font-bold text-slate-700">
                {formatCurrency(goal.revenue_actual)} <span className="text-slate-400 font-normal">realizado</span>
              </p>
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            <Target className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">Nenhuma meta definida</p>
            <button
              onClick={() => setEditing(true)}
              className="mt-2 text-xs font-bold text-indigo-600 hover:text-indigo-700"
            >
              Definir Meta
            </button>
          </div>
        )}
      </div>
    </Card>
  );
}

// =============================================
// WIDGET: PROGRESSO DE VENDAS (Quanto Falta)
// =============================================

interface SalesProgressWidgetProps {
  goal: SalesGoal | null;
}

export function SalesProgressWidget({ goal }: SalesProgressWidgetProps) {
  const hasGoal = goal?.revenue_goal && goal.revenue_goal > 0;
  const remaining = hasGoal ? Math.max(0, goal.revenue_goal! - goal.revenue_actual) : 0;
  const onTrack = goal ? goal.revenue_progress >= (goal.days_passed / goal.total_days) * 100 * 0.8 : true;

  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50">
        <div className="flex items-center gap-2">
          {onTrack ? (
            <TrendingUp className="w-4 h-4 text-emerald-600" />
          ) : (
            <TrendingDown className="w-4 h-4 text-rose-600" />
          )}
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Quanto Falta</h3>
        </div>
      </div>

      <div className="p-4">
        {hasGoal ? (
          <div className="space-y-3">
            <div className="text-center">
              <p className={`text-3xl font-extrabold ${remaining === 0 ? 'text-emerald-600' : 'text-slate-900'}`}>
                {remaining === 0 ? 'Meta Batida!' : formatCurrency(remaining)}
              </p>
              <p className="text-xs text-slate-500 font-medium">
                {remaining === 0 ? 'Parabéns!' : 'para bater a meta'}
              </p>
            </div>

            {!onTrack && remaining > 0 && (
              <div className="flex items-center gap-2 p-2 bg-amber-50 rounded-lg border border-amber-100">
                <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                <p className="text-xs text-amber-700 font-medium">Velocidade abaixo do esperado</p>
              </div>
            )}

            <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-100">
              <div className="flex-1 min-w-0">
                <p className="text-[10px] text-slate-400 font-bold uppercase">Realizado</p>
                <p className="text-xs font-bold text-slate-700 truncate">{formatCurrency(goal.revenue_actual)}</p>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] text-slate-400 font-bold uppercase">Meta</p>
                <p className="text-xs font-bold text-slate-700 truncate">{formatCurrency(goal.revenue_goal!)}</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            <TrendingUp className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">Defina uma meta primeiro</p>
          </div>
        )}
      </div>
    </Card>
  );
}

// =============================================
// WIDGET: VENDAS FECHADAS
// =============================================

interface DealsClosedWidgetProps {
  metrics: SalesMetrics | null;
}

export function DealsClosedWidget({ metrics }: DealsClosedWidgetProps) {
  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50">
        <div className="flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-emerald-600" />
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Vendas Fechadas</h3>
        </div>
      </div>

      <div className="p-4">
        <div className="text-center mb-3">
          <p className="text-4xl font-extrabold text-emerald-600">
            {metrics?.total_deals || 0}
          </p>
          <p className="text-xs text-slate-500 font-medium">este mês</p>
        </div>

        <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-100">
          <div className="text-center flex-1 min-w-[60px]">
            <p className="text-lg font-bold text-slate-700">{metrics?.deals_today || 0}</p>
            <p className="text-[10px] text-slate-400 font-bold uppercase">Hoje</p>
          </div>
          <div className="text-center flex-1 min-w-[60px]">
            <p className="text-lg font-bold text-slate-700">{metrics?.deals_this_week || 0}</p>
            <p className="text-[10px] text-slate-400 font-bold uppercase">Semana</p>
          </div>
        </div>
      </div>
    </Card>
  );
}

// =============================================
// WIDGET: TICKET MÉDIO
// =============================================

interface AverageTicketWidgetProps {
  metrics: SalesMetrics | null;
}

export function AverageTicketWidget({ metrics }: AverageTicketWidgetProps) {
  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50">
        <div className="flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-indigo-600" />
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Ticket Médio</h3>
        </div>
      </div>

      <div className="p-4">
        <div className="text-center">
          <p className="text-3xl font-extrabold text-indigo-600">
            {metrics?.average_ticket ? formatCurrency(metrics.average_ticket) : 'R$ 0'}
          </p>
          <p className="text-xs text-slate-500 font-medium">por venda</p>
        </div>

        {metrics && metrics.total_revenue > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-100 text-center">
            <p className="text-sm font-bold text-slate-700">
              {formatCurrency(metrics.total_revenue)}
            </p>
            <p className="text-[10px] text-slate-400 font-bold uppercase">Receita Total</p>
          </div>
        )}
      </div>
    </Card>
  );
}

// =============================================
// WIDGET: PROJEÇÃO DO MÊS
// =============================================

interface MonthProjectionWidgetProps {
  metrics: SalesMetrics | null;
  goal: SalesGoal | null;
}

export function MonthProjectionWidget({ metrics, goal }: MonthProjectionWidgetProps) {
  const hasGoal = goal?.revenue_goal && goal.revenue_goal > 0;
  const projectedRevenue = metrics?.projected_revenue || 0;
  const willReachGoal = hasGoal && projectedRevenue >= goal.revenue_goal!;

  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-violet-600" />
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Projeção do Mês</h3>
        </div>
      </div>

      <div className="p-4">
        <div className="text-center mb-3">
          <p className="text-3xl font-extrabold text-violet-600">
            {formatCurrency(projectedRevenue)}
          </p>
          <p className="text-xs text-slate-500 font-medium">estimativa de fechamento</p>
        </div>

        {hasGoal && (
          <div className={`flex items-center justify-center gap-2 p-2 rounded-lg ${willReachGoal ? 'bg-emerald-50 border border-emerald-100' : 'bg-amber-50 border border-amber-100'
            }`}>
            {willReachGoal ? (
              <>
                <CheckCircle className="w-4 h-4 text-emerald-600" />
                <p className="text-xs text-emerald-700 font-bold">Meta será batida!</p>
              </>
            ) : (
              <>
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <p className="text-xs text-amber-700 font-bold">
                  Faltam {formatCurrency(goal.revenue_goal! - projectedRevenue)}
                </p>
              </>
            )}
          </div>
        )}

        <div className="mt-3 pt-3 border-t border-slate-100 text-center">
          <p className="text-sm font-bold text-slate-700">{metrics?.projected_deals || 0} vendas</p>
          <p className="text-[10px] text-slate-400 font-bold uppercase">Projetadas</p>
        </div>
      </div>
    </Card>
  );
}

// =============================================
// WIDGET: RANKING DE VENDEDORES
// =============================================

interface SellerRankingWidgetProps {
  metrics: SalesMetrics | null;
}

export function SellerRankingWidget({ metrics }: SellerRankingWidgetProps) {
  const ranking = metrics?.seller_ranking || [];

  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50">
        <div className="flex items-center gap-2">
          <Trophy className="w-4 h-4 text-amber-500" />
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Ranking de Vendedores</h3>
        </div>
      </div>

      <div className="p-4">
        {ranking.length > 0 ? (
          <div className="space-y-3">
            {ranking.map((seller, index) => (
              <div
                key={seller.seller_id}
                className={`flex items-center gap-3 p-2 rounded-lg ${index === 0 ? 'bg-amber-50 border border-amber-100' : 'bg-slate-50'
                  }`}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${index === 0 ? 'bg-amber-500 text-white' :
                  index === 1 ? 'bg-slate-400 text-white' :
                    index === 2 ? 'bg-orange-400 text-white' :
                      'bg-slate-200 text-slate-600'
                  }`}>
                  {index + 1}
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-slate-800 truncate">{seller.seller_name}</p>
                  <p className="text-xs text-slate-500">
                    {seller.leads_assigned} leads | {seller.conversion_rate.toFixed(0)}% conversão
                  </p>
                </div>

                <div className="text-right">
                  <p className="text-lg font-extrabold text-slate-900">{seller.deals_count}</p>
                  <p className="text-[10px] text-slate-400 uppercase">vendas</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-4">
            <Trophy className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">Nenhuma venda registrada</p>
          </div>
        )}
      </div>
    </Card>
  );
}

// =============================================
// WIDGET: DIAS RESTANTES
// =============================================

interface DaysRemainingWidgetProps {
  goal: SalesGoal | null;
}

export function DaysRemainingWidget({ goal }: DaysRemainingWidgetProps) {
  const daysRemaining = goal?.days_remaining || 0;
  const totalDays = goal?.total_days || 30;
  const percentPassed = goal ? (goal.days_passed / totalDays) * 100 : 0;

  const urgencyColor = daysRemaining <= 5 ? 'text-rose-600' : daysRemaining <= 10 ? 'text-amber-600' : 'text-slate-900';
  const urgencyBg = daysRemaining <= 5 ? 'bg-rose-500' : daysRemaining <= 10 ? 'bg-amber-500' : 'bg-indigo-500';

  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-slate-600" />
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Dias Restantes</h3>
        </div>
      </div>

      <div className="p-4">
        <div className="text-center mb-3">
          <p className={`text-4xl font-extrabold ${urgencyColor}`}>
            {daysRemaining}
          </p>
          <p className="text-xs text-slate-500 font-medium">dias para fim do mês</p>
        </div>

        <div className="space-y-1">
          <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full ${urgencyBg} transition-all duration-500`}
              style={{ width: `${percentPassed}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-slate-400 font-bold">
            <span>Dia 1</span>
            <span>Dia {totalDays}</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

// =============================================
// WIDGET: TAXA DE CONVERSÃO
// =============================================

interface ConversionRateWidgetProps {
  metrics: SalesMetrics | null;
}

export function ConversionRateWidget({ metrics }: ConversionRateWidgetProps) {
  const rate = metrics?.conversion_rate || 0;
  const isGood = rate >= 10;

  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50">
        <div className="flex items-center gap-2">
          <Percent className="w-4 h-4 text-cyan-600" />
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Taxa de Conversão</h3>
        </div>
      </div>

      <div className="p-4">
        <div className="text-center mb-3">
          <p className={`text-4xl font-extrabold ${isGood ? 'text-emerald-600' : 'text-cyan-600'}`}>
            {rate.toFixed(1)}%
          </p>
          <p className="text-xs text-slate-500 font-medium">leads → vendas</p>
        </div>

        <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${isGood ? 'bg-emerald-500' : 'bg-cyan-500'}`}
            style={{ width: `${Math.min(rate * 2, 100)}%` }}
          />
        </div>

        {metrics && (
          <div className="mt-3 pt-3 border-t border-slate-100 text-center">
            <p className="text-xs text-slate-500">
              {metrics.total_deals} vendas de {formatNumber(metrics.goal?.leads_actual || 0)} leads
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}

// =============================================
// WIDGET: REVENUE ATTRIBUTION (ROI MAP)
// =============================================

interface RevenueBySourceWidgetProps {
  metrics: SalesMetrics | null;
}

export function RevenueBySourceWidget({ metrics }: RevenueBySourceWidgetProps) {
  const data = metrics?.revenue_by_source || {};
  const sources = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const maxRevenue = Math.max(...Object.values(data), 1);

  const sourceLabels: Record<string, string> = {
    'paid': 'Ads (Pago)',
    'organic': 'Orgânico',
    'referral': 'Indicação',
    'social': 'Social Media',
    'google': 'Google Search',
    'facebook': 'Meta Ads',
    'instagram': 'Instagram',
  };

  const colors: Record<string, string> = {
    'paid': 'bg-indigo-500',
    'organic': 'bg-emerald-500',
    'referral': 'bg-amber-500',
    'social': 'bg-rose-500',
  };

  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <PieChart className="w-4 h-4 text-indigo-600" />
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Mapa de ROI (Canais)</h3>
        </div>
      </div>
      <div className="p-4 space-y-4">
        {sources.length > 0 ? (
          sources.map(([source, revenue]) => {
            const percent = (revenue / maxRevenue) * 100;
            return (
              <div key={source} className="space-y-1">
                <div className="flex justify-between text-[11px] font-bold">
                  <span className="text-slate-600">{sourceLabels[source] || source}</span>
                  <span className="text-slate-900">{formatCurrency(revenue)}</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${colors[source] || 'bg-slate-400'} transition-all duration-1000`}
                    style={{ width: `${percent}%` }}
                  />
                </div>
              </div>
            );
          })
        ) : (
          <div className="text-center py-8">
            <PieChart className="w-8 h-8 text-slate-200 mx-auto mb-2" />
            <p className="text-xs text-slate-400 font-bold uppercase">Sem dados de receita</p>
          </div>
        )}
      </div>
    </Card>
  );
}

// =============================================
// WIDGET: PROPENSITY RANKING (IA PREDITIVA)
// =============================================

import { Zap, PieChart, Activity as PulseIcon, ChevronRight } from 'lucide-react';
import { getLeads } from '@/lib/api';

export function PropensityRankingWidget() {
  const [leads, setLeads] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getLeads({ page: 1, sort_by: 'propensity_score' }) as any;
        setLeads(data.items.slice(0, 5));
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-500 fill-amber-500" />
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Top Oportunidades (IA)</h3>
        </div>
        <span className="px-2 py-0.5 bg-amber-100 text-[9px] font-black text-amber-700 rounded uppercase tracking-tighter">Preditivo</span>
      </div>
      <div className="p-2 space-y-1">
        {loading ? (
          <div className="p-4 space-y-2 animate-pulse">
            <div className="h-10 bg-slate-100 rounded-xl" />
            <div className="h-10 bg-slate-100 rounded-xl" />
          </div>
        ) : leads.map(lead => (
          <div key={lead.id} className="flex items-center gap-3 p-2 hover:bg-slate-50 rounded-xl transition-all group">
            <div className="w-10 h-10 rounded-xl bg-slate-100 flex flex-col items-center justify-center border border-slate-200">
              <span className="text-[10px] font-black leading-none text-slate-400 uppercase">Score</span>
              <span className="text-sm font-black text-indigo-600">{lead.propensity_score || 0}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-slate-800 truncate">{lead.name || 'Lead sem nome'}</p>
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-bold text-slate-400 uppercase">{lead.status}</span>
                <div className="w-1 h-1 bg-slate-300 rounded-full" />
                <span className="text-[9px] font-bold text-slate-400 uppercase">{lead.source}</span>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-indigo-500 transition-all" />
          </div>
        ))}
      </div>
    </Card>
  );
}

// =============================================
// WIDGET: SALES PULSE (LIVE FEED)
// =============================================

export function SalesPulseWidget({ metrics }: { metrics: SalesMetrics | null }) {
  const pulse = metrics?.pulse || [];

  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full flex flex-col">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <PulseIcon className="w-4 h-4 text-rose-500" />
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Pulse de Atividade</h3>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 bg-rose-500 rounded-full animate-ping" />
          <span className="text-[10px] font-bold text-rose-500 uppercase tracking-tighter">Live</span>
        </div>
      </div>
      <div className="flex-1 p-2 space-y-2 overflow-y-auto max-h-[300px] scrollbar-hide">
        {pulse.length > 0 ? (
          pulse.map((ev, i) => (
            <div key={ev.id || i} className="flex gap-3 p-2 border-b border-slate-50 last:border-0 items-start">
              <div className={`mt-1 w-2 h-2 rounded-full shrink-0 ${ev.type === 'venda' ? 'bg-emerald-500' :
                ev.type === 'mudanca_status' ? 'bg-indigo-500' :
                  'bg-slate-300'
                }`} />
              <div className="min-w-0">
                <p className="text-xs font-bold text-slate-800 leading-tight">
                  <span className="text-indigo-600">{ev.lead_name}</span> {ev.description}
                </p>
                <p className="text-[9px] font-bold text-slate-400 uppercase mt-1">
                  {new Date(ev.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </div>
          ))
        ) : (
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <PulseIcon className="w-8 h-8 text-slate-100 mb-2" />
            <p className="text-[10px] font-bold text-slate-300 uppercase">Aguardando atividades...</p>
          </div>
        )}
      </div>
    </Card>
  );
}
