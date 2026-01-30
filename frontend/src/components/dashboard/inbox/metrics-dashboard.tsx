/**
 * MetricsDashboard - Dashboard de Métricas do Vendedor
 * ====================================================
 *
 * Exibe métricas de performance do vendedor no inbox.
 */

'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, MessageSquare, TrendingUp, Clock, CheckCircle2, AlertCircle } from 'lucide-react';
import axios from 'axios';
import { cn } from '@/lib/utils';

interface Metrics {
  total_leads: number;
  active_conversations: number;
  total_messages: number;
  avg_first_response_time_seconds: number;
  conversion_rate: number;
  sla_compliance: number;
}

export function MetricsDashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadMetrics();
  }, []);

  async function loadMetrics() {
    try {
      setIsLoading(true);
      const token = localStorage.getItem('token');

      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/v1/seller/inbox/metrics`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setMetrics(response.data);
    } catch (error) {
      console.error('Erro ao carregar métricas:', error);
    } finally {
      setIsLoading(false);
    }
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
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
          <p className="text-sm text-red-600">Erro ao carregar métricas</p>
        </CardContent>
      </Card>
    );
  }

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}min`;
    return `${Math.round(seconds / 3600)}h`;
  };

  const stats = [
    {
      label: 'Total de Leads',
      value: metrics.total_leads,
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      label: 'Conversas Ativas',
      value: metrics.active_conversations,
      icon: MessageSquare,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      label: 'Mensagens Enviadas',
      value: metrics.total_messages,
      icon: TrendingUp,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      label: 'Tempo Médio 1ª Resposta',
      value: formatTime(metrics.avg_first_response_time_seconds),
      icon: Clock,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
    {
      label: 'Taxa de Conversão',
      value: `${metrics.conversion_rate.toFixed(1)}%`,
      icon: CheckCircle2,
      color: 'text-teal-600',
      bgColor: 'bg-teal-50',
    },
    {
      label: 'SLA Compliance',
      value: `${metrics.sla_compliance.toFixed(1)}%`,
      icon: AlertCircle,
      color: metrics.sla_compliance >= 80 ? 'text-green-600' : 'text-red-600',
      bgColor: metrics.sla_compliance >= 80 ? 'bg-green-50' : 'bg-red-50',
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
      {stats.map((stat, index) => {
        const Icon = stat.icon;
        return (
          <Card key={index} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-2 space-y-0">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs sm:text-sm font-medium text-muted-foreground">
                  {stat.label}
                </CardTitle>
                <div className={cn('p-1.5 sm:p-2 rounded-lg', stat.bgColor)}>
                  <Icon className={cn('h-3 w-3 sm:h-4 sm:w-4', stat.color)} />
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-2">
              <div className="text-xl sm:text-2xl font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
