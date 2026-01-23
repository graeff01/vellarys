'use client';

/**
 * LEAD PAGE WIDGETS
 * =================
 *
 * Componentes de widgets para a página de detalhes do lead.
 * Cada widget é independente e responsivo ao container.
 */

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Phone,
  Mail,
  MapPin,
  Building2,
  UserCheck,
  Trash2,
  Sparkles,
  Briefcase,
  Plus,
  DollarSign,
  Calendar,
  Clock,
  History,
  TrendingUp,
  Zap,
  UserPlus,
  X,
  FileText,
  MessageSquare,
  Bot,
  User,
  ChevronDown,
  CheckCircle,
  AlertCircle,
  Target,
} from 'lucide-react';
import {
  Opportunity,
  createLeadOpportunity,
  updateOpportunity,
  deleteOpportunity,
  winOpportunity,
  loseOpportunity,
  registerDeal,
  updateLead,
} from '@/lib/api';

// =============================================
// TIPOS
// =============================================

interface Lead {
  id: number;
  name: string | null;
  phone: string | null;
  email: string | null;
  city: string | null;
  qualification: string;
  status: string;
  summary: string | null;
  custom_data: Record<string, any>;
  created_at: string;
  assigned_seller?: {
    id: number;
    name: string;
    whatsapp: string;
  } | null;
}

interface LeadEvent {
  id: number;
  event_type: string;
  old_value: string | null;
  new_value: string | null;
  description: string;
  created_at: string;
}

interface Seller {
  id: number;
  name: string;
  whatsapp: string;
  available: boolean;
  active: boolean;
}

interface Message {
  id: number;
  role: string;
  content: string;
  created_at: string;
}

interface Note {
  id: number;
  content: string;
  created_by: string;
  created_at: string;
}

// =============================================
// CONTACT WIDGET
// =============================================

interface ContactWidgetProps {
  lead: Lead;
}

export function ContactWidget({ lead }: ContactWidgetProps) {
  return (
    <Card className="bg-white/80 backdrop-blur-sm rounded-2xl p-4 shadow-xl border border-white/50 h-full flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 mb-3 shrink-0">
        <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-lg">
          <Building2 className="w-4 h-4 text-white" />
        </div>
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wide">Contato</h3>
      </div>
      <div className="space-y-2.5 flex-1 overflow-auto">
        {lead.phone && (
          <div className="flex items-center gap-2.5 text-sm group">
            <Phone className="w-4 h-4 text-slate-400 group-hover:text-blue-500 transition-colors shrink-0" />
            <span className="text-slate-900 font-semibold truncate">{lead.phone}</span>
          </div>
        )}
        {lead.email && (
          <div className="flex items-center gap-2.5 text-sm group">
            <Mail className="w-4 h-4 text-slate-400 group-hover:text-blue-500 transition-colors shrink-0" />
            <span className="text-slate-900 font-semibold truncate">{lead.email}</span>
          </div>
        )}
        {lead.city && (
          <div className="flex items-center gap-2.5 text-sm group">
            <MapPin className="w-4 h-4 text-slate-400 group-hover:text-blue-500 transition-colors shrink-0" />
            <span className="text-slate-900 font-semibold truncate">{lead.city}</span>
          </div>
        )}
        {!lead.phone && !lead.email && !lead.city && (
          <p className="text-xs text-slate-400 italic">Sem informações de contato</p>
        )}
      </div>
    </Card>
  );
}

// =============================================
// SELLER WIDGET
// =============================================

interface SellerWidgetProps {
  lead: Lead;
  sellers: Seller[];
  onAssignSeller: (sellerId: number) => void;
  onRemoveSeller: () => void;
  assigning: boolean;
}

export function SellerWidget({ lead, sellers, onAssignSeller, onRemoveSeller, assigning }: SellerWidgetProps) {
  return (
    <Card className="bg-white/80 backdrop-blur-sm rounded-2xl p-4 shadow-xl border border-white/50 h-full flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 mb-3 shrink-0">
        <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-green-600 rounded-lg flex items-center justify-center shadow-lg">
          <UserCheck className="w-4 h-4 text-white" />
        </div>
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wide">Vendedor</h3>
      </div>
      <div className="flex-1 overflow-auto">
        {lead.assigned_seller ? (
          <div className="bg-gradient-to-br from-emerald-50 to-green-50 border border-emerald-200 rounded-xl p-3 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-9 h-9 bg-gradient-to-br from-emerald-500 to-green-600 rounded-lg flex items-center justify-center text-white font-bold shadow-lg shrink-0">
                  {lead.assigned_seller.name.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-slate-900 text-sm truncate">{lead.assigned_seller.name}</p>
                  <p className="text-xs text-emerald-700 font-medium truncate">{lead.assigned_seller.whatsapp}</p>
                </div>
              </div>
              <button onClick={onRemoveSeller} className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-all hover:scale-110 shrink-0">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          <select
            onChange={(e) => onAssignSeller(parseInt(e.target.value))}
            disabled={assigning}
            className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-700 font-medium outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 shadow-sm"
          >
            <option value="">Selecionar vendedor</option>
            {sellers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        )}
      </div>
    </Card>
  );
}

// =============================================
// INSIGHTS WIDGET
// =============================================

interface InsightsWidgetProps {
  lead: Lead;
}

export function InsightsWidget({ lead }: InsightsWidgetProps) {
  if (!lead.summary) {
    return (
      <Card className="bg-white/80 backdrop-blur-sm rounded-2xl p-4 shadow-xl border border-white/50 h-full flex flex-col items-center justify-center">
        <Sparkles className="w-8 h-8 text-slate-300 mb-2" />
        <p className="text-xs text-slate-400 text-center">IA ainda não gerou insights</p>
      </Card>
    );
  }

  return (
    <Card className="bg-gradient-to-br from-violet-500 via-purple-500 to-indigo-600 rounded-2xl p-4 shadow-2xl h-full flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 mb-2 shrink-0">
        <Sparkles className="w-4 h-4 text-white" />
        <h3 className="text-xs font-bold text-white uppercase tracking-wide">IA Insights</h3>
      </div>
      <div className="flex-1 overflow-auto">
        <p className="text-sm text-white/95 leading-relaxed font-medium">&quot;{lead.summary}&quot;</p>
      </div>
    </Card>
  );
}

// =============================================
// OPPORTUNITIES WIDGET (Enhanced for Real Estate)
// =============================================

interface OpportunitiesWidgetProps {
  leadId: number;
  opportunities: Opportunity[];
  onReload: () => void;
  products?: { id: number; name: string }[];
}

const STATUS_CONFIG = {
  novo: { label: 'Novo', color: 'bg-blue-100 text-blue-700', icon: Target },
  negociacao: { label: 'Negociando', color: 'bg-amber-100 text-amber-700', icon: TrendingUp },
  proposta: { label: 'Proposta', color: 'bg-purple-100 text-purple-700', icon: FileText },
  ganho: { label: 'Ganho', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  perdido: { label: 'Perdido', color: 'bg-red-100 text-red-700', icon: AlertCircle },
};

const PAYMENT_TYPES = [
  { value: 'a_vista', label: 'À Vista' },
  { value: 'financiamento', label: 'Financiamento' },
  { value: 'fgts', label: 'FGTS' },
  { value: 'parcelado', label: 'Parcelado Direto' },
  { value: 'permuta', label: 'Permuta' },
  { value: 'misto', label: 'Misto' },
];

export function OpportunitiesWidget({ leadId, opportunities, onReload, products }: OpportunitiesWidgetProps) {
  const [showForm, setShowForm] = useState(false);
  const [expandedOpp, setExpandedOpp] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);

  // Form fields
  const [title, setTitle] = useState('');
  const [value, setValue] = useState('');
  const [productId, setProductId] = useState<number | undefined>();
  const [expectedCloseDate, setExpectedCloseDate] = useState('');
  const [probability, setProbability] = useState('50');
  const [paymentType, setPaymentType] = useState('');
  const [commission, setCommission] = useState('');
  const [propertyAddress, setPropertyAddress] = useState('');
  const [notes, setNotes] = useState('');

  const resetForm = () => {
    setTitle('');
    setValue('');
    setProductId(undefined);
    setExpectedCloseDate('');
    setProbability('50');
    setPaymentType('');
    setCommission('');
    setPropertyAddress('');
    setNotes('');
  };

  const handleCreate = async () => {
    if (!title.trim()) return;
    setCreating(true);
    try {
      await createLeadOpportunity(leadId, {
        title: title.trim(),
        value: value ? parseInt(value) * 100 : 0,
        product_id: productId,
        expected_close_date: expectedCloseDate || undefined,
        notes: notes || undefined,
        custom_data: {
          probability: probability ? parseInt(probability) : 50,
          payment_type: paymentType || undefined,
          commission_percent: commission ? parseFloat(commission) : undefined,
          property_address: propertyAddress || undefined,
        },
      });
      resetForm();
      setShowForm(false);
      onReload();
    } catch (error) {
      console.error('Erro ao criar oportunidade:', error);
    } finally {
      setCreating(false);
    }
  };

  const handleStatusChange = async (oppId: number, newStatus: string) => {
    try {
      if (newStatus === 'ganho') {
        const opp = opportunities.find(o => o.id === oppId);

        if (confirm(`Confirmar venda no valor de ${formatCurrency(opp?.value || 0)}? Isso atualizará a meta e o status do lead.`)) {
          // 1. Marca oportunidade como ganha
          await winOpportunity(oppId);

          // 2. Registra a venda na dashboard (Meta)
          if (opp && opp.value > 0) {
            await registerDeal(leadId, opp.value, `Venda: ${opp.title}`);
          }

          // 3. Atualiza status do lead para Qualificado/Quente
          await updateLead(leadId, {
            status: 'qualified',
            qualification: 'hot'
          });

          // Feedback
          alert('Venda registrada com sucesso! Meta atualizada.');
        } else {
          return; // Cancelado pelo usuário
        }
      } else if (newStatus === 'perdido') {
        const reason = prompt('Motivo da perda:');
        if (reason) {
          await loseOpportunity(oppId, reason);
        } else return;
      } else {
        await updateOpportunity(oppId, { status: newStatus });
      }
      onReload();
    } catch (error) {
      console.error('Erro ao atualizar status:', error);
      alert('Erro ao atualizar status. Verifique o console.');
    }
  };

  const handleDelete = async (oppId: number) => {
    if (!confirm('Remover oportunidade?')) return;
    try {
      await deleteOpportunity(oppId);
      onReload();
    } catch (error) {
      console.error('Erro ao remover:', error);
    }
  };

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(cents / 100);
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
  };

  const getPaymentLabel = (type?: string) => {
    if (!type) return null;
    return PAYMENT_TYPES.find(p => p.value === type)?.label || type;
  };

  // Calculate total pipeline value
  const pipelineValue = opportunities
    .filter(o => !['ganho', 'perdido'].includes(o.status))
    .reduce((sum, o) => sum + o.value, 0);

  const wonValue = opportunities
    .filter(o => o.status === 'ganho')
    .reduce((sum, o) => sum + o.value, 0);

  return (
    <Card className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/50 h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50 shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-teal-500 to-cyan-600 rounded-lg flex items-center justify-center shadow-lg">
              <Briefcase className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wide">Oportunidades</h3>
              <p className="text-[9px] text-slate-400 font-bold">{opportunities.length} negócio(s)</p>
            </div>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="p-1.5 bg-teal-50 text-teal-600 rounded-lg hover:bg-teal-100 transition-all"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* Mini stats */}
        {opportunities.length > 0 && (
          <div className="flex gap-2 text-[10px]">
            <div className="flex-1 bg-blue-50 rounded-lg px-2 py-1">
              <span className="text-blue-600 font-bold">Pipeline: {formatCurrency(pipelineValue)}</span>
            </div>
            <div className="flex-1 bg-emerald-50 rounded-lg px-2 py-1">
              <span className="text-emerald-600 font-bold">Ganho: {formatCurrency(wonValue)}</span>
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-auto p-3 space-y-2">
        {/* Form de criação expandido */}
        {showForm && (
          <div className="p-3 bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl border border-slate-200 space-y-3 mb-3">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <Target className="w-4 h-4 text-teal-600" />
              <span className="text-xs font-bold text-slate-700">Nova Oportunidade</span>
            </div>

            {/* Título */}
            <input
              type="text"
              placeholder="Título da oportunidade *"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg outline-none focus:border-teal-500 bg-white"
            />

            {/* Valor e Produto */}
            <div className="grid grid-cols-2 gap-2">
              <div className="relative">
                <DollarSign className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="number"
                  placeholder="Valor (R$)"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  className="w-full pl-8 pr-3 py-2 text-sm border border-slate-200 rounded-lg outline-none focus:border-teal-500 bg-white"
                />
              </div>
              {products && products.length > 0 && (
                <select
                  value={productId || ''}
                  onChange={(e) => setProductId(e.target.value ? parseInt(e.target.value) : undefined)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg outline-none focus:border-teal-500 bg-white"
                >
                  <option value="">Imóvel (opcional)</option>
                  {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              )}
            </div>

            {/* Data prevista e Probabilidade */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-slate-500 font-bold mb-1 block">Previsão Fechamento</label>
                <input
                  type="date"
                  value={expectedCloseDate}
                  onChange={(e) => setExpectedCloseDate(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg outline-none focus:border-teal-500 bg-white"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-500 font-bold mb-1 block">Probabilidade: {probability}%</label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="10"
                  value={probability}
                  onChange={(e) => setProbability(e.target.value)}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-teal-600"
                />
              </div>
            </div>

            {/* Tipo Pagamento e Comissão */}
            <div className="grid grid-cols-2 gap-2">
              <select
                value={paymentType}
                onChange={(e) => setPaymentType(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg outline-none focus:border-teal-500 bg-white"
              >
                <option value="">Tipo Pagamento</option>
                {PAYMENT_TYPES.map(pt => <option key={pt.value} value={pt.value}>{pt.label}</option>)}
              </select>
              <div className="relative">
                <input
                  type="number"
                  step="0.1"
                  placeholder="Comissão %"
                  value={commission}
                  onChange={(e) => setCommission(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg outline-none focus:border-teal-500 bg-white"
                />
              </div>
            </div>

            {/* Endereço */}
            <input
              type="text"
              placeholder="Endereço do imóvel (opcional)"
              value={propertyAddress}
              onChange={(e) => setPropertyAddress(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg outline-none focus:border-teal-500 bg-white"
            />

            {/* Notas */}
            <textarea
              placeholder="Observações..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg outline-none focus:border-teal-500 bg-white resize-none"
            />

            {/* Botões */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={handleCreate}
                disabled={creating || !title.trim()}
                className="flex-1 py-2.5 bg-gradient-to-r from-teal-600 to-cyan-600 text-white rounded-lg text-xs font-bold hover:from-teal-700 hover:to-cyan-700 disabled:opacity-50 transition-all shadow-lg"
              >
                {creating ? 'Criando...' : 'Criar Oportunidade'}
              </button>
              <button
                onClick={() => { setShowForm(false); resetForm(); }}
                className="px-4 py-2 text-slate-600 text-xs font-bold hover:bg-slate-200 rounded-lg transition-all"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}

        {/* Lista de oportunidades */}
        {opportunities.length === 0 && !showForm ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Briefcase className="w-10 h-10 text-slate-300 mb-2" />
            <p className="text-xs text-slate-400">Nenhuma oportunidade</p>
            <button
              onClick={() => setShowForm(true)}
              className="mt-2 text-xs text-teal-600 font-bold hover:underline"
            >
              Criar primeira
            </button>
          </div>
        ) : (
          opportunities.map((opp) => {
            const statusInfo = STATUS_CONFIG[opp.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.novo;
            const isExpanded = expandedOpp === opp.id;
            const customData = opp.custom_data || {};

            return (
              <div
                key={opp.id}
                className={`bg-white border rounded-xl transition-all group ${opp.status === 'ganho' ? 'border-emerald-200 bg-emerald-50/30' :
                    opp.status === 'perdido' ? 'border-red-200 bg-red-50/30 opacity-60' :
                      'border-slate-200 hover:shadow-md'
                  }`}
              >
                {/* Main row - always visible */}
                <div
                  className="p-3 cursor-pointer"
                  onClick={() => setExpandedOpp(isExpanded ? null : opp.id)}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="min-w-0 flex-1">
                      <h4 className="font-bold text-slate-900 text-sm truncate">{opp.title}</h4>
                      <div className="flex flex-wrap items-center gap-1 mt-1">
                        {opp.product_name && (
                          <span className="text-[10px] text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">{opp.product_name}</span>
                        )}
                        {customData.probability && (
                          <span className="text-[10px] text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-bold">{customData.probability}%</span>
                        )}
                        {opp.expected_close_date && (
                          <span className="text-[10px] text-orange-600 bg-orange-50 px-1.5 py-0.5 rounded flex items-center gap-0.5">
                            <Calendar className="w-3 h-3" />
                            {formatDate(opp.expected_close_date)}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(opp.id); }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-red-500 hover:bg-red-50 rounded transition-all"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <DollarSign className="w-3 h-3 text-emerald-500" />
                      <span className="text-xs font-bold text-emerald-600">{formatCurrency(opp.value)}</span>
                      {customData.commission_percent && (
                        <span className="text-[10px] text-slate-500">(com. {customData.commission_percent}%)</span>
                      )}
                    </div>
                    <select
                      value={opp.status}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => handleStatusChange(opp.id, e.target.value)}
                      className={`px-2 py-1 rounded-lg text-[10px] font-bold border-0 cursor-pointer ${statusInfo.color}`}
                    >
                      <option value="novo">Novo</option>
                      <option value="negociacao">Negociando</option>
                      <option value="proposta">Proposta</option>
                      <option value="ganho">Ganho</option>
                      <option value="perdido">Perdido</option>
                    </select>
                  </div>
                </div>

                {/* Expanded details */}
                {isExpanded && (
                  <div className="px-3 pb-3 pt-0 border-t border-slate-100 mt-0 space-y-2 animate-in fade-in slide-in-from-top-2 duration-200">
                    {customData.payment_type && (
                      <div className="flex items-center gap-2 text-xs text-slate-600">
                        <span className="font-bold text-slate-500">Pagamento:</span>
                        <span>{getPaymentLabel(customData.payment_type)}</span>
                      </div>
                    )}
                    {customData.property_address && (
                      <div className="flex items-start gap-2 text-xs text-slate-600">
                        <MapPin className="w-3 h-3 mt-0.5 text-slate-400" />
                        <span>{customData.property_address}</span>
                      </div>
                    )}
                    {opp.notes && (
                      <div className="text-xs text-slate-500 bg-slate-50 rounded-lg p-2 italic">
                        {opp.notes}
                      </div>
                    )}
                    {opp.lost_reason && (
                      <div className="text-xs text-red-600 bg-red-50 rounded-lg p-2">
                        <span className="font-bold">Motivo perda:</span> {opp.lost_reason}
                      </div>
                    )}
                    {opp.won_at && (
                      <div className="text-xs text-emerald-600">
                        Ganho em {new Date(opp.won_at).toLocaleDateString('pt-BR')}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}

// =============================================
// TIMELINE WIDGET
// =============================================

interface TimelineWidgetProps {
  events: LeadEvent[];
}

function getEventIcon(eventType: string) {
  const iconClass = "w-3 h-3";
  switch (eventType) {
    case 'status_change': return <TrendingUp className={`${iconClass} text-blue-600`} />;
    case 'qualification_change': return <Zap className={`${iconClass} text-purple-600`} />;
    case 'seller_assigned': return <UserPlus className={`${iconClass} text-green-600`} />;
    case 'seller_unassigned': return <X className={`${iconClass} text-red-600`} />;
    default: return <Clock className={`${iconClass} text-slate-400`} />;
  }
}

export function TimelineWidget({ events }: TimelineWidgetProps) {
  return (
    <Card className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/50 h-full flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center gap-2 shrink-0">
        <div className="w-8 h-8 bg-gradient-to-br from-amber-500 to-orange-600 rounded-lg flex items-center justify-center shadow-lg">
          <History className="w-4 h-4 text-white" />
        </div>
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wide">Timeline</h3>
      </div>
      <div className="flex-1 overflow-auto p-3">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <History className="w-10 h-10 text-slate-300 mb-2" />
            <p className="text-xs text-slate-400">Sem eventos</p>
          </div>
        ) : (
          <div className="space-y-2">
            {events.slice(0, 10).map((event) => (
              <div key={event.id} className="flex items-start gap-2 p-2 rounded-lg hover:bg-slate-50 transition-colors">
                <div className="mt-0.5">{getEventIcon(event.event_type)}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-slate-900 font-semibold text-xs leading-tight truncate">{event.description}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    {new Date(event.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

// =============================================
// NOTES WIDGET
// =============================================

interface NotesWidgetProps {
  lead: Lead;
  onAddNote: (content: string) => void;
  onDeleteNote: (noteId: number) => void;
}

export function NotesWidget({ lead, onAddNote, onDeleteNote }: NotesWidgetProps) {
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState('');

  const handleSave = () => {
    if (!content.trim()) return;
    onAddNote(content.trim());
    setContent('');
    setEditing(false);
  };

  const notes: Note[] = lead.custom_data?.notas || [];

  return (
    <Card className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/50 h-full flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center shadow-lg">
            <FileText className="w-4 h-4 text-white" />
          </div>
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wide">Notas</h3>
        </div>
        {!editing && (
          <button onClick={() => setEditing(true)} className="text-xs font-bold text-blue-600 hover:text-blue-700 transition-colors">
            + Nova
          </button>
        )}
      </div>
      <div className="flex-1 overflow-auto p-3">
        {editing && (
          <div className="mb-3 space-y-2">
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Digite sua nota..."
              className="w-full bg-white border border-slate-200 rounded-xl p-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 resize-none shadow-sm"
              rows={2}
            />
            <div className="flex gap-2">
              <button onClick={handleSave} className="flex-1 py-1.5 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-lg text-xs font-bold hover:from-blue-600 hover:to-indigo-700 shadow-lg">
                Salvar
              </button>
              <button onClick={() => { setEditing(false); setContent(''); }} className="px-3 py-1.5 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors">
                Cancelar
              </button>
            </div>
          </div>
        )}

        {notes.length === 0 && !editing ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <FileText className="w-10 h-10 text-slate-300 mb-2" />
            <p className="text-xs text-slate-400">Sem notas</p>
          </div>
        ) : (
          <div className="space-y-2">
            {notes.map((nota) => (
              <div key={nota.id} className="group bg-gradient-to-br from-slate-50 to-slate-100 border border-slate-200 rounded-xl p-3 hover:shadow-lg transition-all">
                <div className="flex justify-between items-start mb-1">
                  <span className="text-[10px] text-slate-600 font-bold">{nota.created_by}</span>
                  <button onClick={() => onDeleteNote(nota.id)} className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-700 transition-all">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed font-medium">{nota.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

// =============================================
// CHAT WIDGET
// =============================================

interface ChatWidgetProps {
  messages: Message[];
  scrollRef?: React.RefObject<HTMLDivElement>;
}

function groupMessagesByDate(messages: Message[]): Map<string, Message[]> {
  const groups = new Map<string, Message[]>();
  messages.forEach(msg => {
    const date = new Date(msg.created_at).toLocaleDateString('pt-BR', {
      day: '2-digit', month: 'long', year: 'numeric'
    });
    if (!groups.has(date)) groups.set(date, []);
    groups.get(date)!.push(msg);
  });
  return groups;
}

function isToday(dateString: string): boolean {
  return new Date(dateString).toDateString() === new Date().toDateString();
}

function isYesterday(dateString: string): boolean {
  const date = new Date(dateString);
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return date.toDateString() === yesterday.toDateString();
}

function formatDateLabel(dateString: string, originalDate: string): string {
  if (isToday(originalDate)) return 'Hoje';
  if (isYesterday(originalDate)) return 'Ontem';
  return dateString;
}

export function ChatWidget({ messages, scrollRef }: ChatWidgetProps) {
  const messageGroups = groupMessagesByDate(messages);

  return (
    <Card className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-2xl border border-white/50 h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center shadow-lg">
              <MessageSquare className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-white">Conversas</h3>
              <p className="text-xs text-blue-100 font-medium">WhatsApp Business</p>
            </div>
          </div>
          <Badge className="bg-white/20 backdrop-blur-sm text-white px-3 py-1 font-bold text-xs shadow-lg border border-white/30">
            {messages.length}
          </Badge>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-3 bg-gradient-to-br from-slate-50 to-blue-50/30">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400">
            <MessageSquare className="w-16 h-16 mb-3 opacity-20" />
            <p className="text-sm font-bold">Sem mensagens</p>
          </div>
        ) : (
          <>
            {Array.from(messageGroups.entries()).map(([date, dateMessages]) => (
              <div key={date}>
                <div className="flex items-center justify-center my-4">
                  <span className="px-4 py-1.5 text-xs font-bold text-slate-600 bg-white/80 backdrop-blur-sm border border-slate-200 rounded-full shadow-lg">
                    {formatDateLabel(date, dateMessages[0].created_at)}
                  </span>
                </div>

                <div className="space-y-2">
                  {dateMessages.map((msg, idx) => {
                    const isAssistant = msg.role === 'assistant';
                    const showAvatar = idx === 0 || dateMessages[idx - 1]?.role !== msg.role;

                    return (
                      <div key={msg.id} className={`flex ${isAssistant ? 'justify-start' : 'justify-end'}`}>
                        {isAssistant && (
                          <div className={`shrink-0 mr-2 ${showAvatar ? 'visible' : 'invisible'}`}>
                            <div className="w-8 h-8 bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl flex items-center justify-center shadow-lg">
                              <Bot className="w-4 h-4 text-white" />
                            </div>
                          </div>
                        )}

                        <div className={`
                          max-w-[75%] px-4 py-2.5 rounded-2xl text-sm font-medium shadow-lg
                          ${isAssistant
                            ? 'bg-white text-slate-800 border border-slate-200'
                            : 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white'
                          }
                        `}>
                          <p className="leading-relaxed">{msg.content}</p>
                          <div className={`flex items-center gap-1 mt-1.5 text-xs font-semibold ${isAssistant ? 'text-slate-500' : 'text-blue-100'}`}>
                            <Clock className="w-3 h-3" />
                            <span>{new Date(msg.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                        </div>

                        {!isAssistant && (
                          <div className={`shrink-0 ml-2 ${showAvatar ? 'visible' : 'invisible'}`}>
                            <div className="w-8 h-8 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-xl flex items-center justify-center border-2 border-blue-200 shadow-lg">
                              <User className="w-4 h-4 text-blue-600" />
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </>
        )}
        <div ref={scrollRef} />
      </div>
    </Card>
  );
}
