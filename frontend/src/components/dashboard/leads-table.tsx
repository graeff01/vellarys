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
  Phone,
  Calendar,
} from "lucide-react";

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

export function LeadsTable({
  leads,
  sellers = [],
  onAssignSeller,
  onUnassignSeller,
}: LeadsTableProps) {
  const [loadingLead, setLoadingLead] = useState<number | null>(null);
  const [modalLeadId, setModalLeadId] = useState<number | null>(null);

  const availableSellers = sellers.filter((s) => s.active);

  async function handleAssign(leadId: number, sellerId: number) {
    if (!onAssignSeller) return;
    setLoadingLead(leadId);

    await onAssignSeller(leadId, sellerId);

    setLoadingLead(null);
    setModalLeadId(null); // fecha o modal
  }

  async function handleUnassign(leadId: number) {
    if (!onUnassignSeller) return;
    setLoadingLead(leadId);

    await onUnassignSeller(leadId);

    setLoadingLead(null);
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
      {/* ====================== DESKTOP TABLE ====================== */}
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
              <th></th>
            </tr>
          </thead>

          <tbody>
            {leads.map((lead) => (
              <tr
                key={lead.id}
                className="border-b border-gray-100 hover:bg-gray-50 transition"
              >
                <td className="py-3 px-4 font-medium text-gray-900">
                  {lead.name || "Sem nome"}
                </td>

                <td className="py-3 px-4 text-gray-600">{lead.phone || "-"}</td>

                <td className="py-3 px-4">
                  <Badge variant={qualificationVariant[lead.qualification] || "default"}>
                    {qualificationLabels[lead.qualification] ||
                      lead.qualification.toUpperCase()}
                  </Badge>
                </td>

                <td className="py-3 px-4 text-gray-600">
                  {statusLabels[lead.status] || lead.status}
                </td>

                {/* ---------------- VENDEDOR ---------------- */}
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
                      <span>{lead.assigned_seller.name}</span>
                      <button
                        onClick={() => handleUnassign(lead.id)}
                        className="p-1 hover:bg-red-50 rounded text-gray-400 hover:text-red-500"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setModalLeadId(lead.id)}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
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
                  <Link
                    href={`/dashboard/leads/${lead.id}`}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ====================== MODAL ====================== */}
      {modalLeadId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* BACKDROP */}
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setModalLeadId(null)}
          />

          {/* MODAL BOX */}
          <div className="relative bg-white w-full max-w-sm rounded-xl shadow-2xl p-6 z-50 animate-fadeIn">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Selecionar vendedor
            </h3>

            <div className="space-y-2 max-h-64 overflow-y-auto">
              {availableSellers.map((seller) => (
                <button
                  key={seller.id}
                  onClick={() => handleAssign(modalLeadId, seller.id)}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg border hover:bg-gray-100 transition"
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      seller.available ? "bg-green-500" : "bg-gray-300"
                    }`}
                  />
                  <span className="flex-1 text-left">{seller.name}</span>
                </button>
              ))}

              {availableSellers.length === 0 && (
                <p className="text-gray-500 text-sm text-center py-3">
                  Nenhum vendedor disponível.
                </p>
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
