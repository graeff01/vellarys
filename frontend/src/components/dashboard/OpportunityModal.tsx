'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Building2, User, Phone, Mail, MapPin, DollarSign,
  Calendar, TrendingUp, CheckCircle2, XCircle, Clock,
  Loader2, Home, Bed, Bath, Tag, Sparkles, X, Car, Maximize2,
  ChevronRight, Info, AlertCircle
} from 'lucide-react';
import { getToken } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

// Componente local para acessibilidade
const VisuallyHidden = ({ children }: { children: React.ReactNode }) => (
  <span className="sr-only">{children}</span>
);

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
      novo: { label: 'Nova Oportunidade', color: 'text-blue-600 bg-blue-50 border-blue-200', icon: Sparkles },
      negociacao: { label: 'Em Negociação', color: 'text-yellow-600 bg-yellow-50 border-yellow-200', icon: TrendingUp },
      proposta: { label: 'Proposta Enviada', color: 'text-purple-600 bg-purple-50 border-purple-200', icon: Calendar },
      ganho: { label: 'Negócio Fechado', color: 'text-green-600 bg-green-50 border-green-200', icon: CheckCircle2 },
      perdido: { label: 'Negócio Perdido', color: 'text-red-600 bg-red-50 border-red-200', icon: XCircle },
    };
    return configs[status] || configs.novo;
  };

  const formatValue = (cents: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(cents / 100);
  };

  const formatDateShort = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit'
    });
  };

  if (!opportunity && loading) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="w-[95vw] max-w-6xl h-[90vh] p-0 flex items-center justify-center bg-white rounded-3xl overflow-hidden border-none shadow-2xl">
          <VisuallyHidden>
            <DialogTitle>Carregando oportunidade</DialogTitle>
            <DialogDescription>Aguarde enquanto carregamos os detalhes</DialogDescription>
          </VisuallyHidden>
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-10 h-10 animate-spin text-blue-600" />
            <p className="text-gray-400 font-medium">Sincronizando dados...</p>
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
      <DialogContent className="w-[95vw] max-w-6xl h-[90vh] p-0 gap-0 overflow-hidden bg-white flex flex-col border-none shadow-2xl rounded-3xl">
        <VisuallyHidden>
          <DialogTitle>{opportunity.title}</DialogTitle>
          <DialogDescription>Detalhes completos da oportunidade e gestão de status</DialogDescription>
        </VisuallyHidden>

        {/* --- HEADER --- */}
        <div className="bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-2xl ${statusConfig.color.split(' ')[1]} border ${statusConfig.color.split(' ')[2]}`}>
              <Building2 className={`w-6 h-6 ${statusConfig.color.split(' ')[0]}`} />
            </div>
            <div>
              <div className="flex items-center gap-3 mb-0.5">
                <h2 className="text-xl font-black text-gray-900 leading-none">{opportunity.title}</h2>
                <Badge variant="outline" className={`${statusConfig.color} border px-2 py-0.5 rounded-full font-bold flex items-center gap-1.5 text-[10px]`}>
                  <StatusIcon className="w-3 h-3" />
                  {statusConfig.label.toUpperCase()}
                </Badge>
              </div>
              <div className="flex items-center gap-2 text-[10px] text-gray-400 font-bold uppercase tracking-wider">
                <span>Criada {formatDateShort(opportunity.created_at)}</span>
                <span className="w-1 h-1 bg-gray-200 rounded-full" />
                <span className="text-blue-500 font-black">ID #{opportunity.id}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {opportunity.value > 0 && (
              <div className="text-right mr-4">
                <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest leading-none mb-1">Valor Estimado</p>
                <p className="text-xl font-black text-green-600 leading-none">
                  {formatValue(opportunity.value)}
                </p>
              </div>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-all active:scale-95 bg-gray-50 text-gray-400"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* --- MAIN CONTENT AREA --- */}
        <div className="flex-1 overflow-hidden grid grid-cols-1 md:grid-cols-12 bg-gray-50/30">

          {/* Main Info & Property (8 columns) */}
          <div className="md:col-span-8 overflow-y-auto p-6 space-y-6 border-r border-gray-100 bg-white">

            {/* Property Section */}
            <section className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                  <Home className="w-4 h-4 text-blue-600" />
                  Imóvel de Interesse
                </h3>
                {opportunity.product_data?.codigo && (
                  <Badge className="bg-blue-600 text-white hover:bg-blue-700 border-none px-3 py-1 rounded-lg text-xs font-black tracking-wider">
                    REF: {opportunity.product_data.codigo}
                  </Badge>
                )}
              </div>

              {opportunity.product_data ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                      <span className="text-[9px] font-black text-gray-400 uppercase block mb-1">Tipo</span>
                      <p className="text-sm font-bold text-gray-900 truncate">{opportunity.product_data.tipo || '-'}</p>
                    </div>
                    <div className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                      <span className="text-[9px] font-black text-gray-400 uppercase block mb-1">Região</span>
                      <p className="text-sm font-bold text-gray-900 truncate">{opportunity.product_data.regiao || '-'}</p>
                    </div>
                    <div className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                      <span className="text-[9px] font-black text-gray-400 uppercase block mb-1">Quartos</span>
                      <p className="text-sm font-bold text-gray-900 truncate">{opportunity.product_data.quartos || '-'}</p>
                    </div>
                    <div className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                      <span className="text-[9px] font-black text-gray-400 uppercase block mb-1">Área</span>
                      <p className="text-sm font-bold text-gray-900 truncate">{opportunity.product_data.metragem ? `${opportunity.product_data.metragem}m²` : '-'}</p>
                    </div>
                  </div>

                  {opportunity.product_data.preco && (
                    <div className="bg-green-50/50 border border-green-100 rounded-3xl p-5 flex items-center justify-between shadow-sm">
                      <div>
                        <span className="text-[9px] font-black text-green-600 uppercase tracking-widest block mb-1">Valor de Tabela</span>
                        <p className="text-2xl font-black text-green-700 leading-none">
                          {formatValue(opportunity.product_data.preco)}
                        </p>
                      </div>
                      <Badge className="bg-green-100 text-green-700 border-green-200 px-3 py-1 font-bold text-[10px]">PREÇO SUGERIDO</Badge>
                    </div>
                  )}

                  <div className="p-5 bg-gray-50 border border-gray-100 rounded-3xl">
                    <span className="text-[9px] font-black text-gray-400 uppercase tracking-widest block mb-3">Descrição Detalhada</span>
                    <p className="text-gray-600 text-sm leading-relaxed">
                      {opportunity.product_data.descricao || "Sem descrição disponível."}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-10 border-2 border-dashed border-gray-100 rounded-3xl flex flex-col items-center justify-center text-center">
                  <Building2 className="w-10 h-10 text-gray-200 mb-3" />
                  <p className="text-gray-400 text-xs font-bold">Sem imóvel vinculado</p>
                </div>
              )}
            </section>

            {/* Notes Section */}
            <section className="space-y-3">
              <h3 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                Observações da Negociação
              </h3>
              <div className="p-5 bg-yellow-50/30 border border-yellow-100 rounded-3xl">
                <p className="text-gray-700 text-sm italic font-medium">
                  {opportunity.notes || "Nenhuma nota adicionada."}
                </p>
              </div>
            </section>
          </div>

          {/* Sidebar Area (4 columns) */}
          <div className="md:col-span-4 p-6 space-y-6 overflow-y-auto">

            {/* Lead & Contact */}
            <div className="bg-white rounded-3xl p-5 border border-gray-100 shadow-sm space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-blue-100 flex items-center justify-center font-black text-blue-600 shadow-sm">
                  {opportunity.lead_name.charAt(0)}
                </div>
                <div>
                  <p className="text-[9px] font-black text-gray-400 uppercase leading-none mb-1">Lead</p>
                  <p className="text-sm font-black text-gray-900 leading-none">{opportunity.lead_name}</p>
                </div>
              </div>

              <div className="space-y-2 pt-2 border-t border-gray-50">
                <div className="flex items-center gap-2 text-xs font-bold text-gray-600">
                  <Phone className="w-3.5 h-3.5 text-blue-500" />
                  {opportunity.lead_phone || 'S/ Tel'}
                </div>
                <div className="flex items-center gap-2 text-xs font-bold text-gray-600 truncate">
                  <Mail className="w-3.5 h-3.5 text-blue-500 truncate" />
                  <span className="truncate">{opportunity.lead_email || 'S/ Email'}</span>
                </div>
              </div>
            </div>

            {/* Seller */}
            {opportunity.seller_name ? (
              <div className="bg-white rounded-3xl p-5 border border-gray-100 shadow-sm">
                <p className="text-[9px] font-black text-gray-400 uppercase mb-3">Responsável</p>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-orange-100 border-2 border-white flex items-center justify-center text-orange-600 font-bold text-xs ring-1 ring-orange-50">
                    {opportunity.seller_name.charAt(0)}
                  </div>
                  <p className="text-xs font-bold text-gray-800">{opportunity.seller_name}</p>
                </div>
              </div>
            ) : null}

            {/* Timeline */}
            <div className="space-y-3 px-2">
              <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Atividade</h4>
              <div className="space-y-4 pl-1">
                <div className="flex gap-3 relative">
                  <div className="w-px bg-gray-100 absolute left-[7px] top-4 bottom-0" />
                  <div className="w-3.5 h-3.5 rounded-full bg-blue-500 border-2 border-white shadow-sm flex-shrink-0 z-10" />
                  <div>
                    <p className="text-xs font-bold text-gray-800">Criada</p>
                    <p className="text-[10px] text-gray-400">{formatDateShort(opportunity.created_at)}</p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-3.5 h-3.5 rounded-full bg-green-500 border-2 border-white shadow-sm flex-shrink-0 z-10" />
                  <div>
                    <p className="text-xs font-bold text-gray-800">Última Atualização</p>
                    <p className="text-[10px] text-gray-400">{formatDateShort(opportunity.updated_at)}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* --- FOOTER: ACTION BAR --- */}
        <div className="bg-white border-t border-gray-100 px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-4 flex-shrink-0">
          <div className="flex items-center gap-3 bg-gray-50 px-4 py-2 rounded-2xl border border-gray-100 w-full sm:w-auto">
            <label className="text-[10px] font-black text-gray-400 uppercase tracking-tighter">Status:</label>
            <select
              value={newStatus}
              onChange={(e) => setNewStatus(e.target.value)}
              className="bg-transparent border-none focus:ring-0 font-bold text-sm text-gray-700 cursor-pointer outline-none"
            >
              <option value="novo">🚀 Nova Oportunidade</option>
              <option value="negociacao">🤝 Em Negociação</option>
              <option value="proposta">📄 Proposta Enviada</option>
              <option value="ganho">🏆 Negócio Fechado (Venda!)</option>
              <option value="perdido">❌ Negócio Perdido</option>
            </select>
          </div>

          <Button
            onClick={handleUpdateStatus}
            disabled={updating || newStatus === opportunity.status}
            className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white font-black rounded-2xl px-10 h-12 shadow-lg shadow-blue-100 transition-all active:scale-95 disabled:grayscale"
          >
            {updating ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              "Confirmar Atualização"
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
