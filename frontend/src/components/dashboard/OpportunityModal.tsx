'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Building2, User, Phone, Mail, MapPin, DollarSign,
  Calendar, TrendingUp, CheckCircle2, XCircle, Clock,
  Loader2, Home, Bed, Bath, Tag, Sparkles, X, Car, Maximize2
} from 'lucide-react';
import { getToken } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';
import { VisuallyHidden } from '@radix-ui/react-visually-hidden';

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

  lead_id: number;
  lead_name: string;
  lead_phone?: string;
  lead_email?: string;
  lead_status?: string;

  seller_id?: number;
  seller_name?: string;
  seller_phone?: string;

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
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Erro ao carregar oportunidade');

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

      if (!response.ok) throw new Error('Erro ao atualizar status');

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
      novo: { label: 'Nova', color: 'bg-blue-500', icon: Sparkles },
      negociacao: { label: 'Em Negociação', color: 'bg-yellow-500', icon: TrendingUp },
      proposta: { label: 'Proposta Enviada', color: 'bg-purple-500', icon: TrendingUp },
      ganho: { label: 'Fechada', color: 'bg-green-500', icon: CheckCircle2 },
      perdido: { label: 'Perdida', color: 'bg-red-500', icon: XCircle },
    };
    return configs[status] || configs.novo;
  };

  const formatValue = (cents: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(cents / 100);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!opportunity && loading) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-7xl h-[85vh] p-0">
          <VisuallyHidden>
            <DialogTitle>Carregando oportunidade</DialogTitle>
            <DialogDescription>Aguarde enquanto carregamos os detalhes</DialogDescription>
          </VisuallyHidden>
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
      <DialogContent className="max-w-7xl h-[85vh] p-0 gap-0 overflow-hidden">
        <VisuallyHidden>
          <DialogTitle>{opportunity.title}</DialogTitle>
          <DialogDescription>Detalhes completos da oportunidade</DialogDescription>
        </VisuallyHidden>

        {/* Header */}
        <div className="bg-white border-b px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-4">
            <div className={`p-3 ${statusConfig.color} rounded-xl`}>
              <Building2 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">{opportunity.title}</h2>
              <div className="flex items-center gap-3 mt-1">
                <Badge className={`${statusConfig.color} text-white border-0`}>
                  <StatusIcon className="w-3 h-3 mr-1.5" />
                  {statusConfig.label}
                </Badge>
                {opportunity.value > 0 && (
                  <span className="text-lg font-bold text-green-600">
                    {formatValue(opportunity.value)}
                  </span>
                )}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content - 2 Columns */}
        <div className="flex-1 overflow-y-auto bg-gray-50">
          <div className="grid grid-cols-2 gap-6 p-6">
            {/* Left Column - Lead & Seller */}
            <div className="space-y-6">
              {/* Lead Card */}
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-center gap-3 mb-5">
                  <div className="p-2.5 bg-blue-50 rounded-lg">
                    <User className="w-5 h-5 text-blue-600" />
                  </div>
                  <h3 className="text-lg font-bold text-gray-900">Informações do Lead</h3>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Nome Completo</label>
                    <p className="mt-1 text-base font-semibold text-gray-900">{opportunity.lead_name}</p>
                  </div>

                  {opportunity.lead_phone && (
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Telefone</label>
                      <div className="mt-1 flex items-center gap-2">
                        <Phone className="w-4 h-4 text-blue-500" />
                        <p className="text-base font-medium text-gray-700">{opportunity.lead_phone}</p>
                      </div>
                    </div>
                  )}

                  {opportunity.lead_email && (
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Email</label>
                      <div className="mt-1 flex items-center gap-2">
                        <Mail className="w-4 h-4 text-blue-500" />
                        <p className="text-base font-medium text-gray-700">{opportunity.lead_email}</p>
                      </div>
                    </div>
                  )}

                  {opportunity.lead_status && (
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Status do Lead</label>
                      <Badge variant="outline" className="mt-1 font-medium capitalize">{opportunity.lead_status}</Badge>
                    </div>
                  )}
                </div>
              </div>

              {/* Seller Card */}
              {opportunity.seller_name && (
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <div className="flex items-center gap-3 mb-5">
                    <div className="p-2.5 bg-purple-50 rounded-lg">
                      <User className="w-5 h-5 text-purple-600" />
                    </div>
                    <h3 className="text-lg font-bold text-gray-900">Vendedor Responsável</h3>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Nome</label>
                      <p className="mt-1 text-base font-semibold text-gray-900">{opportunity.seller_name}</p>
                    </div>

                    {opportunity.seller_phone && (
                      <div>
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Telefone</label>
                        <div className="mt-1 flex items-center gap-2">
                          <Phone className="w-4 h-4 text-purple-500" />
                          <p className="text-base font-medium text-gray-700">{opportunity.seller_phone}</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Timeline Card */}
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-center gap-3 mb-5">
                  <div className="p-2.5 bg-gray-50 rounded-lg">
                    <Clock className="w-5 h-5 text-gray-600" />
                  </div>
                  <h3 className="text-lg font-bold text-gray-900">Timeline</h3>
                </div>

                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <Calendar className="w-4 h-4 text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-gray-500">Criada em</p>
                      <p className="text-sm font-medium text-gray-900">{formatDate(opportunity.created_at)}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <Calendar className="w-4 h-4 text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-gray-500">Última atualização</p>
                      <p className="text-sm font-medium text-gray-900">{formatDate(opportunity.updated_at)}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column - Property */}
            <div className="space-y-6">
              {opportunity.product_data ? (
                <>
                  {/* Property Header */}
                  <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white">
                    <div className="flex items-center gap-3 mb-4">
                      <Home className="w-7 h-7" />
                      <h3 className="text-2xl font-bold">Imóvel de Interesse</h3>
                    </div>
                    {opportunity.product_data.codigo && (
                      <div className="inline-block bg-white/20 backdrop-blur-sm px-4 py-2 rounded-lg">
                        <p className="text-sm font-medium">Código: <span className="font-bold">{opportunity.product_data.codigo}</span></p>
                      </div>
                    )}
                  </div>

                  {/* Property Details */}
                  <div className="bg-white rounded-xl border border-gray-200 p-6">
                    <div className="grid grid-cols-2 gap-4 mb-6">
                      {opportunity.product_data.tipo && (
                        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                          <Tag className="w-5 h-5 text-green-600" />
                          <div>
                            <p className="text-xs text-gray-500">Tipo</p>
                            <p className="font-semibold text-gray-900">{opportunity.product_data.tipo}</p>
                          </div>
                        </div>
                      )}
                      {opportunity.product_data.regiao && (
                        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                          <MapPin className="w-5 h-5 text-green-600" />
                          <div>
                            <p className="text-xs text-gray-500">Região</p>
                            <p className="font-semibold text-gray-900">{opportunity.product_data.regiao}</p>
                          </div>
                        </div>
                      )}
                      {opportunity.product_data.quartos && (
                        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                          <Bed className="w-5 h-5 text-green-600" />
                          <div>
                            <p className="text-xs text-gray-500">Quartos</p>
                            <p className="font-semibold text-gray-900">{opportunity.product_data.quartos}</p>
                          </div>
                        </div>
                      )}
                      {opportunity.product_data.banheiros && (
                        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                          <Bath className="w-5 h-5 text-green-600" />
                          <div>
                            <p className="text-xs text-gray-500">Banheiros</p>
                            <p className="font-semibold text-gray-900">{opportunity.product_data.banheiros}</p>
                          </div>
                        </div>
                      )}
                      {opportunity.product_data.vagas && (
                        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                          <Car className="w-5 h-5 text-green-600" />
                          <div>
                            <p className="text-xs text-gray-500">Vagas</p>
                            <p className="font-semibold text-gray-900">{opportunity.product_data.vagas}</p>
                          </div>
                        </div>
                      )}
                      {opportunity.product_data.metragem && (
                        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                          <Maximize2 className="w-5 h-5 text-green-600" />
                          <div>
                            <p className="text-xs text-gray-500">Área</p>
                            <p className="font-semibold text-gray-900">{opportunity.product_data.metragem}m²</p>
                          </div>
                        </div>
                      )}
                    </div>

                    {opportunity.product_data.preco && (
                      <div className="bg-gradient-to-br from-green-50 to-green-100 border-2 border-green-200 rounded-xl p-5 mb-6">
                        <div className="flex items-center gap-2 mb-2">
                          <DollarSign className="w-5 h-5 text-green-700" />
                          <p className="text-sm font-medium text-green-700">Valor do Imóvel</p>
                        </div>
                        <p className="text-3xl font-bold text-green-800">
                          {formatValue(opportunity.product_data.preco)}
                        </p>
                      </div>
                    )}

                    {opportunity.product_data.descricao && (
                      <div>
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">Descrição</label>
                        <p className="text-gray-700 leading-relaxed">{opportunity.product_data.descricao}</p>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center justify-center text-center">
                  <Building2 className="w-16 h-16 text-gray-300 mb-4" />
                  <p className="text-gray-500 font-medium">Nenhum imóvel vinculado a esta oportunidade</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer - Status Update */}
        <div className="bg-white border-t px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700">Atualizar Status:</label>
            <select
              value={newStatus}
              onChange={(e) => setNewStatus(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-medium"
            >
              <option value="novo">✨ Nova</option>
              <option value="negociacao">📈 Em Negociação</option>
              <option value="proposta">📋 Proposta Enviada</option>
              <option value="ganho">✅ Fechada (Ganhou)</option>
              <option value="perdido">❌ Perdida</option>
            </select>
          </div>
          <Button
            onClick={handleUpdateStatus}
            disabled={updating || newStatus === opportunity.status}
            size="lg"
            className="gap-2"
          >
            {updating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Atualizando...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Salvar Alterações
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
