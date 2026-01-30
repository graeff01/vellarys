'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Building2, User, Phone, Mail, MapPin, DollarSign,
  Calendar, TrendingUp, CheckCircle2, XCircle, Clock,
  Loader2, Home, Bed, Bath, Tag, Sparkles, X
} from 'lucide-react';
import { getToken } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

interface OpportunityModalProps {
  opportunityId: number | null;
  open: boolean;
  onClose: () => void;
  onUpdate: () => void;
}

interface OpportunityDetails {
  id: number;
  title: string;
  status: string;
  value: number;
  created_at: string;
  updated_at: string;

  // Lead
  lead_id: number;
  lead_name: string;
  lead_phone?: string;
  lead_email?: string;
  lead_status?: string;

  // Seller
  seller_id?: number;
  seller_name?: string;
  seller_phone?: string;

  // Product/Imóvel
  product_id?: number;
  product_name?: string;
  product_data?: {
    codigo?: string;
    tipo?: string;
    regiao?: string;
    preco?: number;
    quartos?: number;
    banheiros?: number;
    vagas?: number;
    metragem?: number;
    descricao?: string;
  };
}

export function OpportunityModal({ opportunityId, open, onClose, onUpdate }: OpportunityModalProps) {
  const [opportunity, setOpportunity] = useState<OpportunityDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [newStatus, setNewStatus] = useState<string>('');
  const { toast } = useToast();

  useEffect(() => {
    if (open && opportunityId) {
      loadOpportunity();
    }
  }, [open, opportunityId]);

  async function loadOpportunity() {
    if (!opportunityId) return;

    try {
      setLoading(true);
      const token = getToken();
      const response = await fetch(`${API_URL}/v1/opportunities/${opportunityId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Erro ao carregar oportunidade');
      }

      const data = await response.json();
      setOpportunity(data);
      setNewStatus(data.status);
    } catch (error) {
      console.error('Erro ao carregar oportunidade:', error);
      toast({
        variant: 'destructive',
        title: 'Erro ao carregar detalhes',
        description: 'Tente novamente'
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleUpdateStatus() {
    if (!opportunityId || !newStatus) return;

    try {
      setUpdating(true);
      const token = getToken();
      const response = await fetch(`${API_URL}/v1/opportunities/${opportunityId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (!response.ok) {
        throw new Error('Erro ao atualizar status');
      }

      toast({
        title: 'Status atualizado!',
        description: 'A oportunidade foi atualizada com sucesso'
      });

      onUpdate();
      loadOpportunity();
    } catch (error) {
      console.error('Erro ao atualizar status:', error);
      toast({
        variant: 'destructive',
        title: 'Erro ao atualizar',
        description: 'Tente novamente'
      });
    } finally {
      setUpdating(false);
    }
  }

  const getStatusConfig = (status: string) => {
    const configs: Record<string, { label: string; color: string; icon: any }> = {
      novo: {
        label: 'Nova',
        color: 'blue',
        icon: Sparkles
      },
      negociacao: {
        label: 'Em Negociação',
        color: 'yellow',
        icon: TrendingUp
      },
      proposta: {
        label: 'Proposta Enviada',
        color: 'purple',
        icon: TrendingUp
      },
      ganho: {
        label: 'Fechada',
        color: 'green',
        icon: CheckCircle2
      },
      perdido: {
        label: 'Perdida',
        color: 'red',
        icon: XCircle
      },
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!opportunity && loading) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-6xl h-[90vh] p-0">
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  if (!opportunity) return null;

  const statusConfig = getStatusConfig(opportunity.status);
  const StatusIcon = statusConfig.icon;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl h-[90vh] p-0 gap-0">
        {/* Header Fixo */}
        <div className="bg-gradient-to-r from-gray-900 to-gray-800 px-8 py-6 flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-3">
              <Building2 className="w-7 h-7 text-white" />
              <h2 className="text-2xl font-bold text-white">{opportunity.title}</h2>
            </div>
            <div className="flex items-center gap-3">
              <Badge className={`bg-${statusConfig.color}-500 text-white border-0 px-3 py-1`}>
                <StatusIcon className="w-4 h-4 mr-2" />
                {statusConfig.label}
              </Badge>
              {opportunity.value > 0 && (
                <span className="text-2xl font-bold text-green-400">
                  {formatValue(opportunity.value)}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white/70 hover:text-white transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Conteúdo - Grid 3 Colunas SEM SCROLL */}
        <div className="grid grid-cols-3 gap-6 p-8 h-[calc(90vh-140px)]">
          {/* Coluna 1: Lead */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-2 bg-blue-100 rounded-lg">
                <User className="w-5 h-5 text-blue-600" />
              </div>
              <h3 className="font-bold text-gray-900 text-lg">Lead</h3>
            </div>

            <div className="space-y-3">
              <div>
                <p className="text-xs text-gray-500 mb-1">Nome</p>
                <p className="font-semibold text-gray-900">{opportunity.lead_name}</p>
              </div>
              {opportunity.lead_phone && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Telefone</p>
                  <p className="font-medium text-gray-700 flex items-center gap-2">
                    <Phone className="w-4 h-4 text-blue-500" />
                    {opportunity.lead_phone}
                  </p>
                </div>
              )}
              {opportunity.lead_email && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Email</p>
                  <p className="font-medium text-gray-700 flex items-center gap-2">
                    <Mail className="w-4 h-4 text-blue-500" />
                    {opportunity.lead_email}
                  </p>
                </div>
              )}
              {opportunity.lead_status && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Status</p>
                  <Badge variant="outline" className="font-medium">{opportunity.lead_status}</Badge>
                </div>
              )}
            </div>

            {/* Vendedor */}
            {opportunity.seller_name && (
              <>
                <div className="border-t pt-4 mt-4">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <User className="w-5 h-5 text-purple-600" />
                    </div>
                    <h3 className="font-bold text-gray-900 text-lg">Vendedor</h3>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Nome</p>
                      <p className="font-semibold text-gray-900">{opportunity.seller_name}</p>
                    </div>
                    {opportunity.seller_phone && (
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Telefone</p>
                        <p className="font-medium text-gray-700 flex items-center gap-2">
                          <Phone className="w-4 h-4 text-purple-500" />
                          {opportunity.seller_phone}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}

            {/* Datas */}
            <div className="border-t pt-4 mt-4 space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="w-4 h-4 text-gray-400" />
                <div>
                  <p className="text-xs text-gray-500">Criada em</p>
                  <p className="font-medium text-gray-700">{formatDate(opportunity.created_at)}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="w-4 h-4 text-gray-400" />
                <div>
                  <p className="text-xs text-gray-500">Atualizada em</p>
                  <p className="font-medium text-gray-700">{formatDate(opportunity.updated_at)}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Coluna 2: Imóvel */}
          <div className="col-span-2 space-y-4">
            {opportunity.product_data ? (
              <>
                <div className="flex items-center gap-2 mb-4">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <Home className="w-6 h-6 text-green-600" />
                  </div>
                  <h3 className="font-bold text-gray-900 text-xl">Imóvel de Interesse</h3>
                </div>

                {opportunity.product_data.codigo && (
                  <div className="mb-4">
                    <Badge className="bg-green-600 text-white text-base px-4 py-1.5 border-0">
                      Código: {opportunity.product_data.codigo}
                    </Badge>
                  </div>
                )}

                <div className="grid grid-cols-4 gap-4 mb-5">
                  {opportunity.product_data.tipo && (
                    <div className="flex items-start gap-2">
                      <Tag className="w-5 h-5 text-green-600 mt-0.5" />
                      <div>
                        <p className="text-xs text-gray-500">Tipo</p>
                        <p className="font-semibold text-gray-900">{opportunity.product_data.tipo}</p>
                      </div>
                    </div>
                  )}
                  {opportunity.product_data.regiao && (
                    <div className="flex items-start gap-2">
                      <MapPin className="w-5 h-5 text-green-600 mt-0.5" />
                      <div>
                        <p className="text-xs text-gray-500">Região</p>
                        <p className="font-semibold text-gray-900">{opportunity.product_data.regiao}</p>
                      </div>
                    </div>
                  )}
                  {opportunity.product_data.quartos && (
                    <div className="flex items-start gap-2">
                      <Bed className="w-5 h-5 text-green-600 mt-0.5" />
                      <div>
                        <p className="text-xs text-gray-500">Quartos</p>
                        <p className="font-semibold text-gray-900">{opportunity.product_data.quartos}</p>
                      </div>
                    </div>
                  )}
                  {opportunity.product_data.banheiros && (
                    <div className="flex items-start gap-2">
                      <Bath className="w-5 h-5 text-green-600 mt-0.5" />
                      <div>
                        <p className="text-xs text-gray-500">Banheiros</p>
                        <p className="font-semibold text-gray-900">{opportunity.product_data.banheiros}</p>
                      </div>
                    </div>
                  )}
                </div>

                {opportunity.product_data.preco && (
                  <div className="bg-green-50 border-2 border-green-200 rounded-lg p-4 mb-4">
                    <p className="text-sm text-gray-600 mb-2">Valor do Imóvel</p>
                    <p className="text-3xl font-bold text-green-700">
                      {formatValue(opportunity.product_data.preco)}
                    </p>
                  </div>
                )}

                {opportunity.product_data.descricao && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm font-semibold text-gray-700 mb-2">Descrição</p>
                    <p className="text-gray-600 leading-relaxed">{opportunity.product_data.descricao}</p>
                  </div>
                )}

                {/* Atualizar Status */}
                <div className="bg-gray-50 border-2 border-gray-200 rounded-lg p-5 mt-6">
                  <h3 className="font-bold text-gray-900 mb-4 text-lg">Atualizar Status</h3>
                  <div className="flex gap-3">
                    <select
                      value={newStatus}
                      onChange={(e) => setNewStatus(e.target.value)}
                      className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="novo">✨ Nova</option>
                      <option value="negociacao">📈 Em Negociação</option>
                      <option value="proposta">📋 Proposta Enviada</option>
                      <option value="ganho">✅ Fechada (Ganhou)</option>
                      <option value="perdido">❌ Perdida</option>
                    </select>
                    <Button
                      onClick={handleUpdateStatus}
                      disabled={updating || newStatus === opportunity.status}
                      className="gap-2 px-6"
                    >
                      {updating ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Atualizando...
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4" />
                          Atualizar
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                  <Building2 className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>Nenhum imóvel vinculado</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
