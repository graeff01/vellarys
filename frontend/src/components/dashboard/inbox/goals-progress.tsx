/**
 * GoalsProgress - Progresso das Metas
 * ====================================
 *
 * Exibe metas definidas pelo gestor e progresso do vendedor
 */

'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Target, CheckCircle, TrendingUp, Clock, DollarSign, Users, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  getSellerGoals,
  calculateProgress,
  getGoalTypeLabel,
  formatTime,
  formatCurrency,
  type Goal,
} from '@/lib/metrics';

interface GoalsProgressProps {
  sellerId?: number;
}

export function GoalsProgress({ sellerId }: GoalsProgressProps) {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadGoals();
  }, [sellerId]);

  async function loadGoals() {
    try {
      setIsLoading(true);
      const data = await getSellerGoals(sellerId);
      setGoals(data);
    } catch (error) {
      console.error('Erro ao carregar metas:', error);
    } finally {
      setIsLoading(false);
    }
  }

  const getGoalIcon = (type: Goal['goal_type']) => {
    switch (type) {
      case 'conversions':
        return CheckCircle;
      case 'leads':
        return Users;
      case 'sla':
        return Target;
      case 'response_time':
        return Clock;
      case 'revenue':
        return DollarSign;
      default:
        return Target;
    }
  };

  const getGoalColor = (progress: number) => {
    if (progress >= 100) return 'text-green-600';
    if (progress >= 70) return 'text-blue-600';
    if (progress >= 40) return 'text-orange-600';
    return 'text-red-600';
  };

  const getGoalBgColor = (progress: number) => {
    if (progress >= 100) return 'bg-green-50';
    if (progress >= 70) return 'bg-blue-50';
    if (progress >= 40) return 'bg-orange-50';
    return 'bg-red-50';
  };

  const getProgressBarColor = (progress: number) => {
    if (progress >= 100) return 'bg-green-500';
    if (progress >= 70) return 'bg-blue-500';
    if (progress >= 40) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const formatGoalValue = (type: Goal['goal_type'], value: number) => {
    switch (type) {
      case 'conversions':
      case 'leads':
        return value.toLocaleString('pt-BR');
      case 'sla':
        return `${value}%`;
      case 'response_time':
        return formatTime(value);
      case 'revenue':
        return formatCurrency(value);
      default:
        return value.toString();
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <div className="h-5 bg-gray-200 rounded w-32 animate-pulse" />
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 bg-gray-200 rounded w-24 animate-pulse" />
              <div className="h-8 bg-gray-100 rounded animate-pulse" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (goals.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3 border-b bg-gradient-to-r from-purple-50 to-pink-50">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-purple-600" />
            <CardTitle className="text-base font-semibold text-gray-900">
              Metas do Período
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="py-8">
          <div className="text-center text-muted-foreground">
            <Target className="h-12 w-12 mx-auto mb-2 opacity-20" />
            <p className="text-sm">Nenhuma meta definida ainda</p>
            <p className="text-xs mt-1">Aguarde o gestor definir suas metas</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3 border-b bg-gradient-to-r from-purple-50 to-pink-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-purple-600" />
            <CardTitle className="text-base font-semibold text-gray-900">
              Metas do Período
            </CardTitle>
          </div>
          <button
            onClick={loadGoals}
            className="text-xs text-blue-600 hover:text-blue-700 font-medium"
          >
            Atualizar
          </button>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-3">
        {goals.map((goal) => {
          const Icon = getGoalIcon(goal.goal_type);
          const progress = calculateProgress(goal.current_value, goal.target_value);
          const isCompleted = progress >= 100;
          const isOnTrack = progress >= 70;

          return (
            <div
              key={goal.id}
              className={cn(
                'p-3 rounded-lg border-2 transition-all',
                isCompleted ? 'bg-green-50 border-green-200' : 'bg-white border-gray-200'
              )}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2 flex-1">
                  <div className={cn('p-1.5 rounded-lg', getGoalBgColor(progress))}>
                    <Icon className={cn('h-4 w-4', getGoalColor(progress))} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-sm text-gray-900">
                      {getGoalTypeLabel(goal.goal_type)}
                    </h4>
                    <p className="text-xs text-gray-500">
                      Definida por {goal.created_by_name}
                    </p>
                  </div>
                </div>

                {/* Status Badge */}
                <div
                  className={cn(
                    'px-2 py-1 rounded-full text-xs font-medium',
                    isCompleted
                      ? 'bg-green-100 text-green-700'
                      : isOnTrack
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-orange-100 text-orange-700'
                  )}
                >
                  {isCompleted ? '✓ Atingida' : isOnTrack ? 'No caminho' : 'Atenção'}
                </div>
              </div>

              {/* Progress Bar */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-gray-700">
                    {formatGoalValue(goal.goal_type, goal.current_value)} de{' '}
                    {formatGoalValue(goal.goal_type, goal.target_value)}
                  </span>
                  <span className={cn('font-semibold', getGoalColor(progress))}>
                    {progress}%
                  </span>
                </div>

                {/* Progress Bar */}
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full transition-all duration-500 rounded-full',
                      getProgressBarColor(progress)
                    )}
                    style={{ width: `${Math.min(progress, 100)}%` }}
                  />
                </div>
              </div>

              {/* Warning for low progress */}
              {!isCompleted && progress < 40 && (
                <div className="mt-2 flex items-start gap-1.5 text-xs text-orange-600">
                  <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                  <span>
                    Você precisa de mais {goal.target_value - goal.current_value}{' '}
                    {goal.goal_type === 'conversions' ? 'conversões' : 'para atingir a meta'}
                  </span>
                </div>
              )}
            </div>
          );
        })}

        {/* Summary */}
        <div className="pt-3 border-t">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-600">
              Metas atingidas: {goals.filter(g => calculateProgress(g.current_value, g.target_value) >= 100).length} de {goals.length}
            </span>
            <span className="text-gray-600">
              Média de progresso:{' '}
              <span className="font-semibold text-gray-900">
                {Math.round(goals.reduce((acc, g) => acc + calculateProgress(g.current_value, g.target_value), 0) / goals.length)}%
              </span>
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
