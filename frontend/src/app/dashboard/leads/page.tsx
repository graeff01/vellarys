'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card, CardHeader } from '@/components/ui/card';
import { LeadsTable } from '@/components/dashboard/leads-table';
import { LeadsHeader } from '@/components/dashboard/leads-header';
import { LeadsViewSwitch } from '@/components/dashboard/leads-view-switch';
import { LeadsInsights } from '@/components/dashboard/leads-insights';
import { LeadsKanban } from '@/components/dashboard/leads-kanban';
import { LeadsQuickview } from '@/components/dashboard/leads-quickview';
import { AssignSellerModal } from '@/components/dashboard/assign-seller-modal';



import { getLeads } from '@/lib/api';
import {
  getSellers,
  assignLeadToSeller,
  unassignLeadFromSeller,
} from '@/lib/sellers';
import { Search } from 'lucide-react';

interface Seller {
  id: number;
  name: string;
  whatsapp: string;
  available: boolean;
  active: boolean;
}

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
  assigned_seller_id?: number | null;
}

interface LeadsResponse {
  items: Lead[];
  total: number;
  page: number;
  pages: number;
}

type ViewMode = 'table' | 'kanban' | 'insights';

export default function LeadsPage() {
  const [data, setData] = useState<LeadsResponse | null>(null);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    search: '',
    qualification: '',
    status: '',
    page: 1,
  });

  const [view, setView] = useState<ViewMode>('table');
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const [assignModalLeadId, setAssignModalLeadId] = useState<number | null>(
    null
  );
  const [assignModalLoading, setAssignModalLoading] = useState(false);

  async function loadData() {
    setLoading(true);
    try {
      const [leadsResponse, sellersResponse] = await Promise.all([
        getLeads(filters),
        getSellers(),
      ]);
      setData(leadsResponse as LeadsResponse);
      setSellers((sellersResponse as any).sellers || []);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [filters]);

  async function handleAssignSeller(leadId: number, sellerId: number) {
    try {
      await assignLeadToSeller(leadId, sellerId);
      await loadData();
    } catch (error) {
      console.error('Erro ao atribuir vendedor:', error);
      alert('Erro ao atribuir vendedor');
    }
  }

  async function handleAssignSellerFromModal(sellerId: number) {
    if (!assignModalLeadId) return;
    setAssignModalLoading(true);
    try {
      await handleAssignSeller(assignModalLeadId, sellerId);
      setAssignModalLeadId(null);
    } finally {
      setAssignModalLoading(false);
    }
  }

  async function handleUnassignSeller(leadId: number) {
    try {
      await unassignLeadFromSeller(leadId);
      await loadData();
    } catch (error) {
      console.error('Erro ao remover atribuição:', error);
      alert('Erro ao remover atribuição');
    }
  }

  const stats = useMemo(() => {
    const leads = data?.items || [];
    const total = leads.length;
    const hot = leads.filter((l) =>
      ['hot', 'quente'].includes(l.qualification)
    ).length;
    const warm = leads.filter((l) =>
      ['warm', 'morno'].includes(l.qualification)
    ).length;
    const cold = leads.filter((l) =>
      ['cold', 'frio'].includes(l.qualification)
    ).length;
    return { total, hot, warm, cold };
  }, [data]);

  const currentLeads = data?.items || [];

  const assignModalLead =
    assignModalLeadId != null
      ? currentLeads.find((l) => l.id === assignModalLeadId) || null
      : null;

  return (
    <div className="space-y-6">
      {/* Header + switch de visualização */}
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <LeadsHeader
          total={stats.total}
          hot={stats.hot}
          warm={stats.warm}
          cold={stats.cold}
        />

        <LeadsViewSwitch value={view} onChange={setView} />
      </div>

      {/* Filtros */}
      <Card>
        <div className="flex flex-wrap gap-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por nome, telefone..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={filters.search}
              onChange={(e) =>
                setFilters({ ...filters, search: e.target.value, page: 1 })
              }
            />
          </div>
          <select
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            value={filters.qualification}
            onChange={(e) =>
              setFilters({
                ...filters,
                qualification: e.target.value,
                page: 1,
              })
            }
          >
            <option value="">Todas qualificações</option>
            <option value="hot">Quente</option>
            <option value="warm">Morno</option>
            <option value="cold">Frio</option>
          </select>
          <select
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            value={filters.status}
            onChange={(e) =>
              setFilters({ ...filters, status: e.target.value, page: 1 })
            }
          >
            <option value="">Todos status</option>
            <option value="new">Novo</option>
            <option value="in_progress">Em Atendimento</option>
            <option value="qualified">Qualificado</option>
            <option value="handed_off">Transferido</option>
            <option value="closed">Fechado</option>
          </select>
        </div>
      </Card>

      {/* Conteúdo principal, dependente da view */}
      <Card>
        <CardHeader title={`${data?.total || 0} leads encontrados`} />
        {loading ? (
          <div className="text-center py-8 text-gray-500">Carregando...</div>
        ) : (
          <>
            {view === 'table' && (
              <LeadsTable
              leads={currentLeads}
              sellers={sellers}
              onAssignSeller={handleAssignSeller}
              onUnassignSeller={handleUnassignSeller}
              onUpdateLead={loadData}
            />
            )}

            {view === 'kanban' && (
              <LeadsKanban
                leads={currentLeads}
                onSelectLead={setSelectedLead}
                onOpenAssignModal={(leadId) => setAssignModalLeadId(leadId)}
              />
            )}

            {view === 'insights' && (
              <div className="p-4">
                <LeadsInsights leads={currentLeads} />
              </div>
            )}

            {data && data.pages > 1 && (
              <div className="flex justify-center gap-2 mt-6">
                {Array.from({ length: data.pages }, (_, i) => i + 1).map(
                  (page) => (
                    <button
                      key={page}
                      onClick={() => setFilters({ ...filters, page })}
                      className={`px-4 py-2 rounded-lg ${
                        filters.page === page
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {page}
                    </button>
                  )
                )}
              </div>
            )}
          </>
        )}
      </Card>

      {/* Quickview lateral (usado principalmente com o kanban) */}
      <LeadsQuickview
        lead={selectedLead}
        onClose={() => setSelectedLead(null)}
        onOpenAssignModal={(leadId) => setAssignModalLeadId(leadId)}
      />

      {/* Modal de atribuição de vendedor (reaproveitado em qualquer view) */}
      <AssignSellerModal
        open={assignModalLeadId !== null}
        leadName={assignModalLead?.name}
        sellers={sellers}
        loading={assignModalLoading}
        onClose={() => setAssignModalLeadId(null)}
        onAssign={handleAssignSellerFromModal}
      />
    </div>
  );
}
