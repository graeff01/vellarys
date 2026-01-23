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
    <div className="flex flex-wrap gap-2 h-full content-start">
      {/* 1. Atendimento Total */}
      <Card className="bg-white border-slate-200 shadow-sm overflow-hidden rounded-2xl group hover:border-blue-300 transition-all duration-300 flex-1 min-w-0">
        <div className="p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center border border-blue-100 shrink-0">
              <MessageSquare className="w-4 h-4 text-blue-600" />
            </div>
            <span className="text-[9px] font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">+{metrics.leads_today}</span>
          </div>
          <p className="text-[10px] font-bold text-slate-500 uppercase truncate">Atendidos</p>
          <h2 className="text-2xl font-extrabold text-slate-900">{metrics.total_leads}</h2>
        </div>
      </Card>

      {/* 2. Funil de Qualificação (Ouro) */}
      <Card className="bg-white border-slate-200 shadow-sm overflow-hidden rounded-2xl group hover:border-rose-300 transition-all duration-300 flex-1 min-w-0">
        <div className="p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="w-8 h-8 bg-rose-50 rounded-lg flex items-center justify-center border border-rose-100 shrink-0">
              <Flame className="w-4 h-4 text-rose-600" />
            </div>
            <span className="text-[9px] font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">{hotRate}%</span>
          </div>
          <p className="text-[10px] font-bold text-slate-500 uppercase truncate">Quentes</p>
          <h2 className="text-2xl font-extrabold text-rose-600">{leadsHot}</h2>
        </div>
      </Card>

      {/* 3. Entrega Comercial */}
      <Card className="bg-white border-slate-200 shadow-sm overflow-hidden rounded-2xl group hover:border-emerald-300 transition-all duration-300 flex-1 min-w-0">
        <div className="p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="w-8 h-8 bg-emerald-50 rounded-lg flex items-center justify-center border border-emerald-100 shrink-0">
              <UserCheck className="w-4 h-4 text-emerald-600" />
            </div>
            <span className="text-[9px] font-bold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">Transf.</span>
          </div>
          <p className="text-[10px] font-bold text-slate-500 uppercase truncate">Enviados</p>
          <h2 className="text-2xl font-extrabold text-slate-900">{leadsTransferred + leadsQualified}</h2>
        </div>
      </Card>

      {/* Resumo de Conversão (Banner Compacto) */}
      <div className="w-full basis-full bg-slate-900 rounded-xl p-2 flex flex-wrap items-center justify-around gap-2">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-3 h-3 text-emerald-400 shrink-0" />
          <div>
            <span className="text-[8px] text-slate-400 block">Conv.</span>
            <span className="text-sm font-extrabold text-white">{metrics.conversion_rate}%</span>
          </div>
        </div>
        <div className="flex items-center gap-2 border-l border-slate-700 pl-2">
          <div>
            <span className="text-[8px] text-slate-400 block">Filtro</span>
            <span className="text-sm font-extrabold text-blue-400">{filterRate}%</span>
          </div>
        </div>
        <div className="flex items-center gap-2 border-l border-slate-700 pl-2">
          <div>
            <span className="text-[8px] text-slate-400 block">Ciclo</span>
            <span className="text-sm font-extrabold text-amber-400">
              {metrics.avg_qualification_time_hours > 0 ? `${metrics.avg_qualification_time_hours}h` : '<1h'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}