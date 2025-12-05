'use client';

import { Badge } from '@/components/ui/badge';
import { ChevronRight, UserPlus } from 'lucide-react';

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

type CanonicalStatus = 'new' | 'in_progress' | 'qualified' | 'handed_off' | 'closed';

interface LeadsKanbanProps {
  leads: Lead[];
  onSelectLead: (lead: Lead) => void;
  onOpenAssignModal: (leadId: number) => void;
}

const COLUMNS: { key: CanonicalStatus; title: string; helper: string }[] = [
  { key: 'new', title: 'Novos', helper: 'Entraram recentemente' },
  { key: 'in_progress', title: 'Em atendimento', helper: 'Sendo trabalhados' },
  { key: 'qualified', title: 'Qualificados', helper: 'Prontos para fechar' },
  { key: 'handed_off', title: 'Transferidos', helper: 'Direto para o cliente' },
  { key: 'closed', title: 'Fechados', helper: 'Ganhos ou perdidos' },
];

function normalizeStatus(status: string): CanonicalStatus {
  switch (status) {
    case 'novo':
    case 'new':
      return 'new';
    case 'em_atendimento':
    case 'in_progress':
    case 'contacted':
      return 'in_progress';
    case 'qualified':
    case 'qualificado':
      return 'qualified';
    case 'handed_off':
    case 'transferido':
      return 'handed_off';
    case 'closed':
    case 'convertido':
    case 'lost':
    case 'perdido':
      return 'closed';
    default:
      return 'new';
  }
}

export function LeadsKanban({
  leads,
  onSelectLead,
  onOpenAssignModal,
}: LeadsKanbanProps) {
  const grouped: Record<CanonicalStatus, Lead[]> = {
    new: [],
    in_progress: [],
    qualified: [],
    handed_off: [],
    closed: [],
  };

  for (const lead of leads) {
    const key = normalizeStatus(lead.status);
    grouped[key].push(lead);
  }

  return (
    <div className="grid md:grid-cols-5 gap-4 overflow-x-auto pb-2">
      {COLUMNS.map((col) => (
        <div
          key={col.key}
          className="min-w-[220px] bg-gray-50/60 border border-gray-200 rounded-xl p-3 flex flex-col max-h-[70vh]"
        >
          <div className="flex items-center justify-between mb-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                {col.title}
              </p>
              <p className="text-[11px] text-gray-400">{col.helper}</p>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-white border border-gray-200 text-xs text-gray-600">
              {grouped[col.key].length}
            </span>
          </div>

          <div className="flex-1 space-y-2 overflow-y-auto pr-1">
            {grouped[col.key].length === 0 && (
              <div className="text-[11px] text-gray-400 italic bg-white border border-dashed border-gray-200 rounded-lg p-3">
                Nenhum lead aqui ainda.
              </div>
            )}

            {grouped[col.key].map((lead) => (
              <button
                key={lead.id}
                onClick={() => onSelectLead(lead)}
                className="w-full text-left rounded-lg bg-white border border-gray-200 hover:border-blue-500 hover:shadow-sm transition-all p-3 space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {lead.name || 'Sem nome'}
                    </p>
                    {lead.phone && (
                      <p className="text-xs text-gray-500">{lead.phone}</p>
                    )}
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-300" />
                </div>

                <div className="flex items-center justify-between">
                  <Badge variant="outline" className="text-[10px] px-2 py-0.5">
                    {lead.qualification?.toUpperCase() || 'SEM QUALIF.'}
                  </Badge>
                  <span className="text-[11px] text-gray-400">
                    {new Date(lead.created_at).toLocaleDateString('pt-BR')}
                  </span>
                </div>

                <div className="flex items-center justify-between pt-1 border-t border-gray-100 mt-1">
                  {lead.assigned_seller ? (
                    <span className="text-[11px] text-gray-500">
                      Vendedor:{' '}
                      <span className="font-medium">
                        {lead.assigned_seller.name}
                      </span>
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpenAssignModal(lead.id);
                      }}
                      className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-700"
                    >
                      <UserPlus className="w-3 h-3" />
                      <span>Atribuir vendedor</span>
                    </button>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
