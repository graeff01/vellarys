'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Building2, User, Phone, Mail, MapPin, DollarSign,
  Calendar, TrendingUp, CheckCircle2, XCircle, Clock,
  Loader2, Home, Bed, Bath, Maximize, Tag, Sparkles
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
    const configs: Record<string, { label: string; className: string; icon: any; bgGradient: string }> = {
      novo: {
        label: 'Nova',
        className: 'bg-blue-500 text-white border-0',
        icon: Sparkles,
        bgGradient: 'from-blue-500 to-blue-600'
      },
      negociacao: {
        label: 'Em Negociação',
        className: 'bg-yellow-500 text-white border-0',
        icon: TrendingUp,
        bgGradient: 'from-yellow-500 to-yellow-600'
      },
      proposta: {
        label: 'Proposta Enviada',
        className: 'bg-purple-500 text-white border-0',
        icon: TrendingUp,
        bgGradient: 'from-purple-500 to-purple-600'
      },
      ganho: {
        label: 'Fechada',
        className: 'bg-green-500 text-white border-0',
        icon: CheckCircle2,
        bgGradient: 'from-green-500 to-green-600'
      },
      perdido: {
        label: 'Perdida',
        className: 'bg-red-500 text-white border-0',
        icon: XCircle,
        bgGradient: 'from-red-500 to-red-600'
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
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-center py-12">
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
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        {/* Header com Gradiente */}
        <div className={`-mx-6 -mt-6 px-6 py-6 bg-gradient-to-r ${statusConfig.bgGradient} rounded-t-lg`}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <Building2 className="w-8 h-8 text-white" />
                <h2 className="text-2xl font-bold text-white">{opportunity.title}</h2>
              </div>
              <Badge className="bg-white/20 text-white border-white/30 backdrop-blur-sm">
                <StatusIcon className="w-4 h-4 mr-2" />
                {statusConfig.label}
              </Badge>
            </div>
            {opportunity.value > 0 && (
              <div className="text-right">
                <p className="text-white/80 text-sm mb-1">Valor</p>
                <p className="text-3xl font-bold text-white">
                  {formatValue(opportunity.value)}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6 mt-6">
          {/* Grid de Informações */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Informações do Lead */}
            <Card className="p-5 border-2 border-blue-100 bg-gradient-to-br from-blue-50 to-white">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-blue-500 rounded-lg">
                  <User className="w-5 h-5 text-white" />
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
            </Card>

            {/* Informações do Vendedor */}
            {opportunity.seller_name && (
              <Card className="p-5 border-2 border-purple-100 bg-gradient-to-br from-purple-50 to-white">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-purple-500 rounded-lg">
                    <User className="w-5 h-5 text-white" />
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
              </Card>
            )}
          </div>

          {/* Informações do Imóvel */}
          {opportunity.product_data && (
            <Card className="p-6 border-2 border-green-100 bg-gradient-to-br from-green-50 to-white">
              <div className="flex items-center gap-3 mb-5">
                <div className="p-2 bg-green-500 rounded-lg">
                  <Home className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-bold text-gray-900 text-xl">Imóvel de Interesse</h3>
              </div>

              {opportunity.product_data.codigo && (
                <div className="mb-4">
                  <Badge className="bg-green-500 text-white text-base px-4 py-1.5 border-0">
                    Código: {opportunity.product_data.codigo}
                  </Badge>
                </div>
              )}

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
                {opportunity.product_data.tipo && (
                  <div className="flex items-start gap-3">
                    <Tag className="w-5 h-5 text-green-600 mt-1" />
                    <div>
                      <p className="text-xs text-gray-500">Tipo</p>
                      <p className="font-semibold text-gray-900">{opportunity.product_data.tipo}</p>
                    </div>
                  </div>
                )}
                {opportunity.product_data.regiao && (
                  <div className="flex items-start gap-3">
                    <MapPin className="w-5 h-5 text-green-600 mt-1" />
                    <div>
                      <p className="text-xs text-gray-500">Região</p>
                      <p className="font-semibold text-gray-900">{opportunity.product_data.regiao}</p>
                    </div>
                  </div>
                )}
                {opportunity.product_data.quartos && (
                  <div className="flex items-start gap-3">
                    <Bed className="w-5 h-5 text-green-600 mt-1" />
                    <div>
                      <p className="text-xs text-gray-500">Quartos</p>
                      <p className="font-semibold text-gray-900">{opportunity.product_data.quartos}</p>
                    </div>
                  </div>
                )}
                {opportunity.product_data.banheiros && (
                  <div className="flex items-start gap-3">
                    <Bath className="w-5 h-5 text-green-600 mt-1" />
                    <div>
                      <p className="text-xs text-gray-500">Banheiros</p>
                      <p className="font-semibold text-gray-900">{opportunity.product_data.banheiros}</p>
                    </div>
                  </div>
                )}
              </div>

              {opportunity.product_data.preco && (
                <div className="pt-4 border-t-2 border-green-200 mb-4">
                  <p className="text-sm text-gray-600 mb-2">Valor do Imóvel</p>
                  <p className="text-3xl font-bold text-green-700">
                    {formatValue(opportunity.product_data.preco)}
                  </p>
                </div>
              )}

              {opportunity.product_data.descricao && (
                <div className="pt-4 border-t border-green-200">
                  <p className="text-sm text-gray-600 mb-2">Descrição</p>
                  <p className="text-gray-700 leading-relaxed">{opportunity.product_data.descricao}</p>
                </div>
              )}
            </Card>
          )}

          {/* Atualizar Status */}
          <Card className="p-5 bg-gray-50 border-2">
            <h3 className="font-bold text-gray-900 mb-4 text-lg">Atualizar Status</h3>
            <div className="flex gap-3">
              <Select value={newStatus} onValueChange={setNewStatus}>
                <SelectTrigger className="flex-1 h-11">
                  <SelectValue placeholder="Selecione o status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="novo">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4" />
                      Nova
                    </div>
                  </SelectItem>
                  <SelectItem value="negociacao">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="w-4 h-4" />
                      Em Negociação
                    </div>
                  </SelectItem>
                  <SelectItem value="proposta">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="w-4 h-4" />
                      Proposta Enviada
                    </div>
                  </SelectItem>
                  <SelectItem value="ganho">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4" />
                      Fechada (Ganhou)
                    </div>
                  </SelectItem>
                  <SelectItem value="perdido">
                    <div className="flex items-center gap-2">
                      <XCircle className="w-4 h-4" />
                      Perdida
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
              <Button
                onClick={handleUpdateStatus}
                disabled={updating || newStatus === opportunity.status}
                className="gap-2 h-11 px-6"
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
          </Card>

          {/* Datas */}
          <div className="grid grid-cols-2 gap-4 pt-4 border-t">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Calendar className="w-4 h-4" />
              <div>
                <p className="text-xs text-gray-500">Criada em</p>
                <p className="font-medium text-gray-900">{formatDate(opportunity.created_at)}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Calendar className="w-4 h-4" />
              <div>
                <p className="text-xs text-gray-500">Atualizada em</p>
                <p className="font-medium text-gray-900">{formatDate(opportunity.updated_at)}</p>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
