'use client';

import { X, Phone, Calendar } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface AssignedSeller {
  id: number;
  name: string;
  whatsapp: string;
}

interface Lead {
  id: number;
  name: string | null;
  phone: string | null;
  qualification: string;
  status: string;
  created_at: string;
  assigned_seller?: AssignedSeller | null;
}

interface LeadsQuickviewProps {
  lead: Lead | null;
  onClose: () => void;
  onOpenAssignModal: (leadId: number) => void;
}

const statusLabels: Record<string, string> = {
  novo: 'Novo',
  em_atendimento: 'Em Atendimento',
  qualificado: 'Qualificado',
  transferido: 'Transferido',
  convertido: 'Convertido',
  perdido: 'Perdido',
  contacted: 'Em Contato',
  new: 'Novo',
  in_progress: 'Em Atendimento',
  qualified: 'Qualificado',
  handed_off: 'Transferido',
  converted: 'Convertido',
  lost: 'Perdido',
  closed: 'Fechado',
};

export function LeadsQuickview({
  lead,
  onClose,
  onOpenAssignModal,
}: LeadsQuickviewProps) {
  if (!lead) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full max-w-md bg-white shadow-2xl border-l border-gray-200 flex flex-col">

      {/* HEADER */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide">
            Detalhes do lead
          </p>
          <h2 className="text-base font-semibold text-gray-900">
            {lead.name || 'Sem nome'}
          </h2>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* BODY */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">

        {/* BADGES */}
        <div className="flex items-center gap-3">
          <Badge>{statusLabels[lead.status] || lead.status}</Badge>
          <Badge variant="outline">{lead.qualification?.toUpperCase()}</Badge>
        </div>

        {/* CONTACT INFO */}
        <div className="space-y-2 text-sm">
          {lead.phone && (
            <div className="flex items-center gap-2 text-gray-700">
              <Phone className="w-4 h-4 text-gray-400" />
              <span>{lead.phone}</span>
            </div>
          )}

          <div className="flex items-center gap-2 text-gray-500 text-xs">
            <Calendar className="w-3 h-3" />
            <span>
              Criado em {new Date(lead.created_at).toLocaleDateString('pt-BR')}
            </span>
          </div>
        </div>

        {/* SELLER INFO */}
        <div className="border-t border-gray-100 pt-4 space-y-2 text-sm">
          <p className="text-xs text-gray-400 uppercase tracking-wide">
            Vendedor responsável
          </p>

          {lead.assigned_seller ? (
            <div className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {lead.assigned_seller.name}
                </p>
                <p className="text-xs text-gray-500">
                  {lead.assigned_seller.whatsapp}
                </p>
              </div>
            </div>
          ) : (
            <button
              onClick={() => onOpenAssignModal(lead.id)}
              className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
            >
              <span>Atribuir vendedor agora</span>
            </button>
          )}
        </div>
      </div>

    </div>
  );
}
