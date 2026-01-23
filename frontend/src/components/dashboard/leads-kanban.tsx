'use client';

import { useState, useCallback, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import {
  ChevronRight,
  UserPlus,
  DollarSign,
  X,
  MessageSquare,
  AlertCircle,
  CheckCircle2,
  Trophy,
  Ban
} from 'lucide-react';
import {
  updateLead,
  createLeadOpportunity,
  winOpportunity,
  registerDeal,
} from '@/lib/api';

interface Lead {
  id: number;
  name: string | null;
  phone: string | null;
  qualification: string;
  status: string;
  created_at: string;
  assigned_seller?: {
    id: number;
    name: string;
    whatsapp: string;
  } | null;
}

type CanonicalStatus = 'new' | 'in_progress' | 'qualified' | 'handed_off' | 'won' | 'lost';

interface LeadsKanbanProps {
  leads: Lead[];
  onSelectLead: (lead: Lead) => void;
  onOpenAssignModal: (leadId: number) => void;
  onLeadUpdate?: () => void;
}

const COLUMNS: { key: CanonicalStatus; title: string; helper: string; color: string; icon: any }[] = [
  { key: 'new', title: 'Novos', helper: 'Entrada', color: 'border-blue-200 bg-blue-50/50', icon: MessageSquare },
  { key: 'in_progress', title: 'Em Atendimento', helper: 'Conversando', color: 'border-amber-200 bg-amber-50/50', icon: MessageSquare },
  { key: 'qualified', title: 'Qualificados', helper: 'Quentes', color: 'border-emerald-200 bg-emerald-50/50', icon: CheckCircle2 },
  { key: 'handed_off', title: 'Transferidos', helper: 'Com Vendedor', color: 'border-indigo-200 bg-indigo-50/50', icon: UserPlus },
  { key: 'won', title: 'Venda / Ganho', helper: 'Sucesso!', color: 'border-green-300 bg-green-100/50', icon: Trophy },
  { key: 'lost', title: 'Perdidos', helper: 'Descartados', color: 'border-gray-200 bg-gray-50/50', icon: Ban },
];

const normalizeStatus = (status: string): CanonicalStatus => {
  const s = status?.toLowerCase() || '';
  if (s === 'ganho' || s === 'won' || s === 'venda' || s === 'closed' || s === 'convertido' || s === 'converted') return 'won';
  if (s === 'perdido' || s === 'lost') return 'lost';
  if (s === 'transferido' || s === 'handed_off') return 'handed_off';

  if (['novo', 'new'].includes(s)) return 'new';
  if (['em_atendimento', 'em atendimento', 'in_progress', 'contacted', 'atendimento'].includes(s)) return 'in_progress';
  if (['qualificado', 'qualified', 'hot', 'warm'].includes(s)) return 'qualified';

  return 'new';
};

export function LeadsKanban({
  leads,
  onSelectLead,
  onOpenAssignModal,
  onLeadUpdate
}: LeadsKanbanProps) {
  const [localLeads, setLocalLeads] = useState<Lead[]>(leads);
  const [draggedLead, setDraggedLead] = useState<Lead | null>(null);

  // Deal Modal State
  const [showDealModal, setShowDealModal] = useState(false);
  const [pendingDealLead, setPendingDealLead] = useState<Lead | null>(null);
  const [dealValue, setDealValue] = useState('');
  const [dealTitle, setDealTitle] = useState('');

  useEffect(() => {
    setLocalLeads(leads);
  }, [leads]);

  // Grouping
  const grouped: Record<string, Lead[]> = {
    new: [],
    in_progress: [],
    qualified: [],
    handed_off: [],
    won: [],
    lost: [],
  };

  localLeads.forEach(lead => {
    const key = normalizeStatus(lead.status);
    if (grouped[key]) grouped[key].push(lead);
    else grouped['new'].push(lead); // fallback
  });

  // Drag Handlers
  const handleDragStart = (lead: Lead) => {
    setDraggedLead(lead);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault(); // allow drop
  };

  const handleDrop = async (e: React.DragEvent, targetStatus: CanonicalStatus) => {
    e.preventDefault();
    if (!draggedLead) return;
    if (normalizeStatus(draggedLead.status) === targetStatus) {
      setDraggedLead(null);
      return;
    }

    const leadToUpdate = draggedLead;
    setDraggedLead(null);

    // Trigger Logic based on destination
    if (targetStatus === 'won') {
      // Trigger Deal Modal
      setPendingDealLead(leadToUpdate);
      setDealTitle(`Venda: ${leadToUpdate.name || 'Lead'}`);
      setShowDealModal(true);
      return; // Wait for modal
    }

    if (targetStatus === 'lost') {
      const reason = prompt('Motivo da perda? (Ex: Caro, Sem interesse, Concorrente)');
      if (!reason) return; // Cancelled
      await updateLeadStatus(leadToUpdate.id, 'lost', { loss_reason: reason });
      return;
    }

    if (targetStatus === 'in_progress') {
      if (confirm(`Iniciar atendimento com ${leadToUpdate.name}? \nIsso abrirá o WhatsApp.`)) {
        const phone = leadToUpdate.phone?.replace(/\D/g, '');
        if (phone) {
          window.open(`https://wa.me/${phone}?text=Olá ${leadToUpdate.name?.split(' ')[0] || ''}, tudo bem?`, '_blank');
        } else {
          alert('Lead sem telefone cadastrado.');
        }
      }
      await updateLeadStatus(leadToUpdate.id, 'in_progress');
      return;
    }

    // Default update (New -> Qualified, etc)
    const apiStatusMap: Record<string, string> = {
      'new': 'new',
      'in_progress': 'in_progress',
      'qualified': 'qualified',
    };
    await updateLeadStatus(leadToUpdate.id, apiStatusMap[targetStatus] || 'new');
  };

  const updateLeadStatus = async (id: number, status: string, customData?: any) => {
    // Optimistic Update
    setLocalLeads(prev => prev.map(l =>
      l.id === id ? { ...l, status, qualification: status === 'qualified' ? 'hot' : l.qualification } : l
    ));

    try {
      await updateLead(id, {
        status,
        qualification: status === 'qualified' ? 'hot' : undefined,
        custom_data: customData // Pass extra data like loss reason
      });
      if (onLeadUpdate) onLeadUpdate();
    } catch (error) {
      console.error('Failed to update lead', error);
      // Revert would go here
    }
  };

  const handleConfirmDeal = async () => {
    if (!pendingDealLead || !dealValue) return;

    const numericValue = parseFloat(dealValue.replace(/\D/g, '')) * 100; // Centavos? Or simple. Let's assume input is BRL -> cents later
    // Actually our API expects cents if integer, but let's check input. 
    // Usually user types "500000". Let's treat as raw value -> registerDeal expects cents? 
    // In lead-widgets.tsx we multiplied by 100.
    const finalValue = numericValue; // input 5000 -> 500000 cents

    try {
      // 1. Create Opportunity
      const opp = await createLeadOpportunity(pendingDealLead.id, {
        title: dealTitle,
        value: finalValue,
      });

      // 2. Win it (Explicitly if API doesn't handle status in create)
      await winOpportunity(opp.id);

      // 3. Register Deal (Dashboard Goals)
      await registerDeal(pendingDealLead.id, finalValue, `Venda via Kanban: ${dealTitle}`);

      // 4. Update Lead to CONVERTIDO
      // Usamos 'convertido' para alinhar com o backend (LeadStatus.CONVERTED)
      await updateLead(pendingDealLead.id, { status: 'convertido', qualification: 'hot' });

      // UI Update
      setLocalLeads(prev => prev.map(l =>
        l.id === pendingDealLead.id ? { ...l, status: 'won' } : l
      ));

      alert('🚀 VENDA REGISTRADA! Parabéns!');
      setShowDealModal(false);
      setPendingDealLead(null);
      setDealValue('');
      if (onLeadUpdate) onLeadUpdate();

    } catch (e) {
      console.error(e);
      alert('Erro ao registrar venda.');
    }
  };

  return (
    <>
      <div className="flex gap-4 overflow-x-auto pb-4 min-h-[500px]">
        {COLUMNS.map((col) => {
          const colLeads = grouped[col.key] || [];
          const Icon = col.icon;

          return (
            <div
              key={col.key}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, col.key)}
              className={`min-w-[260px] max-w-[260px] flex flex-col rounded-2xl border ${col.color} transition-colors duration-200
                ${draggedLead ? 'border-dashed border-2' : ''}
              `}
            >
              <div className="p-3 border-b border-black/5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-white rounded-lg shadow-sm">
                    <Icon className="w-4 h-4 text-slate-700" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wide text-slate-700">{col.title}</h3>
                    <p className="text-[10px] text-slate-500 font-medium">{col.helper}</p>
                  </div>
                </div>
                <Badge variant="outline" className="bg-white text-slate-700 font-bold border-0">
                  {colLeads.length}
                </Badge>
              </div>

              <div className="flex-1 p-2 space-y-2 overflow-y-auto max-h-[70vh]">
                {colLeads.length === 0 && (
                  <div className="h-24 flex items-center justify-center text-slate-400 text-xs italic border-2 border-dashed border-slate-200 rounded-xl">
                    Arraste para cá
                  </div>
                )}
                {colLeads.map(lead => (
                  <div
                    key={lead.id}
                    draggable
                    onDragStart={() => handleDragStart(lead)}
                    className="group bg-white p-3 rounded-xl border border-slate-100 shadow-sm hover:shadow-md cursor-grab active:cursor-grabbing transition-all hover:scale-[1.02]"
                    onClick={() => onSelectLead(lead)}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase
                         ${lead.qualification === 'hot' ? 'bg-rose-100 text-rose-700' :
                          lead.qualification === 'warm' ? 'bg-amber-100 text-amber-700' :
                            'bg-slate-100 text-slate-600'}`
                      }>
                        {lead.qualification === 'hot' ? '🔥 Quente' : lead.qualification || 'Lead'}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        {new Date(lead.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    <h4 className="font-bold text-slate-800 text-sm mb-1 truncate">{lead.name || 'Sem nome'}</h4>

                    {lead.phone && (
                      <p className="text-xs text-slate-500 mb-2 font-mono flex items-center gap-1">
                        <MessageSquare className="w-3 h-3" /> {lead.phone}
                      </p>
                    )}

                    <div className="flex items-center justify-between pt-2 border-t border-slate-50 mt-1">
                      {lead.assigned_seller ? (
                        <div className="flex items-center gap-1.5">
                          <div className="w-5 h-5 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center text-[10px] font-bold">
                            {lead.assigned_seller.name.charAt(0)}
                          </div>
                          <span className="text-[10px] font-bold text-slate-600 truncate max-w-[80px]">
                            {lead.assigned_seller.name}
                          </span>
                        </div>
                      ) : (
                        <button
                          onClick={(e) => { e.stopPropagation(); onOpenAssignModal(lead.id); }}
                          className="text-[10px] font-bold text-indigo-600 flex items-center gap-1 hover:bg-indigo-50 px-2 py-1 rounded transition-colors"
                        >
                          <UserPlus className="w-3 h-3" /> Atribuir
                        </button>
                      )}
                      <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-indigo-500 transition-colors" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* DEAL MODAL */}
      {showDealModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="bg-gradient-to-r from-emerald-500 to-green-600 p-6 text-white text-center">
              <Trophy className="w-12 h-12 mx-auto mb-2 text-yellow-300 drop-shadow-lg" />
              <h2 className="text-2xl font-extrabold tracking-tight">Venda Confirmada!</h2>
              <p className="text-emerald-100 font-medium">Parabéns pelo fechamento</p>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Título do Negócio</label>
                <input
                  type="text"
                  value={dealTitle}
                  onChange={e => setDealTitle(e.target.value)}
                  className="w-full border border-slate-200 rounded-xl px-4 py-2 text-sm font-semibold focus:ring-2 focus:ring-emerald-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Valor da Venda (R$)</label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
                  <input
                    type="number"
                    value={dealValue}
                    onChange={e => setDealValue(e.target.value)}
                    placeholder="0,00"
                    className="w-full border border-slate-200 rounded-xl pl-10 pr-4 py-3 text-lg font-bold text-slate-900 focus:ring-2 focus:ring-emerald-500 outline-none"
                    autoFocus
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setShowDealModal(false)}
                  className="flex-1 py-3 bg-slate-100 text-slate-600 font-bold rounded-xl hover:bg-slate-200 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleConfirmDeal}
                  className="flex-1 py-3 bg-emerald-600 text-white font-bold rounded-xl hover:bg-emerald-700 shadow-lg shadow-emerald-200 transition-all active:scale-95"
                >
                  Confirmar Venda
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
