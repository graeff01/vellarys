'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Building2,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Clock,
  CheckCircle2,
  XCircle,
  Plus,
  Search,
  Filter,
  Calendar,
  MapPin,
  User
} from 'lucide-react';
import { getOpportunities, getOpportunityMetrics, type Opportunity, type OpportunityMetrics } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { OpportunityModal } from '@/components/dashboard/OpportunityModal';
import { CreateOpportunityModal } from '@/components/dashboard/CreateOpportunityModal';

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [metrics, setMetrics] = useState<OpportunityMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedOpportunityId, setSelectedOpportunityId] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  async function loadData() {
    try {
      setLoading(true);
      const [oppsData, metricsData] = await Promise.all([
        getOpportunities({ status: statusFilter === 'all' ? undefined : statusFilter }),
        getOpportunityMetrics()
      ]);
      setOpportunities(oppsData.items || oppsData);
      setMetrics(metricsData);
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Erro ao carregar oportunidades',
        description: error.response?.data?.detail || 'Tente novamente'
      });
    } finally {
      setLoading(false);
    }
  }

  const filteredOpportunities = opportunities.filter(opp => {
    const searchLower = searchQuery.toLowerCase();
    return (
      !searchQuery ||
      opp.title.toLowerCase().includes(searchLower) ||
      opp.product_name?.toLowerCase().includes(searchLower) ||
      opp.seller_name?.toLowerCase().includes(searchLower)
    );
  });

  const getStatusConfig = (status: string) => {
    const configs: Record<string, { label: string; className: string; icon: any }> = {
      novo: { label: 'Nova', className: 'bg-blue-100 text-blue-800', icon: Clock },
      negociacao: { label: 'Em Negociação', className: 'bg-yellow-100 text-yellow-800', icon: TrendingUp },
      proposta: { label: 'Proposta Enviada', className: 'bg-purple-100 text-purple-800', icon: TrendingUp },
      ganho: { label: 'Fechada', className: 'bg-green-100 text-green-800', icon: CheckCircle2 },
      perdido: { label: 'Perdida', className: 'bg-red-100 text-red-800', icon: XCircle },
    };
    return configs[status] || configs.novo;
  };

  const formatValue = (cents: number) => {
    const reais = cents / 100;
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(reais);
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="text-gray-500">Carregando oportunidades...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <TrendingUp className="w-8 h-8" />
            Oportunidades
          </h1>
          <p className="text-gray-500 mt-1">Gerencie suas oportunidades de negócio</p>
        </div>
        <Button onClick={() => setCreateModalOpen(true)} className="gap-2">
          <Plus className="w-4 h-4" />
          Nova Oportunidade
        </Button>
      </div>

      {/* Métricas */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total</p>
                <p className="text-2xl font-bold mt-1">{metrics.total}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <Building2 className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Valor Total</p>
                <p className="text-2xl font-bold mt-1 text-green-600">
                  {formatValue(metrics.total_value)}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <DollarSign className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Fechadas</p>
                <p className="text-2xl font-bold mt-1 text-blue-600">{metrics.by_status?.won || 0}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <CheckCircle2 className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Taxa de Conversão</p>
                <p className="text-2xl font-bold mt-1 text-purple-600">{metrics.conversion_rate}%</p>
              </div>
              <div className="p-3 bg-purple-100 rounded-lg">
                <TrendingUp className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Filtros */}
      <div className="flex gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Buscar oportunidades..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        <div className="flex gap-2">
          <Button
            variant={statusFilter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter('all')}
          >
            Todas
          </Button>
          <Button
            variant={statusFilter === 'novo' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter('novo')}
          >
            Novas
          </Button>
          <Button
            variant={statusFilter === 'negociacao' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter('negociacao')}
          >
            Em Negociação
          </Button>
          <Button
            variant={statusFilter === 'proposta' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter('proposta')}
          >
            Proposta Enviada
          </Button>
          <Button
            variant={statusFilter === 'ganho' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter('ganho')}
          >
            Fechadas
          </Button>
        </div>
      </div>

      {/* Grid de Oportunidades */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredOpportunities.length === 0 ? (
          <Card className="col-span-full p-12 text-center">
            <TrendingUp className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-700 mb-2">
              Nenhuma oportunidade encontrada
            </h3>
            <p className="text-gray-500">
              {searchQuery ? 'Tente buscar outros termos' : 'As oportunidades aparecerão aqui'}
            </p>
          </Card>
        ) : (
          filteredOpportunities.map((opportunity) => {
            const statusConfig = getStatusConfig(opportunity.status);
            const StatusIcon = statusConfig.icon;

            return (
              <div
                key={opportunity.id}
                className="cursor-pointer"
                onClick={() => {
                  setSelectedOpportunityId(opportunity.id);
                  setModalOpen(true);
                }}
              >
                <Card className="p-4 hover:shadow-lg transition-all border border-gray-200 h-full">
                  {/* Header com Status */}
                  <div className="flex items-start justify-between mb-3">
                    <Badge className={statusConfig.className}>
                      <StatusIcon className="w-3 h-3 mr-1" />
                      {statusConfig.label}
                    </Badge>
                    {opportunity.value > 0 && (
                      <span className="text-lg font-bold text-green-600">
                        {formatValue(opportunity.value)}
                      </span>
                    )}
                  </div>

                  {/* Título */}
                  <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2">
                    {opportunity.title}
                  </h3>

                  {/* Produto/Imóvel */}
                  {opportunity.product_name && (
                    <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
                      <Building2 className="w-4 h-4" />
                      <span className="line-clamp-1">{opportunity.product_name}</span>
                    </div>
                  )}

                  {/* Vendedor */}
                  {opportunity.seller_name && (
                    <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
                      <User className="w-4 h-4" />
                      <span>{opportunity.seller_name}</span>
                    </div>
                  )}

                  {/* Data */}
                  <div className="flex items-center gap-2 text-xs text-gray-500 mt-3 pt-3 border-t">
                    <Calendar className="w-3 h-3" />
                    <span>
                      Criado em {new Date(opportunity.created_at).toLocaleDateString('pt-BR')}
                    </span>
                  </div>

                  {/* Notas Preview */}
                  {opportunity.notes && (
                    <p className="text-xs text-gray-500 mt-2 line-clamp-2">
                      {opportunity.notes}
                    </p>
                  )}
                </Card>
              </div>
            );
          })
        )}
      </div>

      {/* Modal de Detalhes da Oportunidade */}
      <OpportunityModal
        opportunityId={selectedOpportunityId}
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setSelectedOpportunityId(null);
        }}
        onUpdate={loadData}
      />

      {/* Modal de Criar Nova Oportunidade */}
      <CreateOpportunityModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSuccess={loadData}
      />
    </div>
  );
}
