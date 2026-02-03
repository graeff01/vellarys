/**
 * TeamAnalysis - Análise da Equipe
 * =================================
 *
 * Exibe análise detalhada de cada vendedor (apenas para gestores)
 */

'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Users,
  TrendingUp,
  MessageSquare,
  Clock,
  CheckCircle2,
  DollarSign,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getTeamAnalytics, formatTime, formatCurrency, type SellerAnalytics } from '@/lib/metrics';

export function TeamAnalysis() {
  const [sellers, setSellers] = useState<SellerAnalytics[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedSellerId, setExpandedSellerId] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<'conversions' | 'conversion_rate' | 'revenue'>('conversions');

  useEffect(() => {
    loadTeamAnalytics();
  }, []);

  async function loadTeamAnalytics() {
    try {
      setIsLoading(true);
      const data = await getTeamAnalytics();
      setSellers(data);
    } catch (error) {
      console.error('Erro ao carregar análise da equipe:', error);
    } finally {
      setIsLoading(false);
    }
  }

  const sortedSellers = [...sellers].sort((a, b) => {
    switch (sortBy) {
      case 'conversions':
        return b.total_conversions - a.total_conversions;
      case 'conversion_rate':
        return (b.conversion_rate || 0) - (a.conversion_rate || 0);
      case 'revenue':
        return b.revenue_generated - a.revenue_generated;
      default:
        return 0;
    }
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <div className="h-5 bg-gray-200 rounded w-32 animate-pulse" />
        </CardHeader>
        <CardContent className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 bg-gray-100 rounded animate-pulse" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (sellers.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3 border-b bg-gradient-to-r from-indigo-50 to-purple-50">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-indigo-600" />
            <CardTitle className="text-base font-semibold text-gray-900">
              Análise por Vendedor
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="py-8">
          <div className="text-center text-muted-foreground">
            <Users className="h-12 w-12 mx-auto mb-2 opacity-20" />
            <p className="text-sm">Nenhum vendedor cadastrado</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3 border-b bg-gradient-to-r from-indigo-50 to-purple-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-indigo-600" />
            <CardTitle className="text-base font-semibold text-gray-900">
              Análise por Vendedor
            </CardTitle>
          </div>

          {/* Sort Buttons */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setSortBy('conversions')}
              className={cn(
                'px-2 py-1 text-xs rounded transition-colors',
                sortBy === 'conversions'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-100'
              )}
            >
              Conversões
            </button>
            <button
              onClick={() => setSortBy('conversion_rate')}
              className={cn(
                'px-2 py-1 text-xs rounded transition-colors',
                sortBy === 'conversion_rate'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-100'
              )}
            >
              Taxa
            </button>
            <button
              onClick={() => setSortBy('revenue')}
              className={cn(
                'px-2 py-1 text-xs rounded transition-colors',
                sortBy === 'revenue'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-100'
              )}
            >
              Receita
            </button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-2">
        {sortedSellers.map((seller, index) => {
          const isExpanded = expandedSellerId === seller.seller_id;
          const isTopPerformer = index === 0;

          return (
            <div
              key={seller.seller_id}
              className={cn(
                'rounded-lg border-2 transition-all overflow-hidden',
                isTopPerformer ? 'border-yellow-300 bg-yellow-50' : 'border-gray-200 bg-white',
                isExpanded && 'shadow-md'
              )}
            >
              {/* Header - Always Visible */}
              <button
                onClick={() => setExpandedSellerId(isExpanded ? null : seller.seller_id)}
                className="w-full p-3 text-left hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  {/* Seller Info */}
                  <div className="flex items-center gap-3 flex-1">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                      <span className="text-sm font-semibold text-white">
                        {seller.seller_name.charAt(0).toUpperCase()}
                      </span>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-sm text-gray-900 truncate">
                          {seller.seller_name}
                        </h4>
                        {isTopPerformer && (
                          <span className="px-2 py-0.5 bg-yellow-200 text-yellow-800 text-xs rounded-full font-medium">
                            ⭐ Top
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 truncate">{seller.seller_email}</p>
                    </div>
                  </div>

                  {/* Quick Stats */}
                  <div className="flex items-center gap-4 mr-2">
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Conversões</p>
                      <p className="text-sm font-bold text-gray-900">{seller.total_conversions}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Taxa</p>
                      <p className="text-sm font-bold text-gray-900">
                        {(seller.conversion_rate || 0).toFixed(1)}%
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Receita</p>
                      <p className="text-sm font-bold text-gray-900">
                        {formatCurrency(seller.revenue_generated)}
                      </p>
                    </div>
                  </div>

                  {/* Expand Icon */}
                  {isExpanded ? (
                    <ChevronUp className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  )}
                </div>
              </button>

              {/* Expanded Details */}
              {isExpanded && (
                <div className="px-3 pb-3 pt-1 border-t bg-gray-50">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-2">
                    <div className="flex items-center gap-2 p-2 bg-white rounded border">
                      <Users className="h-4 w-4 text-blue-500" />
                      <div>
                        <p className="text-xs text-gray-500">Total Leads</p>
                        <p className="text-sm font-semibold text-gray-900">
                          {(seller.total_leads || 0).toLocaleString('pt-BR')}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 p-2 bg-white rounded border">
                      <MessageSquare className="h-4 w-4 text-green-500" />
                      <div>
                        <p className="text-xs text-gray-500">Conversas</p>
                        <p className="text-sm font-semibold text-gray-900">
                          {(seller.active_conversations || 0).toLocaleString('pt-BR')}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 p-2 bg-white rounded border">
                      <Clock className="h-4 w-4 text-orange-500" />
                      <div>
                        <p className="text-xs text-gray-500">Tempo Resp.</p>
                        <p className="text-sm font-semibold text-gray-900">
                          {formatTime(seller.avg_first_response_time_seconds || 0)}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 p-2 bg-white rounded border">
                      <CheckCircle2 className="h-4 w-4 text-teal-500" />
                      <div>
                        <p className="text-xs text-gray-500">SLA</p>
                        <p className="text-sm font-semibold text-gray-900">
                          {(seller.sla_compliance || 0).toFixed(1)}%
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="mt-2 text-xs text-gray-500">
                    Ativo desde {new Date(seller.active_since).toLocaleDateString('pt-BR')}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
