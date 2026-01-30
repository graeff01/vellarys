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

// Componente local para acessibilidade sem dep externas
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
    const configs: Record<string, { label: string; color: string; icon: any; variant: "default" | "secondary" | "outline" | "destructive" }> = {
      novo: { label: 'Nova Oportunidade', color: 'text-blue-600 bg-blue-50 border-blue-200', icon: Sparkles, variant: "default" },
      negociacao: { label: 'Em Negociação', color: 'text-yellow-600 bg-yellow-50 border-yellow-200', icon: TrendingUp, variant: "secondary" },
      proposta: { label: 'Proposta Enviada', color: 'text-purple-600 bg-purple-50 border-purple-200', icon: Calendar, variant: "outline" },
      ganho: { label: 'Negócio Fechado', color: 'text-green-600 bg-green-50 border-green-200', icon: CheckCircle2, variant: "default" },
      perdido: { label: 'Negócio Perdido', color: 'text-red-600 bg-red-50 border-red-200', icon: XCircle, variant: "destructive" },
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
        <DialogContent className="max-w-7xl h-[85vh] p-0 flex items-center justify-center bg-white">
          <VisuallyHidden>
            <DialogTitle>Carregando oportunidade</DialogTitle>
            <DialogDescription>Aguarde enquanto carregamos os detalhes</DialogDescription>
          </VisuallyHidden>
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-10 h-10 animate-spin text-blue-600" />
            <p className="text-gray-500 font-medium">Carregando dados da oportunidade...</p>
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
      <DialogContent className="max-w-6xl h-[90vh] p-0 gap-0 overflow-hidden bg-gray-50/50 flex flex-col border-none shadow-2xl">
        <VisuallyHidden>
          <DialogTitle>{opportunity.title}</DialogTitle>
          <DialogDescription>Detalhes completos da oportunidade e gestão de status</DialogDescription>
        </VisuallyHidden>

        {/* --- HEADER --- */}
        <div className="bg-white border-b border-gray-100 px-8 py-5 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-5">
            <div className={`p-4 rounded-2xl ${statusConfig.color.split(' ')[1]} border ${statusConfig.color.split(' ')[2]}`}>
              <Building2 className={`w-7 h-7 ${statusConfig.color.split(' ')[0]}`} />
            </div>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h2 className="text-2xl font-extrabold text-gray-900 tracking-tight">{opportunity.title}</h2>
                <Badge variant="outline" className={`${statusConfig.color} border py-1 px-3 rounded-full font-bold flex items-center gap-2 text-xs`}>
                  <StatusIcon className="w-3.5 h-3.5" />
                  {statusConfig.label}
                </Badge>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-500 font-medium">
                <span className="flex items-center gap-1.5">
                  <Calendar className="w-4 h-4" />
                  Criada em {formatDateShort(opportunity.created_at)}
                </span>
                <span className="w-1 h-1 bg-gray-300 rounded-full" />
                <span className="flex items-center gap-1.5 text-blue-600 font-bold">
                  ID #{opportunity.id}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {opportunity.value > 0 && (
              <div className="text-right">
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-0.5">Valor Estimado</p>
                <p className="text-2xl font-black text-green-600">
                  {formatValue(opportunity.value)}
                </p>
              </div>
            )}
            <div className="h-10 w-px bg-gray-100 mx-2" />
            <button
              onClick={onClose}
              className="p-2.5 hover:bg-gray-100 rounded-full transition-all active:scale-95 bg-gray-50"
            >
              <X className="w-6 h-6 text-gray-400" />
            </button>
          </div>
        </div>

        {/* --- MAIN CONTENT AREA --- */}
        <div className="flex-1 overflow-hidden flex">

          {/* LEFT SIDE: Main Info & Property (70%) */}
          <div className="flex-[0_0_68%] overflow-y-auto p-8 space-y-8 border-r border-gray-100">

            {/* Seção Imóvel */}
            <section className="space-y-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                    <Home className="w-5 h-5 text-blue-600" />
                    Detalhes do Imóvel de Interesse
                  </h3>
                </div>
                {opportunity.product_data?.codigo && (
                  <Badge className="bg-gray-900 text-white hover:bg-gray-800 border-none px-4 py-1.5 rounded-lg text-sm font-bold">
                    Ref: {opportunity.product_data.codigo}
                  </Badge>
                )}
              </div>

              {opportunity.product_data ? (
                <div className="grid grid-cols-1 gap-6">
                  {/* Grid de Características Premium */}
                  <div className="grid grid-cols-4 gap-4">
                    <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm hover:border-blue-200 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <Tag className="w-4 h-4 text-blue-500" />
                        <span className="text-[10px] font-bold text-gray-400 uppercase">Tipo</span>
                      </div>
                      <p className="text-sm font-bold text-gray-900 truncate">{opportunity.product_data.tipo || '-'}</p>
                    </div>
                    <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm hover:border-blue-200 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <MapPin className="w-4 h-4 text-blue-500" />
                        <span className="text-[10px] font-bold text-gray-400 uppercase">Região</span>
                      </div>
                      <p className="text-sm font-bold text-gray-900 truncate">{opportunity.product_data.regiao || '-'}</p>
                    </div>
                    <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm hover:border-blue-200 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <Bed className="w-4 h-4 text-blue-500" />
                        <span className="text-[10px] font-bold text-gray-400 uppercase">Quartos</span>
                      </div>
                      <p className="text-sm font-bold text-gray-900 truncate">{opportunity.product_data.quartos || '-'}</p>
                    </div>
                    <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm hover:border-blue-200 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <Maximize2 className="w-4 h-4 text-blue-500" />
                        <span className="text-[10px] font-bold text-gray-400 uppercase">Área</span>
                      </div>
                      <p className="text-sm font-bold text-gray-900 truncate">{opportunity.product_data.metragem ? `${opportunity.product_data.metragem}m²` : '-'}</p>
                    </div>
                  </div>

                  {/* Valor Card */}
                  {opportunity.product_data.preco && (
                    <div className="bg-gradient-to-br from-green-50 to-green-100/50 border border-green-200 rounded-3xl p-6 flex items-center justify-between shadow-sm">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <DollarSign className="w-5 h-5 text-green-600" />
                          <p className="text-xs font-bold text-green-700 uppercase tracking-widest">Valor do Imóvel</p>
                        </div>
                        <p className="text-3xl font-black text-green-800 tracking-tight">
                          {formatValue(opportunity.product_data.preco)}
                        </p>
                      </div>
                      <div className="bg-white px-5 py-3 rounded-2xl border border-green-200/50 shadow-sm">
                        <div className="flex flex-col items-center">
                          <span className="text-[10px] font-bold text-green-600 uppercase">Comissão est.</span>
                          <span className="text-lg font-black text-green-700">6%</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Descrição */}
                  <div className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm">
                    <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                      <Info className="w-3.5 h-3.5" />
                      Descrição Completa
                    </p>
                    <p className="text-gray-700 leading-relaxed text-sm whitespace-pre-wrap">
                      {opportunity.product_data.descricao || "Nenhuma descrição detalhada disponível para este imóvel no momento."}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-12 border-2 border-dashed border-gray-200 rounded-3xl flex flex-col items-center justify-center text-center bg-white/50">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                    <Building2 className="w-8 h-8 text-gray-300" />
                  </div>
                  <h4 className="text-gray-900 font-bold text-lg mb-1">Sem Imóvel Vinculado</h4>
                  <p className="text-gray-500 text-sm max-w-xs">Esta oportunidade ainda não tem um imóvel específico cadastrado.</p>
                </div>
              )}
            </section>

            {/* Observações da Oportunidade */}
            <section className="space-y-4">
              <h3 className="text-sm font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2">
                Notas do Gestor
              </h3>
              <div className="p-6 bg-yellow-50/50 border border-yellow-100 rounded-3xl">
                <p className="text-gray-700 text-sm italic">
                  {opportunity.notes || "Nenhuma observação interna adicionada."}
                </p>
              </div>
            </section>
          </div>

          {/* RIGHT SIDE: Sidebar Metadata (32%) */}
          <aside className="flex-[0_0_32%] bg-white p-8 overflow-y-auto space-y-8">

            {/* Lead Info Card */}
            <div className="space-y-6">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
                  <User className="w-4 h-4 text-blue-600" />
                </div>
                <h4 className="font-bold text-gray-900">Informações do Contato</h4>
              </div>

              <div className="space-y-5">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 text-gray-400">
                    <User className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-gray-400 uppercase">Nome Completo</p>
                    <p className="text-sm font-bold text-gray-900">{opportunity.lead_name}</p>
                    {opportunity.lead_status && (
                      <Badge variant="secondary" className="mt-1 bg-blue-50 text-blue-600 border-none text-[9px] font-bold uppercase py-0 px-2 leading-tight">
                        {opportunity.lead_status}
                      </Badge>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 pt-4 border-t border-gray-50">
                  <div className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer border border-transparent hover:border-gray-100">
                    <div className="w-8 h-8 rounded-lg bg-green-50 flex items-center justify-center flex-shrink-0">
                      <Phone className="w-4 h-4 text-green-600" />
                    </div>
                    <div className="truncate">
                      <p className="text-[10px] font-bold text-gray-400 uppercase">Telefone</p>
                      <p className="text-xs font-bold text-gray-900 truncate">{opportunity.lead_phone || 'Não informado'}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer border border-transparent hover:border-gray-100">
                    <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                      <Mail className="w-4 h-4 text-blue-600" />
                    </div>
                    <div className="truncate">
                      <p className="text-[10px] font-bold text-gray-400 uppercase">Email</p>
                      <p className="text-xs font-bold text-gray-900 truncate">{opportunity.lead_email || 'Não informado'}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Seller Info Card */}
            {opportunity.seller_name && (
              <div className="space-y-4 pt-6 border-t border-gray-100">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-orange-100 flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-orange-600" />
                  </div>
                  <h4 className="font-bold text-gray-900">Responsável</h4>
                </div>
                <div className="bg-gray-50 rounded-2xl p-4 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-orange-200 border-2 border-white flex items-center justify-center font-bold text-orange-700 shadow-sm">
                    {opportunity.seller_name.charAt(0)}
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-gray-400 uppercase">Corretor</p>
                    <p className="text-sm font-extrabold text-gray-900">{opportunity.seller_name}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Footprint / Updates */}
            <div className="pt-6 border-t border-gray-100 space-y-4">
              <div className="flex items-center justify-between text-[11px] font-bold text-gray-400 px-1">
                <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" /> Últimas Atualizações</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </div>
              <div className="space-y-3">
                <div className="flex gap-3 relative pb-2 group">
                  <div className="w-1 absolute top-3 left-[7px] bottom-0 bg-gray-100 rounded-full" />
                  <div className="w-4 h-4 rounded-full bg-blue-500 border-2 border-white shadow-sm flex-shrink-0 z-10" />
                  <div>
                    <p className="text-xs font-bold text-gray-800">Criada</p>
                    <p className="text-[10px] text-gray-500">{formatDateShort(opportunity.created_at)}</p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-4 h-4 rounded-full bg-green-500 border-2 border-white shadow-sm flex-shrink-0 z-10" />
                  <div>
                    <p className="text-xs font-bold text-gray-800">Status Ativo</p>
                    <p className="text-[10px] text-gray-500">{formatDateShort(opportunity.updated_at)}</p>
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>

        {/* --- FOOTER: ACTION BOTTOM BAR --- */}
        <div className="bg-white border-t border-gray-100 px-8 py-5 flex items-center justify-between flex-shrink-0 z-20 shadow-[0_-4px_20px_rgba(0,0,0,0.03)]">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-blue-500" />
              <label className="text-xs font-black text-gray-400 uppercase tracking-widest">Ação Necessária</label>
            </div>

            <div className="flex items-center gap-2 bg-gray-50 p-1.5 rounded-2xl border border-gray-100 shadow-inner">
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                className="pl-4 pr-10 py-2.5 bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 font-extrabold text-sm text-gray-700 shadow-sm appearance-none cursor-pointer hover:bg-gray-50 transition-colors"
                style={{ backgroundImage: 'radial-gradient(circle, #666 1px, transparent 1px)', backgroundSize: '24px 24px' }}
              >
                <option value="novo">🚀 Nova Oportunidade</option>
                <option value="negociacao">🤝 Em Negociação</option>
                <option value="proposta">📄 Proposta Enviada</option>
                <option value="ganho">🏆 Negócio Fechado (Venda!)</option>
                <option value="perdido">❌ Negócio Perdido</option>
              </select>

              <Button
                onClick={handleUpdateStatus}
                disabled={updating || newStatus === opportunity.status}
                size="lg"
                className="gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-lg shadow-blue-200 px-8 py-6 transition-all active:scale-95 disabled:opacity-50 disabled:grayscale"
              >
                {updating ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Processando...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-5 h-5" />
                    Confirmar Transição
                  </>
                )}
              </Button>
            </div>
          </div>

          <p className="text-[10px] font-bold text-gray-300 italic">
            Alterações impactam metas e relatórios automaticamente.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
