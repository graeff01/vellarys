'use client';

import { Card } from '@/components/ui/card';
import { Users, Flame, UserCheck, Filter, Clock, TrendingUp, MessageSquare, Zap } from 'lucide-react';

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
  // Calcula métricas derivadas
  const leadsHot = metrics.by_qualification?.hot || metrics.by_qualification?.quente || 0;
  const leadsWarm = metrics.by_qualification?.warm || metrics.by_qualification?.morno || 0;
  const leadsCold = metrics.by_qualification?.cold || metrics.by_qualification?.frio || 0;
  
  const leadsTransferred = metrics.by_status?.handed_off || metrics.by_status?.transferido || 0;
  const leadsQualified = metrics.by_status?.qualified || metrics.by_status?.qualificado || 0;
  
  // Taxa de leads quentes (eficiência da IA em encontrar compradores)
  const hotRate = metrics.total_leads > 0 
    ? Math.round((leadsHot / metrics.total_leads) * 100) 
    : 0;
  
  // Taxa de filtro (leads frios = curiosos filtrados)
  const filterRate = metrics.total_leads > 0 
    ? Math.round((leadsCold / metrics.total_leads) * 100) 
    : 0;

  return (
    <div className="space-y-6">
      {/* Cards principais - Resultado da IA */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-blue-100">
              <MessageSquare className="w-6 h-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Atendidos pela IA</p>
              <p className="text-2xl font-bold text-gray-900">{metrics.total_leads}</p>
              <p className="text-xs text-gray-400">{metrics.leads_today} hoje</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-red-100">
              <Flame className="w-6 h-6 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Prontos p/ Comprar</p>
              <p className="text-2xl font-bold text-red-600">{leadsHot}</p>
              <p className="text-xs text-green-600 font-medium">{hotRate}% dos leads</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-green-100">
              <UserCheck className="w-6 h-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Entregues p/ Vendedor</p>
              <p className="text-2xl font-bold text-gray-900">{leadsTransferred + leadsQualified}</p>
              <p className="text-xs text-gray-400">qualificados</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center">
            <div className="p-3 rounded-lg bg-gray-100">
              <Filter className="w-6 h-6 text-gray-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Curiosos Filtrados</p>
              <p className="text-2xl font-bold text-gray-900">{leadsCold}</p>
              <p className="text-xs text-blue-600 font-medium">{filterRate}% bloqueados</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Cards secundários - Performance */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Leads Interessados</p>
              <p className="text-xl font-bold text-yellow-600">{leadsWarm}</p>
            </div>
            <div className="p-2 rounded-lg bg-yellow-100">
              <Zap className="w-5 h-5 text-yellow-600" />
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">Ainda em conversa com a IA</p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Tempo Médio</p>
              <p className="text-xl font-bold text-gray-900">
                {metrics.avg_qualification_time_hours > 0 
                  ? `${metrics.avg_qualification_time_hours}h` 
                  : '< 1h'}
              </p>
            </div>
            <div className="p-2 rounded-lg bg-purple-100">
              <Clock className="w-5 h-5 text-purple-600" />
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">Para qualificar um lead</p>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Taxa de Conversão</p>
              <p className="text-xl font-bold text-green-600">{metrics.conversion_rate}%</p>
            </div>
            <div className="p-2 rounded-lg bg-green-100">
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">Leads que avançaram</p>
        </Card>
      </div>
    </div>
  );
}