"use client";

import { useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import {
  ChevronRight,
  UserCheck,
  UserPlus,
  X,
  Loader2,
  ChevronDown,
  Flame,
  Phone,
  Send,
} from "lucide-react";
import { updateLead } from "@/lib/api";

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
  onUpdateLead?: () => void;
  onOpenAssignModal?: (leadId: number) => void;
  showHandoffButton?: boolean;
}

const qualificationVariant: Record<string, "hot" | "warm" | "cold" | "default"> = {
  quente: "hot",
  morno: "warm",
  frio: "cold",
  hot: "hot",
  warm: "warm",
  cold: "cold",
};

const qualificationLabels: Record<string, string> = {
  quente: "QUENTE",
  morno: "MORNO",
  frio: "FRIO",
  hot: "QUENTE",
  warm: "MORNO",
  cold: "FRIO",
};

const statusLabels: Record<string, string> = {
  novo: "Novo",
  em_atendimento: "Em Atendimento",
  qualificado: "Qualificado",
  transferido: "Transferido",
  convertido: "Convertido",
  perdido: "Perdido",
  contacted: "Em Contato",
  new: "Novo",
  in_progress: "Em Atendimento",
  qualified: "Qualificado",
  handed_off: "Transferido",
  converted: "Convertido",
  lost: "Perdido",
  closed: "Fechado",
};

const statusOptions = [
  { value: "new", label: "Novo", color: "bg-gray-100 text-gray-700" },
  { value: "in_progress", label: "Em Atendimento", color: "bg-blue-100 text-blue-700" },
  { value: "qualified", label: "Qualificado", color: "bg-purple-100 text-purple-700" },
  { value: "handed_off", label: "Transferido", color: "bg-orange-100 text-orange-700" },
  { value: "converted", label: "Convertido", color: "bg-green-100 text-green-700" },
  { value: "lost", label: "Perdido", color: "bg-red-100 text-red-700" },
];

export function LeadsTable({
  leads,
  sellers = [],
  onAssignSeller,
  onUnassignSeller,
  onUpdateLead,
  onOpenAssignModal,
  showHandoffButton = false,
}: LeadsTableProps) {
  const [loadingLead, setLoadingLead] = useState<number | null>(null);
  const [modalLeadId, setModalLeadId] = useState<number | null>(null);
  const [statusDropdownId, setStatusDropdownId] = useState<number | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState<number | null>(null);

  const availableSellers = sellers.filter((s) => s.active);

  async function handleAssign(leadId: number, sellerId: number) {
    if (!onAssignSeller) return;
    setLoadingLead(leadId);
    await onAssignSeller(leadId, sellerId);
    setLoadingLead(null);
    setModalLeadId(null);
  }

  async function handleUnassign(leadId: number) {
    if (!onUnassignSeller) return;
    setLoadingLead(leadId);
    await onUnassignSeller(leadId);
    setLoadingLead(null);
  }

  async function handleStatusChange(leadId: number, newStatus: string) {
    setUpdatingStatus(leadId);
    try {
      await updateLead(leadId, { status: newStatus });
      if (onUpdateLead) onUpdateLead();
    } catch (err) {
      console.error("Erro ao atualizar status:", err);
    } finally {
      setUpdatingStatus(null);
      setStatusDropdownId(null);
    }
  }

  function getStatusColor(status: string): string {
    const option = statusOptions.find((o) => o.value === status);
    if (option) return option.color;
    if (status === "novo" || status === "new") return "bg-gray-100 text-gray-700";
    if (status === "em_atendimento" || status === "contacted") return "bg-blue-100 text-blue-700";
    if (status === "qualificado") return "bg-purple-100 text-purple-700";
    if (status === "transferido") return "bg-orange-100 text-orange-700";
    if (status === "convertido") return "bg-green-100 text-green-700";
    if (status === "perdido") return "bg-red-100 text-red-700";
    return "bg-gray-100 text-gray-700";
  }

  function isHotLead(qualification: string): boolean {
    return ["hot", "quente"].includes(qualification);
  }

  function handleOpenModal(leadId: number) {
    if (onOpenAssignModal) {
      onOpenAssignModal(leadId);
    } else {
      setModalLeadId(leadId);
    }
  }

  if (leads.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        Nenhum lead encontrado
      </div>
    );
  }

  return (
    <>
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Nome</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Telefone</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Qualificacao</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Status</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Vendedor</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Data</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => {
              const isHot = isHotLead(lead.qualification);
              const needsHandoff = isHot && !lead.assigned_seller_id && lead.status !== "handed_off";
              return (
                <tr
                  key={lead.id}
                  className={`border-b border-gray-100 hover:bg-gray-50 transition ${needsHandoff ? "bg-orange-50/50" : ""}`}
                >
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      {isHot && (
                        <span className="flex-shrink-0" title="Lead Quente">
                          <Flame className="w-4 h-4 text-orange-500" />
                        </span>
                      )}
                      <span className="font-medium text-gray-900">
                        {lead.name || "Sem nome"}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    {lead.phone ? (
                      <a
                        href={`https://wa.me/${lead.phone.replace(/\D/g, "")}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-gray-600 hover:text-green-600 transition"
                      >
                        <Phone className="w-3.5 h-3.5" />
                        {lead.phone}
                      </a>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <Badge variant={qualificationVariant[lead.qualification] || "default"}>
                      {qualificationLabels[lead.qualification] || lead.qualification?.toUpperCase() || "N/A"}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 relative">
                    {updatingStatus === lead.id ? (
                      <div className="flex items-center gap-2 text-gray-400">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="text-sm">Salvando...</span>
                      </div>
                    ) : (
                      <div className="relative">
                        <button
                          onClick={() => setStatusDropdownId(statusDropdownId === lead.id ? null : lead.id)}
                          className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition ${getStatusColor(lead.status)} hover:opacity-80`}
                        >
                          {statusLabels[lead.status] || lead.status}
                          <ChevronDown className="w-3 h-3" />
                        </button>
                        {statusDropdownId === lead.id && (
                          <>
                            <div className="fixed inset-0 z-10" onClick={() => setStatusDropdownId(null)} />
                            <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 min-w-[160px]">
                              {statusOptions.map((option) => (
                                <button
                                  key={option.value}
                                  onClick={() => handleStatusChange(lead.id, option.value)}
                                  className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg flex items-center gap-2 ${lead.status === option.value ? "bg-gray-50 font-medium" : ""}`}
                                >
                                  <span className={`w-2 h-2 rounded-full ${option.color.split(" ")[0].replace("100", "500")}`} />
                                  {option.label}
                                </button>
                              ))}
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {loadingLead === lead.id ? (
                      <div className="flex items-center gap-2 text-gray-400">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Salvando...
                      </div>
                    ) : lead.assigned_seller ? (
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 bg-green-100 rounded-full flex items-center justify-center">
                          <UserCheck className="w-4 h-4 text-green-600" />
                        </div>
                        <span className="text-gray-700">{lead.assigned_seller.name}</span>
                        <button
                          onClick={() => handleUnassign(lead.id)}
                          className="p-1 hover:bg-red-50 rounded text-gray-400 hover:text-red-500"
                          title="Remover atribuicao"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : showHandoffButton && needsHandoff ? (
                      <button
                        onClick={() => handleOpenModal(lead.id)}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-orange-500 hover:bg-orange-600 rounded-lg transition shadow-sm"
                      >
                        <Send className="w-4 h-4" />
                        Transferir
                      </button>
                    ) : (
                      <button
                        onClick={() => handleOpenModal(lead.id)}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                      >
                        <UserPlus className="w-4 h-4" />
                        Atribuir
                      </button>
                    )}
                  </td>
                  <td className="py-3 px-4 text-gray-500 text-sm">
                    {new Date(lead.created_at).toLocaleDateString("pt-BR")}
                  </td>
                  <td className="py-3 px-4">
                    <Link href={`/dashboard/leads/${lead.id}`} className="text-blue-600 hover:text-blue-800">
                      <ChevronRight className="w-5 h-5" />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="md:hidden space-y-3 px-2 pb-4">
        {leads.map((lead) => {
          const isHot = isHotLead(lead.qualification);
          const needsHandoff = isHot && !lead.assigned_seller_id && lead.status !== "handed_off";
          return (
            <div
              key={lead.id}
              className={`p-4 border rounded-lg ${needsHandoff ? "border-orange-200 bg-orange-50/50" : "border-gray-200 bg-white"}`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  {isHot && <Flame className="w-4 h-4 text-orange-500" />}
                  <span className="font-medium text-gray-900">{lead.name || "Sem nome"}</span>
                </div>
                <Badge variant={qualificationVariant[lead.qualification] || "default"}>
                  {qualificationLabels[lead.qualification] || "N/A"}
                </Badge>
              </div>
              <div className="space-y-2 text-sm">
                {lead.phone && (
                  <a
                    href={`https://wa.me/${lead.phone.replace(/\D/g, "")}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-gray-600"
                  >
                    <Phone className="w-4 h-4" />
                    {lead.phone}
                  </a>
                )}
                <div className="flex items-center justify-between">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(lead.status)}`}>
                    {statusLabels[lead.status] || lead.status}
                  </span>
                  <span className="text-gray-400 text-xs">
                    {new Date(lead.created_at).toLocaleDateString("pt-BR")}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3 pt-3 border-t">
                {lead.assigned_seller ? (
                  <div className="flex items-center gap-2 flex-1">
                    <UserCheck className="w-4 h-4 text-green-600" />
                    <span className="text-sm text-gray-700">{lead.assigned_seller.name}</span>
                  </div>
                ) : showHandoffButton && needsHandoff ? (
                  <button
                    onClick={() => handleOpenModal(lead.id)}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-white bg-orange-500 hover:bg-orange-600 rounded-lg"
                  >
                    <Send className="w-4 h-4" />
                    Transferir para Vendedor
                  </button>
                ) : (
                  <button
                    onClick={() => handleOpenModal(lead.id)}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
                  >
                    <UserPlus className="w-4 h-4" />
                    Atribuir Vendedor
                  </button>
                )}
                <Link href={`/dashboard/leads/${lead.id}`} className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg">
                  <ChevronRight className="w-5 h-5" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      {modalLeadId !== null && !onOpenAssignModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setModalLeadId(null)} />
          <div className="relative bg-white w-full max-w-sm rounded-xl shadow-2xl p-6 z-50">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Selecionar vendedor</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {availableSellers.map((seller) => (
                <button
                  key={seller.id}
                  onClick={() => handleAssign(modalLeadId, seller.id)}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg border hover:bg-gray-100 transition"
                >
                  <div className={`w-2 h-2 rounded-full ${seller.available ? "bg-green-500" : "bg-gray-300"}`} />
                  <span className="flex-1 text-left">{seller.name}</span>
                </button>
              ))}
              {availableSellers.length === 0 && (
                <p className="text-gray-500 text-sm text-center py-3">Nenhum vendedor disponivel.</p>
              )}
            </div>
            <button
              onClick={() => setModalLeadId(null)}
              className="mt-4 w-full py-2 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 transition"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}
    </>
  );
}