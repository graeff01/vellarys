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
  Loader2, Home, Bed, Bath, Maximize, Tag
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
    const configs: Record<string, { label: string; className: string; icon: any }> = {
      new: { label: 'Nova', className: 'bg-blue-100 text-blue-800', icon: Clock },
      in_progress: { label: 'Em Progresso', className: 'bg-yellow-100 text-yellow-800', icon: TrendingUp },
      won: { label: 'Fechada', className: 'bg-green-100 text-green-800', icon: CheckCircle2 },
      lost: { label: 'Perdida', className: 'bg-red-100 text-red-800', icon: XCircle },
    };
    return configs[status] || configs.new;
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
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
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
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl flex items-center gap-3">
            <Building2 className="w-7 h-7 text-purple-600" />
            {opportunity.title}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          {/* Status e Valor */}
          <div className="flex items-center justify-between">
            <Badge className={`${statusConfig.className} text-base px-3 py-1`}>
              <StatusIcon className="w-4 h-4 mr-2" />
              {statusConfig.label}
            </Badge>
            {opportunity.value > 0 && (
              <div className="flex items-center gap-2 text-2xl font-bold text-green-600">
                <DollarSign className="w-6 h-6" />
                {formatValue(opportunity.value)}
              </div>
            )}
          </div>

          {/* Informações do Lead */}
          <Card className="p-4 bg-blue-50 border-blue-200">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <User className="w-5 h-5 text-blue-600" />
              Informações do Lead
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-gray-600">Nome</p>
                <p className="font-medium">{opportunity.lead_name}</p>
              </div>
              {opportunity.lead_phone && (
                <div>
                  <p className="text-gray-600">Telefone</p>
                  <p className="font-medium flex items-center gap-1">
                    <Phone className="w-4 h-4 text-gray-500" />
                    {opportunity.lead_phone}
                  </p>
                </div>
              )}
              {opportunity.lead_email && (
                <div>
                  <p className="text-gray-600">Email</p>
                  <p className="font-medium flex items-center gap-1">
                    <Mail className="w-4 h-4 text-gray-500" />
                    {opportunity.lead_email}
                  </p>
                </div>
              )}
              {opportunity.lead_status && (
                <div>
                  <p className="text-gray-600">Status do Lead</p>
                  <Badge variant="outline">{opportunity.lead_status}</Badge>
                </div>
              )}
            </div>
          </Card>

          {/* Informações do Vendedor */}
          {opportunity.seller_name && (
            <Card className="p-4 bg-purple-50 border-purple-200">
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <User className="w-5 h-5 text-purple-600" />
                Vendedor Responsável
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-gray-600">Nome</p>
                  <p className="font-medium">{opportunity.seller_name}</p>
                </div>
                {opportunity.seller_phone && (
                  <div>
                    <p className="text-gray-600">Telefone</p>
                    <p className="font-medium flex items-center gap-1">
                      <Phone className="w-4 h-4 text-gray-500" />
                      {opportunity.seller_phone}
                    </p>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Informações do Imóvel/Produto */}
          {opportunity.product_data && (
            <Card className="p-4 bg-green-50 border-green-200">
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Home className="w-5 h-5 text-green-600" />
                Imóvel de Interesse
              </h3>
              
              {opportunity.product_data.codigo && (
                <div className="mb-3">
                  <Badge className="bg-green-600 text-white text-sm px-3 py-1">
                    Código: {opportunity.product_data.codigo}
                  </Badge>
                </div>
              )}

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
                {opportunity.product_data.tipo && (
                  <div className="flex items-center gap-2">
                    <Tag className="w-4 h-4 text-gray-500" />
                    <div>
                      <p className="text-gray-600 text-xs">Tipo</p>
                      <p className="font-medium">{opportunity.product_data.tipo}</p>
                    </div>
                  </div>
                )}
                {opportunity.product_data.regiao && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-gray-500" />
                    <div>
                      <p className="text-gray-600 text-xs">Região</p>
                      <p className="font-medium">{opportunity.product_data.regiao}</p>
                    </div>
                  </div>
                )}
                {opportunity.product_data.quartos && (
                  <div className="flex items-center gap-2">
                    <Bed className="w-4 h-4 text-gray-500" />
                    <div>
                      <p className="text-gray-600 text-xs">Quartos</p>
                      <p className="font-medium">{opportunity.product_data.quartos}</p>
                    </div>
                  </div>
                )}
                {opportunity.product_data.banheiros && (
                  <div className="flex items-center gap-2">
                    <Bath className="w-4 h-4 text-gray-500" />
                    <div>
                      <p className="text-gray-600 text-xs">Banheiros</p>
                      <p className="font-medium">{opportunity.product_data.banheiros}</p>
                    </div>
                  </div>
                )}
              </div>

              {opportunity.product_data.preco && (
                <div className="pt-3 border-t border-green-200">
                  <p className="text-gray-600 text-sm mb-1">Valor do Imóvel</p>
                  <p className="text-2xl font-bold text-green-700">
                    {formatValue(opportunity.product_data.preco)}
                  </p>
                </div>
              )}

              {opportunity.product_data.descricao && (
                <div className="mt-3 pt-3 border-t border-green-200">
                  <p className="text-gray-600 text-sm mb-1">Descrição</p>
                  <p className="text-sm text-gray-700">{opportunity.product_data.descricao}</p>
                </div>
              )}
            </Card>
          )}

          {/* Atualizar Status */}
          <Card className="p-4 bg-gray-50">
            <h3 className="font-semibold text-gray-900 mb-3">Atualizar Status da Oportunidade</h3>
            <div className="flex gap-3">
              <Select value={newStatus} onValueChange={setNewStatus}>
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder="Selecione o status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="new">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      Nova
                    </div>
                  </SelectItem>
                  <SelectItem value="in_progress">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="w-4 h-4" />
                      Em Progresso
                    </div>
                  </SelectItem>
                  <SelectItem value="won">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4" />
                      Fechada (Ganhou)
                    </div>
                  </SelectItem>
                  <SelectItem value="lost">
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
                    Atualizar
                  </>
                )}
              </Button>
            </div>
          </Card>

          {/* Datas */}
          <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
            <div>
              <p className="flex items-center gap-1 mb-1">
                <Calendar className="w-4 h-4" />
                Criada em:
              </p>
              <p className="font-medium text-gray-900">{formatDate(opportunity.created_at)}</p>
            </div>
            <div>
              <p className="flex items-center gap-1 mb-1">
                <Calendar className="w-4 h-4" />
                Atualizada em:
              </p>
              <p className="font-medium text-gray-900">{formatDate(opportunity.updated_at)}</p>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
