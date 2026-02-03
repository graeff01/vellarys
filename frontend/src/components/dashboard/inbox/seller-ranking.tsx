/**
 * SellerRanking - Ranking de Vendedores
 * ======================================
 *
 * Exibe ranking de performance dos vendedores
 * - Gestor: Vê todos os vendedores
 * - Vendedor: Vê sua posição destacada
 */

'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Trophy, TrendingUp, Clock, Target, Medal, Crown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getSellerRanking, formatTime, type RankingEntry } from '@/lib/metrics';

interface SellerRankingProps {
  currentUserId?: number;
  isManager?: boolean;
  compact?: boolean;
}

export function SellerRanking({ currentUserId, isManager = false, compact = false }: SellerRankingProps) {
  const [ranking, setRanking] = useState<RankingEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadRanking();
  }, [currentUserId]);

  async function loadRanking() {
    try {
      setIsLoading(true);
      const data = await getSellerRanking(currentUserId);
      setRanking(data);
    } catch (error) {
      console.error('Erro ao carregar ranking:', error);
    } finally {
      setIsLoading(false);
    }
  }

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Crown className="h-5 w-5 text-yellow-500" />;
      case 2:
        return <Medal className="h-5 w-5 text-gray-400" />;
      case 3:
        return <Medal className="h-5 w-5 text-amber-600" />;
      default:
        return <span className="text-sm font-semibold text-gray-500">#{rank}</span>;
    }
  };

  const getRankEmoji = (rank: number) => {
    switch (rank) {
      case 1:
        return '🥇';
      case 2:
        return '🥈';
      case 3:
        return '🥉';
      default:
        return `${rank}️⃣`;
    }
  };

  const getRankColor = (rank: number) => {
    switch (rank) {
      case 1:
        return 'bg-gradient-to-r from-yellow-50 to-yellow-100 border-yellow-300';
      case 2:
        return 'bg-gradient-to-r from-gray-50 to-gray-100 border-gray-300';
      case 3:
        return 'bg-gradient-to-r from-amber-50 to-amber-100 border-amber-300';
      default:
        return 'bg-white border-gray-200';
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <div className="h-5 bg-gray-200 rounded w-32 animate-pulse" />
        </CardHeader>
        <CardContent className="space-y-2">
          {Array.from({ length: compact ? 3 : 5 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
          ))}
        </CardContent>
      </Card>
    );
  }

  const displayRanking = compact ? ranking.slice(0, 5) : ranking;

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3 border-b bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-indigo-600" />
            <CardTitle className="text-base font-semibold text-gray-900">
              {isManager ? 'Ranking da Equipe' : 'Seu Desempenho na Equipe'}
            </CardTitle>
          </div>
          <button
            onClick={loadRanking}
            className="text-xs text-blue-600 hover:text-blue-700 font-medium"
          >
            Atualizar
          </button>
        </div>
      </CardHeader>

      <CardContent className="pt-4 px-3 sm:px-4">
        <div className="space-y-2">
          {displayRanking.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Trophy className="h-12 w-12 mx-auto mb-2 opacity-20" />
              <p className="text-sm">Nenhum dado de ranking disponível</p>
            </div>
          ) : (
            displayRanking.map((entry) => (
              <div
                key={entry.seller_id}
                className={cn(
                  'p-3 rounded-lg border-2 transition-all',
                  getRankColor(entry.rank),
                  entry.is_current_user && 'ring-2 ring-blue-500 ring-offset-2 scale-[1.02]'
                )}
              >
                <div className="flex items-center gap-3">
                  {/* Rank Icon */}
                  <div className="flex-shrink-0 w-10 flex items-center justify-center">
                    {getRankIcon(entry.rank)}
                  </div>

                  {/* Seller Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold text-sm text-gray-900 truncate">
                        {entry.seller_name}
                        {entry.is_current_user && (
                          <span className="ml-2 text-xs font-normal text-blue-600">(Você)</span>
                        )}
                      </h4>
                    </div>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2 text-xs">
                      <div className="flex items-center gap-1">
                        <Target className="h-3 w-3 text-purple-500" />
                        <span className="text-gray-600">
                          <span className="font-semibold text-gray-900">{entry.conversions}</span> conversões
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <TrendingUp className="h-3 w-3 text-green-500" />
                        <span className="text-gray-600">
                          <span className="font-semibold text-gray-900">{entry.conversion_rate.toFixed(1)}%</span> taxa
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3 text-orange-500" />
                        <span className="text-gray-600">
                          <span className="font-semibold text-gray-900">{formatTime(entry.avg_response_time_seconds)}</span> resp.
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-gray-600">
                          SLA: <span className="font-semibold text-gray-900">{entry.sla_compliance.toFixed(1)}%</span>
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Rank Badge */}
                  {entry.rank <= 3 && (
                    <div className="text-2xl flex-shrink-0">
                      {getRankEmoji(entry.rank)}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {!isManager && ranking.length > 5 && (
          <div className="mt-3 text-center">
            <p className="text-xs text-gray-500">
              Mostrando top 5 de {ranking.length} vendedores
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
