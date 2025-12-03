'use client';

import { useState, useRef } from 'react';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { ChevronRight, UserCheck, UserPlus, X, Loader2, Phone, Calendar } from 'lucide-react';

interface AssignedSeller {
  id: number;
  name: string;
  whatsapp: string;
}

interface Seller {
  id: number;
  name: string;
  whatsapp: string;
  available: boolean;
  active: boolean;
}

interface Lead {
  id: number;
  name: string | null;
  phone: string | null;
  qualification: string;
  status: string;
  created_at: string;
  assigned_seller?: AssignedSeller | null;
  assigned_seller_id?: number | null;
}

interface LeadsTableProps {
  leads: Lead[];
  sellers?: Seller[];
  onAssignSeller?: (leadId: number, sellerId: number) => Promise<void>;
  onUnassignSeller?: (leadId: number) => Promise<void>;
}

const qualificationVariant: Record<string, 'hot' | 'warm' | 'cold' | 'default'> = {
  quente: 'hot',
  morno: 'warm',
  frio: 'cold',
  hot: 'hot',
  warm: 'warm',
  cold: 'cold',
};

const qualificationLabels: Record<string, string> = {
  quente: 'QUENTE',
  morno: 'MORNO',
  frio: 'FRIO',
  hot: 'QUENTE',
  warm: 'MORNO',
  cold: 'FRIO',
};

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

interface DropdownPosition {
  top: number;
  left: number;
}

export function LeadsTable({ leads, sellers = [], onAssignSeller, onUnassignSeller }: LeadsTableProps) {
  const [openDropdown, setOpenDropdown] = useState<number | null>(null);
  const [loadingLead, setLoadingLead] = useState<number | null>(null);
  const [dropdownPosition, setDropdownPosition] = useState<DropdownPosition>({ top: 0, left: 0 });
  const buttonRefs = useRef<Record<number, HTMLButtonElement | null>>({});

  const handleOpenDropdown = (leadId: number, isMobile = false) => {
    if (openDropdown === leadId) {
      setOpenDropdown(null);
      return;
    }

    const button = buttonRefs.current[leadId];
    if (button && !isMobile) {
      const rect = button.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + 4,
        left: Math.min(rect.left, window.innerWidth - 240),
      });
    } else {
      // Mobile: centraliza
      setDropdownPosition({
        top: window.innerHeight / 2 - 100,
        left: window.innerWidth / 2 - 112,
      });
    }
    setOpenDropdown(leadId);
  };

  const handleAssign = async (leadId: number, sellerId: number) => {
    if (!onAssignSeller) return;

    setLoadingLead(leadId);
    try {
      await onAssignSeller(leadId, sellerId);
    } finally {
      setLoadingLead(null);
      setOpenDropdown(null);
    }
  };

  const handleUnassign = async (leadId: number) => {
    if (!onUnassignSeller) return;

    setLoadingLead(leadId);
    try {
      await onUnassignSeller(leadId);
    } finally {
      setLoadingLead(null);
    }
  };

  const availableSellers = sellers.filter(s => s.active);

  if (leads.length === 0) {
    return <div className="text-center py-8 text-gray-500">Nenhum lead encontrado</div>;
  }

  return (
    <>
      {/* Versão Desktop - Tabela */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Nome</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Telefone</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Qualificação</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Status</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Vendedor</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Data</th>
              <th className="py-3 px-4"></th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => (
              <tr key={lead.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-3 px-4">
                  <span className="font-medium text-gray-900">{lead.name || 'Sem nome'}</span>
                </td>
                <td className="py-3 px-4 text-gray-600">{lead.phone || '-'}</td>
                <td className="py-3 px-4">
                  <Badge variant={qualificationVariant[lead.qualification] || 'default'}>
                    {qualificationLabels[lead.qualification] || lead.qualification.toUpperCase()}
                  </Badge>
                </td>
                <td className="py-3 px-4 text-gray-600">
                  {statusLabels[lead.status] || lead.status}
                </td>
                <td className="py-3 px-4">
                  {loadingLead === lead.id ? (
                    <div className="flex items-center gap-2 text-gray-400">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm">Salvando...</span>
                    </div>
                  ) : lead.assigned_seller ? (
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 bg-green-100 rounded-full flex items-center justify-center">
                        <UserCheck className="w-4 h-4 text-green-600" />
                      </div>
                      <span className="text-sm text-gray-700">{lead.assigned_seller.name}</span>
                      {onUnassignSeller && (
                        <button
                          onClick={() => handleUnassign(lead.id)}
                          className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                          title="Remover atribuição"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ) : (
                    <button
                      ref={(el) => { buttonRefs.current[lead.id] = el; }}
                      onClick={() => handleOpenDropdown(lead.id)}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    >
                      <UserPlus className="w-4 h-4" />
                      <span>Atribuir</span>
                    </button>
                  )}
                </td>
                <td className="py-3 px-4 text-gray-500 text-sm">
                  {new Date(lead.created_at).toLocaleDateString('pt-BR')}
                </td>
                <td className="py-3 px-4">
                  <Link href={`/dashboard/leads/${lead.id}`} className="text-blue-600 hover:text-blue-800">
                    <ChevronRight className="w-5 h-5" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Versão Mobile - Cards */}
      <div className="md:hidden space-y-3">
        {leads.map((lead) => (
          <div
            key={lead.id}
            className="bg-gray-50 rounded-lg p-4 border border-gray-100"
          >
            {/* Header do Card */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-gray-900 truncate">
                  {lead.name || 'Sem nome'}
                </h4>
                {lead.phone && (
                  <div className="flex items-center gap-1 text-sm text-gray-500 mt-1">
                    <Phone className="w-3 h-3" />
                    <span>{lead.phone}</span>
                  </div>
                )}
              </div>
              <Badge variant={qualificationVariant[lead.qualification] || 'default'}>
                {qualificationLabels[lead.qualification] || lead.qualification.toUpperCase()}
              </Badge>
            </div>

            {/* Info do Card */}
            <div className="flex items-center gap-4 text-sm text-gray-500 mb-3">
              <span className="px-2 py-0.5 bg-gray-200 rounded text-xs">
                {statusLabels[lead.status] || lead.status}
              </span>
              <div className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                <span>{new Date(lead.created_at).toLocaleDateString('pt-BR')}</span>
              </div>
            </div>

            {/* Vendedor + Ações */}
            <div className="flex items-center justify-between pt-3 border-t border-gray-200">
              {loadingLead === lead.id ? (
                <div className="flex items-center gap-2 text-gray-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Salvando...</span>
                </div>
              ) : lead.assigned_seller ? (
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center">
                    <UserCheck className="w-3 h-3 text-green-600" />
                  </div>
                  <span className="text-sm text-gray-700">{lead.assigned_seller.name}</span>
                  {onUnassignSeller && (
                    <button
                      onClick={() => handleUnassign(lead.id)}
                      className="p-1 text-gray-400 hover:text-red-500 rounded"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ) : (
                <button
                  ref={(el) => { buttonRefs.current[lead.id] = el; }}
                  onClick={() => handleOpenDropdown(lead.id, true)}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  <UserPlus className="w-4 h-4" />
                  <span>Atribuir</span>
                </button>
              )}

              <Link
                href={`/dashboard/leads/${lead.id}`}
                className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
              >
                <span>Ver detalhes</span>
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        ))}
      </div>

      {/* Dropdown de seleção de vendedor */}
      {openDropdown !== null && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/20 md:bg-transparent"
            onClick={() => setOpenDropdown(null)}
          />
          <div
            className="fixed w-56 bg-white border border-gray-200 rounded-lg shadow-xl z-50 max-h-64 overflow-y-auto"
            style={{ top: dropdownPosition.top, left: dropdownPosition.left }}
          >
            <div className="py-1">
              <div className="px-3 py-2 text-xs font-medium text-gray-500 uppercase border-b sticky top-0 bg-white">
                Selecione o vendedor
              </div>
              {availableSellers.length > 0 ? (
                availableSellers.map((seller) => (
                  <button
                    key={seller.id}
                    onClick={() => handleAssign(openDropdown, seller.id)}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                  >
                    <div className={`w-2 h-2 rounded-full ${seller.available ? 'bg-green-500' : 'bg-gray-300'}`} />
                    <span className="flex-1">{seller.name}</span>
                    {!seller.available && (
                      <span className="text-xs text-gray-400">Indisponível</span>
                    )}
                  </button>
                ))
              ) : (
                <div className="p-3 text-sm text-gray-500">
                  Nenhum vendedor cadastrado.
                  <Link href="/dashboard/sellers" className="block mt-2 text-blue-600 hover:underline">
                    Cadastrar vendedor →
                  </Link>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}