'use client';

import { useState, useEffect } from 'react';
import { getProposals, getProposalsStats, type CommercialProposal } from '@/lib/proposals';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Building2,
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle2,
  XCircle,
  Plus,
  Filter
} from 'lucide-react';

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<CommercialProposal[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadData();
  }, [filter]);

  async function loadData() {
    try {
      setLoading(true);
      const [proposalsData, statsData] = await Promise.all([
        getProposals(filter === 'all' ? {} : { status: filter }),
        getProposalsStats()
      ]);
      setProposals(proposalsData);
      setStats(statsData);
    } catch (error) {
      console.error('Erro ao carregar propostas:', error);
    } finally {
      setLoading(false);
    }
  }

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; className: string; icon: any }> = {
      pending: { label: 'Pendente', className: 'bg-yellow-100 text-yellow-800', icon: Clock },
      owner_accepted: { label: 'Aceita', className: 'bg-green-100 text-green-800', icon: CheckCircle2 },
      owner_rejected: { label: 'Rejeitada', className: 'bg-red-100 text-red-800', icon: XCircle },
      closed: { label: 'Fechada', className: 'bg-blue-100 text-blue-800', icon: CheckCircle2 },
      negotiating: { label: 'Negociando', className: 'bg-purple-100 text-purple-800', icon: TrendingUp },
    };

    const config = statusConfig[status] || { label: status, className: 'bg-gray-100 text-gray-800', icon: Clock };
    const Icon = config.icon;

    return (
      <Badge className={config.className}>
        <Icon className="w-3 h-3 mr-1" />
        {config.label}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="text-gray-500">Carregando propostas...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Building2 className="w-8 h-8" />
            Propostas Comerciais
          </h1>
          <p className="text-gray-500 mt-1">Gestão de negociações imobiliárias</p>
        </div>

        <Button className="gap-2">
          <Plus className="w-4 h-4" />
          Nova Proposta
        </Button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card className="p-4">
            <div className="text-sm text-gray-500">Total de Propostas</div>
            <div className="text-2xl font-bold mt-1">{stats.total_proposals}</div>
          </Card>

          <Card className="p-4">
            <div className="text-sm text-gray-500">Taxa de Conversão</div>
            <div className="text-2xl font-bold mt-1 text-green-600">
              {stats.conversion_rate}%
            </div>
          </Card>

          <Card className="p-4">
            <div className="text-sm text-gray-500">Fechadas</div>
            <div className="text-2xl font-bold mt-1 text-blue-600">{stats.closed}</div>
          </Card>

          <Card className="p-4">
            <div className="text-sm text-gray-500">Valor Médio Final</div>
            <div className="text-2xl font-bold mt-1">
              R$ {(stats.avg_final_value / 1000).toFixed(0)}k
            </div>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        <Button
          variant={filter === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('all')}
        >
          Todas
        </Button>
        <Button
          variant={filter === 'pending' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('pending')}
        >
          Pendentes
        </Button>
        <Button
          variant={filter === 'negotiating' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('negotiating')}
        >
          Negociando
        </Button>
        <Button
          variant={filter === 'closed' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('closed')}
        >
          Fechadas
        </Button>
      </div>

      {/* Proposals List */}
      <div className="space-y-4">
        {proposals.length === 0 ? (
          <Card className="p-12 text-center">
            <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-700 mb-2">
              Nenhuma proposta encontrada
            </h3>
            <p className="text-gray-500">
              Crie sua primeira proposta para começar a negociar!
            </p>
          </Card>
        ) : (
          proposals.map((proposal) => (
            <Card key={proposal.id} className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {proposal.lead_name}
                    </h3>
                    {getStatusBadge(proposal.status)}
                  </div>

                  <div className="text-sm text-gray-600 mb-3">
                    <span className="font-medium">{proposal.property_info.type}</span>
                    {' • '}
                    {proposal.property_info.address}
                    {proposal.property_info.rooms && (
                      <>
                        {' • '}
                        {proposal.property_info.rooms} quartos
                      </>
                    )}
                  </div>

                  <div className="flex items-center gap-6">
                    <div>
                      <div className="text-xs text-gray-500">Valor Pedido</div>
                      <div className="text-lg font-semibold text-gray-900">
                        R$ {proposal.asked_value.toLocaleString('pt-BR')}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs text-gray-500">Valor Oferecido</div>
                      <div className="text-lg font-semibold text-blue-600">
                        R$ {proposal.offered_value.toLocaleString('pt-BR')}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs text-gray-500">Diferença</div>
                      <div className={`text-lg font-semibold flex items-center gap-1 ${
                        proposal.diff_value > 0 ? 'text-red-600' : 'text-green-600'
                      }`}>
                        {proposal.diff_value > 0 ? (
                          <TrendingDown className="w-4 h-4" />
                        ) : (
                          <TrendingUp className="w-4 h-4" />
                        )}
                        {Math.abs(proposal.diff_percentage)}%
                      </div>
                    </div>

                    {proposal.final_value && (
                      <div>
                        <div className="text-xs text-gray-500">Valor Final</div>
                        <div className="text-lg font-semibold text-green-600">
                          R$ {proposal.final_value.toLocaleString('pt-BR')}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <Button variant="outline" size="sm">
                    Ver Detalhes
                  </Button>
                  {proposal.status === 'pending' && (
                    <Button size="sm" className="bg-green-600 hover:bg-green-700">
                      Fechar Negócio
                    </Button>
                  )}
                </div>
              </div>

              {/* Timeline Preview */}
              {proposal.timeline && proposal.timeline.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <div className="text-xs text-gray-500 mb-2">Últimos eventos:</div>
                  <div className="space-y-1">
                    {proposal.timeline.slice(-3).reverse().map((event, idx) => (
                      <div key={idx} className="text-xs text-gray-600 flex items-center gap-2">
                        <span className="text-gray-400">
                          {new Date(event.date).toLocaleDateString('pt-BR')}
                        </span>
                        <span>•</span>
                        <span>{event.note || event.event}</span>
                        {event.value && (
                          <span className="font-semibold">
                            R$ {event.value.toLocaleString('pt-BR')}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
