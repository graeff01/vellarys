'use client';

import { Card } from '@/components/ui/card';
import {
  Flame,
  UserCheck,
  TrendingUp,
  MessageSquare
} from 'lucide-react';

interface MetricsCardsProps {
  metrics: {
    total_leads: number;
    leads_today: number;
    leads_this_week: number;
    leads_this_month: number;
    conversion_rate: number;
    avg_qualification_time_hours: number;
    by_qualification: Record<string, number>;
    by_status: Record<string, number>;
  };
}

export function MetricsCards({ metrics }: MetricsCardsProps) {
  // Calcula métricas derivadas com fallback para garantir robustez
  const leadsHot = metrics.by_qualification?.hot || metrics.by_qualification?.quente || 0;
  const leadsCold = metrics.by_qualification?.cold || metrics.by_qualification?.frio || 0;

  const leadsTransferred = metrics.by_status?.handed_off || metrics.by_status?.transferido || 0;
  const leadsQualified = metrics.by_status?.qualified || metrics.by_status?.qualificado || 0;

  // Taxas de performance
  const hotRate = metrics.total_leads > 0
    ? Math.round((leadsHot / metrics.total_leads) * 100)
    : 0;

  const filterRate = metrics.total_leads > 0
    ? Math.round((leadsCold / metrics.total_leads) * 100)
    : 0;

  return (
    <div className="flex flex-wrap gap-4 h-full">
      {/* 1. Atendimento Total */}
      <Card className="bg-white border-slate-200 shadow-sm overflow-hidden rounded-2xl group hover:border-blue-300 transition-all duration-300 flex-1 min-w-[200px]">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center border border-blue-100 group-hover:scale-110 transition-transform">
              <MessageSquare className="w-6 h-6 text-blue-600" />
            </div>
            <div className="flex flex-col items-end">
              <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-lg uppercase tracking-wider">
                Hoje: +{metrics.leads_today}
              </span>
            </div>
          </div>
          <div>
            <p className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-1">Atendidos pela IA</p>
            <div className="flex items-baseline gap-2">
              <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight">{metrics.total_leads}</h2>
              <span className="text-xs font-bold text-slate-400">Conversas</span>
            </div>
          </div>
        </div>
      </Card>

      {/* 2. Funil de Qualificação (Ouro) */}
      <Card className="bg-white border-slate-200 shadow-sm overflow-hidden rounded-2xl group hover:border-rose-300 transition-all duration-300 flex-1 min-w-[200px]">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-rose-50 rounded-xl flex items-center justify-center border border-rose-100 group-hover:scale-110 transition-transform">
              <Flame className="w-6 h-6 text-rose-600" />
            </div>
            <div className="flex flex-col items-end">
              <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-lg uppercase tracking-wider">
                {hotRate}% Eficiência
              </span>
            </div>
          </div>
          <div>
            <p className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-1">Prontos p/ Comprar</p>
            <div className="flex items-baseline gap-2">
              <h2 className="text-4xl font-extrabold text-rose-600 tracking-tight">{leadsHot}</h2>
              <span className="text-xs font-bold text-slate-400">Leads Quentes</span>
            </div>
          </div>
        </div>
      </Card>

      {/* 3. Entrega Comercial */}
      <Card className="bg-white border-slate-200 shadow-sm overflow-hidden rounded-2xl group hover:border-emerald-300 transition-all duration-300 flex-1 min-w-[200px]">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center border border-emerald-100 group-hover:scale-110 transition-transform">
              <UserCheck className="w-6 h-6 text-emerald-600" />
            </div>
            <div className="flex flex-col items-end">
              <span className="text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded-lg uppercase tracking-wider">
                Transf. Direta
              </span>
            </div>
          </div>
          <div>
            <p className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-1">Enviados ao Time</p>
            <div className="flex items-baseline gap-2">
              <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight">{leadsTransferred + leadsQualified}</h2>
              <span className="text-xs font-bold text-slate-400">Oportunidades</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Resumo de Conversão (Banner Sutil) */}
      <div className="w-full basis-full bg-slate-900 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-xl shadow-slate-200/50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-slate-800 rounded-lg flex items-center justify-center border border-slate-700 shrink-0">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-white text-xs font-bold uppercase tracking-widest whitespace-nowrap">Performance Global</p>
        </div>

        <div className="flex flex-wrap items-center gap-4 sm:gap-8 pr-4">
          <div className="flex flex-col min-w-[80px]">
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">Conversão</span>
            <span className="text-lg font-extrabold text-white leading-none">{metrics.conversion_rate}%</span>
          </div>
          <div className="flex flex-col min-w-[80px] border-l border-slate-700 pl-4 sm:pl-8">
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">Filtro Curiosos</span>
            <span className="text-lg font-extrabold text-blue-400 leading-none">{filterRate}%</span>
          </div>
          <div className="flex flex-col min-w-[80px] border-l border-slate-700 pl-4 sm:pl-8">
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">Ciclo Qualif.</span>
            <span className="text-lg font-extrabold text-amber-400 leading-none">
              {metrics.avg_qualification_time_hours > 0 ? `${metrics.avg_qualification_time_hours}h` : '< 1h'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}