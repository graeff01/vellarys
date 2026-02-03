/**
 * CompanyMetrics - Métricas Consolidadas da Empresa
 * ==================================================
 *
 * Exibe métricas agregadas de toda a empresa (apenas para gestores)
 */

'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Users,
  MessageSquare,
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertCircle,
  UserCheck,
  DollarSign,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getCompanyMetrics, formatTime, formatCurrency, type CompanyMetrics as CompanyMetricsType } from '@/lib/metrics';

export function CompanyMetrics() {
  const [metrics, setMetrics] = useState<CompanyMetricsType | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadMetrics();
  }, []);

  async function loadMetrics() {
    try {
      setIsLoading(true);
      const data = await getCompanyMetrics();
      setMetrics(data);
    } catch (error) {
      console.error('Erro ao carregar métricas da empresa:', error);
    } finally {
      setIsLoading(false);
    }
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8 gap-3 sm:gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <div className="h-4 bg-gray-200 rounded w-20" />
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-gray-200 rounded w-12" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!metrics) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="py-4">
          <p className="text-sm text-red-600">Erro ao carregar métricas da empresa</p>
        </CardContent>
      </Card>
    );
  }

  const stats = [
    {
      label: 'Total de Leads',
      value: metrics.total_leads.toLocaleString('pt-BR'),
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      description: 'Empresa',
    },
    {
      label: 'Conversas Ativas',
      value: metrics.active_conversations.toLocaleString('pt-BR'),
      icon: MessageSquare,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      description: 'Em andamento',
    },
    {
      label: 'Conversões Totais',
      value: metrics.total_conversions.toLocaleString('pt-BR'),
      icon: CheckCircle2,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
      description: 'Fechadas',
    },
    {
      label: 'Taxa de Conversão',
      value: `${metrics.conversion_rate.toFixed(1)}%`,
      icon: TrendingUp,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      description: 'Média geral',
    },
    {
      label: 'Tempo Médio 1ª Resposta',
      value: formatTime(metrics.avg_first_response_time_seconds),
      icon: Clock,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      description: 'Equipe',
    },
    {
      label: 'SLA Compliance',
      value: `${metrics.sla_compliance.toFixed(1)}%`,
      icon: AlertCircle,
      color: metrics.sla_compliance >= 80 ? 'text-green-600' : 'text-red-600',
      bgColor: metrics.sla_compliance >= 80 ? 'bg-green-50' : 'bg-red-50',
      description: 'Cumprimento',
    },
    {
      label: 'Vendedores Ativos',
      value: `${metrics.active_sellers}/${metrics.total_sellers}`,
      icon: UserCheck,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-50',
      description: 'Online agora',
    },
    {
      label: 'Receita Gerada',
      value: formatCurrency(metrics.revenue_generated),
      icon: DollarSign,
      color: 'text-teal-600',
      bgColor: 'bg-teal-50',
      description: 'Total',
    },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Métricas da Empresa</h3>
          <p className="text-xs text-gray-500">Visão consolidada de toda a equipe</p>
        </div>
        <button
          onClick={loadMetrics}
          className="text-xs text-blue-600 hover:text-blue-700 font-medium"
        >
          Atualizar
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8 gap-3 sm:gap-4">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card
              key={index}
              className="hover:shadow-md transition-all hover:scale-105 cursor-pointer border-l-4"
              style={{ borderLeftColor: stat.color.replace('text-', '').replace('-600', '') }}
            >
              <CardHeader className="pb-2 space-y-0">
                <div className="flex items-start justify-between mb-1">
                  <CardTitle className="text-[10px] sm:text-xs font-medium text-muted-foreground leading-tight">
                    {stat.label}
                  </CardTitle>
                  <div className={cn('p-1 sm:p-1.5 rounded-lg', stat.bgColor)}>
                    <Icon className={cn('h-3 w-3 sm:h-3.5 sm:w-3.5', stat.color)} />
                  </div>
                </div>
                <p className="text-[9px] text-gray-400">{stat.description}</p>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="text-lg sm:text-xl font-bold">{stat.value}</div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
