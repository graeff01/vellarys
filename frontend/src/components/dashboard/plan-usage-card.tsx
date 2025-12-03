'use client';

import { useEffect, useState } from 'react';
import { 
  Users, 
  MessageSquare, 
  UserPlus, 
  Clock, 
  AlertTriangle,
  Crown,
  TrendingUp,
  Zap
} from 'lucide-react';
import { getToken } from '@/lib/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface UsageData {
  period: string;
  plan: string;
  plan_slug: string;
  status: string;
  is_trial: boolean;
  trial_days_remaining: number;
  is_blocked: boolean;
  limits: {
    leads: { current: number; limit: number; percentage: number; unlimited?: boolean };
    messages: { current: number; limit: number; percentage: number; unlimited?: boolean };
    sellers: { current: number; limit: number; percentage: number; unlimited?: boolean };
  };
  features: Record<string, boolean>;
}

export function PlanUsageCard() {
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchUsage();
  }, []);

  async function fetchUsage() {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/usage`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setUsage(data);
      } else {
        setError('Não foi possível carregar dados de uso');
      }
    } catch (err) {
      console.error('Erro ao carregar uso:', err);
      setError('Erro ao conectar com servidor');
    } finally {
      setLoading(false);
    }
  }

  function getProgressColor(percentage: number): string {
    if (percentage >= 100) return 'bg-red-500';
    if (percentage >= 80) return 'bg-yellow-500';
    return 'bg-green-500';
  }

  function getProgressBgColor(percentage: number): string {
    if (percentage >= 100) return 'bg-red-100';
    if (percentage >= 80) return 'bg-yellow-100';
    return 'bg-gray-100';
  }

  function formatLimit(value: number, unlimited?: boolean): string {
    if (unlimited || value === -1) return '∞';
    return value.toLocaleString('pt-BR');
  }

  const planColors: Record<string, { bg: string; text: string; border: string }> = {
    starter: { bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-200' },
    professional: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200' },
    enterprise: { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-200' },
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
        </div>
      </div>
    );
  }

  if (error || !usage) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <p className="text-gray-500 text-sm">{error || 'Dados não disponíveis'}</p>
      </div>
    );
  }

  const colors = planColors[usage.plan_slug] || planColors.starter;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className={`px-6 py-4 border-b ${colors.border} ${colors.bg}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${colors.bg}`}>
              <Crown className={`w-5 h-5 ${colors.text}`} />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Plano {usage.plan}</h3>
              <p className="text-sm text-gray-500">
                {usage.is_trial 
                  ? `Trial • ${usage.trial_days_remaining} dias restantes`
                  : 'Assinatura ativa'
                }
              </p>
            </div>
          </div>
          
          {usage.is_blocked && (
            <span className="flex items-center gap-1 px-3 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">
              <AlertTriangle className="w-3 h-3" />
              Limite Excedido
            </span>
          )}
          
          {usage.is_trial && usage.trial_days_remaining <= 7 && !usage.is_blocked && (
            <span className="flex items-center gap-1 px-3 py-1 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full">
              <Clock className="w-3 h-3" />
              Trial Expirando
            </span>
          )}
        </div>
      </div>

      {/* Usage Bars */}
      <div className="p-6 space-y-5">
        {/* Leads */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <Users className="w-4 h-4 text-purple-500" />
              Leads
            </span>
            <span className="text-sm text-gray-500">
              {usage.limits.leads.current.toLocaleString('pt-BR')} / {formatLimit(usage.limits.leads.limit, usage.limits.leads.unlimited)}
            </span>
          </div>
          <div className={`h-2.5 rounded-full ${getProgressBgColor(usage.limits.leads.percentage)}`}>
            <div
              className={`h-full rounded-full transition-all duration-500 ${getProgressColor(usage.limits.leads.percentage)}`}
              style={{ width: `${Math.min(usage.limits.leads.percentage, 100)}%` }}
            />
          </div>
          {usage.limits.leads.percentage >= 80 && (
            <p className="text-xs text-yellow-600 mt-1">
              {usage.limits.leads.percentage >= 100 
                ? '⚠️ Limite atingido! Considere fazer upgrade.'
                : `⚠️ ${usage.limits.leads.percentage.toFixed(0)}% do limite usado`
              }
            </p>
          )}
        </div>

        {/* Mensagens */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <MessageSquare className="w-4 h-4 text-blue-500" />
              Mensagens
            </span>
            <span className="text-sm text-gray-500">
              {usage.limits.messages.current.toLocaleString('pt-BR')} / {formatLimit(usage.limits.messages.limit, usage.limits.messages.unlimited)}
            </span>
          </div>
          <div className={`h-2.5 rounded-full ${getProgressBgColor(usage.limits.messages.percentage)}`}>
            <div
              className={`h-full rounded-full transition-all duration-500 ${getProgressColor(usage.limits.messages.percentage)}`}
              style={{ width: `${Math.min(usage.limits.messages.percentage, 100)}%` }}
            />
          </div>
          {usage.limits.messages.percentage >= 80 && (
            <p className="text-xs text-yellow-600 mt-1">
              {usage.limits.messages.percentage >= 100 
                ? '⚠️ Limite atingido! Considere fazer upgrade.'
                : `⚠️ ${usage.limits.messages.percentage.toFixed(0)}% do limite usado`
              }
            </p>
          )}
        </div>

        {/* Vendedores */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <UserPlus className="w-4 h-4 text-green-500" />
              Vendedores
            </span>
            <span className="text-sm text-gray-500">
              {usage.limits.sellers.current} / {formatLimit(usage.limits.sellers.limit, usage.limits.sellers.unlimited)}
            </span>
          </div>
          <div className={`h-2.5 rounded-full ${getProgressBgColor(usage.limits.sellers.percentage)}`}>
            <div
              className={`h-full rounded-full transition-all duration-500 ${getProgressColor(usage.limits.sellers.percentage)}`}
              style={{ width: `${Math.min(usage.limits.sellers.percentage, 100)}%` }}
            />
          </div>
          {usage.limits.sellers.percentage >= 100 && (
            <p className="text-xs text-yellow-600 mt-1">
              ⚠️ Limite de vendedores atingido
            </p>
          )}
        </div>

        {/* Period info */}
        <div className="pt-3 border-t border-gray-100">
          <p className="text-xs text-gray-400 text-center">
            Período: {usage.period} • Renova todo dia 1º
          </p>
        </div>
      </div>

      {/* Footer com upgrade */}
      {(usage.plan_slug !== 'enterprise' || usage.is_trial) && (
        <div className="px-6 py-4 bg-gradient-to-r from-purple-50 to-blue-50 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-purple-600" />
              <span className="text-sm text-gray-700">
                {usage.is_trial 
                  ? 'Assine agora e não perca seus dados!'
                  : 'Precisa de mais? Faça upgrade!'
                }
              </span>
            </div>
            <button className="px-4 py-1.5 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 transition-colors">
              {usage.is_trial ? 'Assinar' : 'Upgrade'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}