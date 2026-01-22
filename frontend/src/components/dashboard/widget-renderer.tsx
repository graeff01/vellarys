'use client';

/**
 * WIDGET RENDERER
 * =================
 *
 * Renderiza widgets dinamicamente baseado no tipo.
 * Conecta o registry com os componentes reais.
 */

import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { MetricsCards } from './metrics-cards';
import { QualificationDonut } from './qualification-donut';
import { LeadsTable } from './leads-table';
import { PlanUsageCard } from './plan-usage-card';
import {
  SalesGoalWidget,
  SalesProgressWidget,
  DealsClosedWidget,
  AverageTicketWidget,
  MonthProjectionWidget,
  SellerRankingWidget,
  DaysRemainingWidget,
  ConversionRateWidget,
  useSalesData,
} from './sales-widgets';
import { getSizeClasses } from './widget-registry';
import { WidgetConfig, SalesGoal, SalesMetrics } from '@/lib/api';
import {
  Flame,
  ArrowRight,
  Clock,
  DollarSign,
  Zap,
  TrendingUp,
  Sparkles,
  Filter,
  MessageSquare,
  Users,
  BarChart3,
  ChevronRight,
} from 'lucide-react';

// Tipos
interface WidgetProps {
  config: WidgetConfig;
  metrics: any;
  leads: any[];
  sellers: any[];
  salesData: {
    goal: SalesGoal | null;
    metrics: SalesMetrics | null;
    reload: () => void;
  };
  /** Quando true, o layout é controlado pelo react-grid-layout */
  isGridMode?: boolean;
}

// =============================================
// COMPONENTES DE WIDGETS EXISTENTES (INLINE)
// =============================================

function HotLeadsCTAWidget({ metrics }: { metrics: any }) {
  const router = useRouter();
  const hotLeadsWaiting = metrics?.hot_leads_waiting || 0;

  if (hotLeadsWaiting <= 0) return null;

  return (
    <div className="relative group overflow-hidden rounded-2xl h-full">
      <div className="absolute inset-0 bg-gradient-to-r from-rose-600 to-orange-500 animate-gradient-x"></div>
      <div className="relative p-3 flex flex-wrap items-center justify-between gap-3 backdrop-blur-sm bg-black/10 h-full">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div className="w-10 h-10 bg-white/20 backdrop-blur-md rounded-xl flex items-center justify-center shadow-2xl shrink-0">
            <Flame className="w-5 h-5 text-white animate-bounce" />
          </div>
          <div className="text-white min-w-0">
            <h3 className="text-lg font-extrabold tracking-tight truncate">
              {hotLeadsWaiting} Lead{hotLeadsWaiting !== 1 ? 's' : ''} Quente{hotLeadsWaiting !== 1 ? 's' : ''} Aguardando!
            </h3>
            <p className="text-xs text-white/80 font-medium truncate">Momentum para fechamento detectado</p>
          </div>
        </div>
        <button
          onClick={() => router.push('/dashboard/leads?qualification=quente')}
          className="px-4 py-2 bg-white text-rose-600 rounded-xl font-extrabold shadow-xl hover:scale-105 active:scale-95 transition-all flex items-center gap-2 group/btn shrink-0 text-sm"
        >
          Atender
          <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
        </button>
      </div>
    </div>
  );
}

function ImpactVelarisWidget({ metrics }: { metrics: any }) {
  const timeSaved = metrics?.time_saved || { hours_saved: 0, cost_saved_brl: 0, leads_handled: 0 };
  const avgResponseTime = metrics?.avg_response_time_minutes || 0;

  return (
    <Card className="bg-white border-slate-200 shadow-sm overflow-hidden rounded-2xl h-full flex flex-col">
      <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-3 bg-slate-50/50 shrink-0">
        <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center border border-blue-100">
          <Sparkles className="w-4 h-4 text-blue-600" />
        </div>
        <div className="min-w-0">
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest truncate">Impacto Velaris IA</h3>
          <p className="text-[9px] text-slate-400 font-bold uppercase truncate">ROI e Eficiência</p>
        </div>
      </div>
      <div className="p-3 flex-1 flex flex-wrap gap-2 content-start overflow-hidden">
        <div className="relative p-3 rounded-xl bg-slate-50 border border-slate-100 hover:border-blue-200 transition-all cursor-default flex-1 min-w-[120px]">
          <div className="absolute top-2 right-2 text-emerald-500 flex items-center gap-1 font-bold text-[8px] uppercase">
            <TrendingUp className="w-2.5 h-2.5" />
            Ativo
          </div>
          <Clock className="w-4 h-4 text-slate-400 mb-1" />
          <p className="text-xl font-extrabold text-slate-900 leading-none mb-0.5">{timeSaved.hours_saved.toFixed(1)}h</p>
          <p className="text-[8px] font-bold text-slate-500 uppercase tracking-wider">Tempo Economizado</p>
        </div>

        <div className="relative p-3 rounded-xl bg-white border-2 border-indigo-100 shadow-sm hover:scale-[1.02] transition-all cursor-default overflow-hidden group flex-1 min-w-[120px]">
          <DollarSign className="w-4 h-4 text-indigo-500 mb-1" />
          <p className="text-xl font-extrabold text-indigo-600 leading-none mb-0.5">R$ {timeSaved.cost_saved_brl.toFixed(0)}</p>
          <p className="text-[8px] font-bold text-slate-500 uppercase tracking-wider">Economia</p>
        </div>

        <div className="relative p-3 rounded-xl bg-slate-50 border border-slate-100 hover:border-amber-200 transition-all cursor-default flex-1 min-w-[120px]">
          <Zap className="w-4 h-4 text-amber-500 mb-1" />
          <p className="text-xl font-extrabold text-slate-900 leading-none mb-0.5">{avgResponseTime.toFixed(1)}m</p>
          <p className="text-[8px] font-bold text-slate-500 uppercase tracking-wider">Resposta</p>
        </div>
      </div>
    </Card>
  );
}

function FunnelWidget({ metrics }: { metrics: any }) {
  const funnel = metrics?.funnel || { total: 0, engaged: 0, qualified: 0, converted: 0 };

  const items = [
    { label: 'Leads Captados', value: funnel.total, icon: Users, color: 'bg-slate-200' },
    { label: 'Engajados (2+ msgs)', value: funnel.engaged, icon: MessageSquare, color: 'bg-blue-400' },
    { label: 'Qualificados (Quentes)', value: funnel.qualified, icon: Flame, color: 'bg-orange-500' },
    { label: 'Oportunidades (Handoff)', value: funnel.converted, icon: Zap, color: 'bg-emerald-500' },
  ];

  return (
    <Card className="bg-white border-slate-200 shadow-sm overflow-hidden rounded-2xl h-full flex flex-col">
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50/50 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-indigo-50 rounded-lg flex items-center justify-center border border-indigo-100">
            <Filter className="w-4 h-4 text-indigo-600" />
          </div>
          <div>
            <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Funil de Atendimento</h3>
            <p className="text-[9px] text-slate-400 font-bold uppercase">Conversão em tempo real</p>
          </div>
        </div>
      </div>
      <div className="p-3 flex-1 overflow-hidden">
        <div className="flex flex-col gap-2 h-full justify-center">
          {items.map((item, idx, arr) => {
            const percentage = arr[0].value > 0 ? (item.value / arr[0].value) * 100 : 0;
            const Icon = item.icon;
            return (
              <div key={item.label} className="relative">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <Icon className="w-3 h-3 text-slate-400" />
                    <span className="text-xs font-bold text-slate-600">{item.label}</span>
                  </div>
                  <span className="text-sm font-black text-slate-800">{item.value}</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
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
  );
}

function TopicsHeatmapWidget({ metrics }: { metrics: any }) {
  const topics = metrics?.top_topics || [];

  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full flex flex-col">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50 shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-slate-600" />
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Interesses / Dúvidas</h3>
        </div>
      </div>
      <div className="p-3 flex-1 overflow-hidden">
        <div className="flex flex-wrap gap-1.5 content-start">
          {topics.length > 0 ? (
            topics.map((topic: any, i: number) => (
              <div
                key={topic.topic}
                className="px-3 py-1.5 rounded-lg border border-slate-100 font-bold transition-all hover:scale-105 cursor-default bg-slate-50 text-slate-600"
                style={{
                  opacity: 1 - (i * 0.08),
                  fontSize: `${Math.max(13 - i, 10)}px`
                }}
              >
                {topic.topic}
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-400 italic">Analisando primeiras interações...</p>
          )}
        </div>
      </div>
    </Card>
  );
}

function QualificationWidget({ metrics }: { metrics: any }) {
  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full flex flex-col">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50 shrink-0">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-slate-600" />
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Qualificação</h3>
        </div>
      </div>
      <div className="p-3 flex-1 overflow-hidden">
        <QualificationDonut data={metrics?.by_qualification || {}} />
      </div>
    </Card>
  );
}

function LeadsTableWidget({ leads, sellers }: { leads: any[]; sellers: any[] }) {
  const router = useRouter();

  return (
    <Card className="bg-white border-slate-200 shadow-sm rounded-2xl overflow-hidden h-full flex flex-col">
      <div className="px-5 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
        <div>
          <h3 className="font-extrabold text-xs text-slate-900 uppercase tracking-widest">Leads Recentes</h3>
          <p className="text-[9px] text-slate-400 font-bold uppercase">Últimas interações</p>
        </div>
        <button
          onClick={() => router.push('/dashboard/leads')}
          className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1"
        >
          Ver Todos
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
      <div className="p-0 overflow-hidden flex-1">
        <LeadsTable leads={leads.slice(0, 5)} sellers={sellers} />
      </div>
    </Card>
  );
}

// =============================================
// WIDGET RENDERER
// =============================================

export function WidgetRenderer({ config, metrics, leads, sellers, salesData, isGridMode = false }: WidgetProps) {
  const sizeClass = getSizeClasses(config.size as any);

  // Renderiza baseado no tipo
  const renderWidget = () => {
    switch (config.type) {
      // Alertas
      case 'hot_leads_cta':
        return <HotLeadsCTAWidget metrics={metrics} />;

      // Métricas Gerais
      case 'metrics_cards':
        return <MetricsCards metrics={metrics} />;

      case 'qualification_donut':
        return <QualificationWidget metrics={metrics} />;

      case 'funnel':
        return <FunnelWidget metrics={metrics} />;

      case 'topics_heatmap':
        return <TopicsHeatmapWidget metrics={metrics} />;

      case 'impact_velaris':
        return <ImpactVelarisWidget metrics={metrics} />;

      case 'leads_table':
        return <LeadsTableWidget leads={leads} sellers={sellers} />;

      // Sistema
      case 'plan_usage':
        return <PlanUsageCard />;

      // Vendas
      case 'sales_goal':
        return <SalesGoalWidget goal={salesData.goal} onUpdate={salesData.reload} />;

      case 'sales_progress':
        return <SalesProgressWidget goal={salesData.goal} />;

      case 'deals_closed':
        return <DealsClosedWidget metrics={salesData.metrics} />;

      case 'average_ticket':
        return <AverageTicketWidget metrics={salesData.metrics} />;

      case 'month_projection':
        return <MonthProjectionWidget metrics={salesData.metrics} goal={salesData.goal} />;

      case 'seller_ranking':
        return <SellerRankingWidget metrics={salesData.metrics} />;

      case 'days_remaining':
        return <DaysRemainingWidget goal={salesData.goal} />;

      case 'conversion_rate':
        return <ConversionRateWidget metrics={salesData.metrics} />;

      default:
        return (
          <Card className="bg-slate-50 border-slate-200 rounded-2xl p-4 h-full flex items-center justify-center">
            <p className="text-sm text-slate-400">Widget não encontrado: {config.type}</p>
          </Card>
        );
    }
  };

  // Widget especial hot_leads_cta - só renderiza se tiver leads quentes
  if (config.type === 'hot_leads_cta' && (!metrics?.hot_leads_waiting || metrics.hot_leads_waiting <= 0)) {
    return null;
  }

  // No modo grid, react-grid-layout controla o sizing
  // overflow-hidden garante que widgets se ajustem sem scrollbar
  if (isGridMode) {
    return (
      <div className="h-full w-full overflow-hidden">
        {renderWidget()}
      </div>
    );
  }

  // Modo tradicional com classes CSS
  return (
    <div className={sizeClass}>
      {renderWidget()}
    </div>
  );
}
