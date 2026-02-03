/**
 * MetricsDashboard - Dashboard de Métricas Inteligente
 * =====================================================
 *
 * Exibe métricas adequadas baseadas no perfil do usuário:
 * - GESTOR: Métricas da empresa, ranking completo, análise da equipe
 * - VENDEDOR: Métricas pessoais, metas, posição no ranking
 */

'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, MessageSquare, TrendingUp, Clock, CheckCircle2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getSellerMetrics, formatTime, type SellerMetrics } from '@/lib/metrics';
import { CompanyMetrics } from './company-metrics';
import { SellerRanking } from './seller-ranking';
import { GoalsProgress } from './goals-progress';
import { TeamAnalysis } from './team-analysis';
import type { SellerInfo } from '@/lib/inbox';

interface MetricsDashboardProps {
  sellerInfo: SellerInfo | null;
}

export function MetricsDashboard({ sellerInfo }: MetricsDashboardProps) {
  const [metrics, setMetrics] = useState<SellerMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Determina se é gestor baseado no role
  const isManager = sellerInfo?.user_role === 'manager' || sellerInfo?.user_role === 'admin';
  const currentUserId = sellerInfo?.seller_id || sellerInfo?.user_id;

  useEffect(() => {
    if (!isManager) {
      loadSellerMetrics();
    } else {
      setIsLoading(false);
    }
  }, [isManager]);

  async function loadSellerMetrics() {
    try {
      setIsLoading(true);
      const data = await getSellerMetrics();
      setMetrics(data);
    } catch (error) {
      console.error('Erro ao carregar métricas:', error);
    } finally {
      setIsLoading(false);
    }
  }

  // ============================================================================
  // GESTOR VIEW
  // ============================================================================
  if (isManager) {
    return (
      <div className="space-y-4">
        {/* Métricas Consolidadas da Empresa */}
        <CompanyMetrics />

        {/* Grid: Ranking + Análise da Equipe */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SellerRanking currentUserId={currentUserId} isManager={true} />
          <TeamAnalysis />
        </div>
      </div>
    );
  }

  // ============================================================================
  // VENDEDOR VIEW
  // ============================================================================

  // Loading State
  if (isLoading) {
    return (
      <div className="space-y-4">
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
      </div>
    );
  }

  // Error State
  if (!metrics) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="py-4">
          <p className="text-sm text-red-600">Erro ao carregar métricas pessoais</p>
        </CardContent>
      </Card>
    );
  }

  const stats = [
    {
      label: 'Meus Leads',
      value: metrics.total_leads ?? 0,
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      label: 'Minhas Conversas',
      value: metrics.active_conversations ?? 0,
      icon: MessageSquare,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      label: 'Minhas Mensagens',
      value: metrics.total_messages ?? 0,
      icon: TrendingUp,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      label: 'Meu Tempo 1ª Resposta',
      value: formatTime(metrics.avg_first_response_time_seconds ?? 0),
      icon: Clock,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
    {
      label: 'Minha Taxa Conversão',
      value: `${(metrics.conversion_rate ?? 0).toFixed(1)}%`,
      icon: CheckCircle2,
      color: 'text-teal-600',
      bgColor: 'bg-teal-50',
    },
    {
      label: 'Meu SLA',
      value: `${(metrics.sla_compliance ?? 0).toFixed(1)}%`,
      icon: AlertCircle,
      color: (metrics.sla_compliance ?? 0) >= 80 ? 'text-green-600' : 'text-red-600',
      bgColor: (metrics.sla_compliance ?? 0) >= 80 ? 'bg-green-50' : 'bg-red-50',
    },
  ];

  return (
    <div className="space-y-4">
      {/* Título */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Minhas Métricas</h3>
          <p className="text-xs text-gray-500">Performance pessoal</p>
        </div>
        <button
          onClick={loadSellerMetrics}
          className="text-xs text-blue-600 hover:text-blue-700 font-medium"
        >
          Atualizar
        </button>
      </div>

      {/* Métricas Pessoais */}
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

      {/* Grid: Metas + Ranking */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <GoalsProgress sellerId={currentUserId} />
        <SellerRanking currentUserId={currentUserId} isManager={false} compact={true} />
      </div>
    </div>
  );
}
