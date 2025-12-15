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
import { assignAndHandoff } from '@/lib/handoff';
import { Search, Flame, Users, Clock, CheckCircle, XCircle } from 'lucide-react';

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
type TabFilter = 'all' | 'pending' | 'in_progress' | 'handed_off' | 'converted' | 'lost';

const tabConfig: {
  id: TabFilter;
  label: string;
  shortLabel: string;
  icon: React.ElementType;
  color: string;
}[] = [
  { id: 'all', label: 'Todos', shortLabel: 'Todos', icon: Users, color: 'text-gray-600' },
  { id: 'pending', label: 'Aguardando', shortLabel: 'Aguard.', icon: Flame, color: 'text-orange-500' },
  { id: 'in_progress', label: 'Em Atendimento', shortLabel: 'Atend.', icon: Clock, color: 'text-blue-500' },
  { id: 'handed_off', label: 'Transferidos', shortLabel: 'Transf.', icon: CheckCircle, color: 'text-green-500' },
  { id: 'converted', label: 'Convertidos', shortLabel: 'Conv.', icon: CheckCircle, color: 'text-emerald-500' },
  { id: 'lost', label: 'Perdidos', shortLabel: 'Perd.', icon: XCircle, color: 'text-red-500' },
];

export default function LeadsPage() {
  const [data, setData] = useState<LeadsResponse | null>(null);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabFilter>('all');
  const [filters, setFilters] = useState({
    search: '',
    qualification: '',
    status: '',
    page: 1,
  });

  const [view, setView] = useState<ViewMode>('table');
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const [assignModalLeadId, setAssignModalLeadId] = useState<number | null>(null);
  const [assignModalLoading, setAssignModalLoading] = useState(false);

  // CORREÇÃO: Limpa filtros ao trocar de aba
  const handleTabChange = (newTab: TabFilter) => {
    setActiveTab(newTab);
    setFilters({
      search: '',
      qualification: '',
      status: '',
      page: 1,
    });
  };

  async function loadData() {
    setLoading(true);
    try {
      const params: Record<string, any> = {};
      
      // Aplica search se tiver
      if (filters.search) {
        params.search = filters.search;
      }
      
      // Aplica filtros baseado na aba ativa
      switch (activeTab) {
        case 'all':
          // Para "Todos", aplica filtros normais se tiver
          if (filters.qualification) params.qualification = filters.qualification;
          if (filters.status) params.status = filters.status;
          break;
          
        case 'pending':
          // Leads quentes sem vendedor atribuído
          params.unassigned = true;
          break;
          
        case 'in_progress':
          params.status = 'in_progress';
          break;
          
        case 'handed_off':
          params.status = 'handed_off';
          break;
          
        case 'converted':
          params.status = 'converted';
          break;
          
        case 'lost':
          params.status = 'lost';
          break;
      }
      
      params.page = filters.page;

      const [leadsResponse, sellersResponse] = await Promise.all([
        getLeads(params),
        getSellers(),
      ]);
      
      let items = (leadsResponse as LeadsResponse).items;
      
      // Filtro adicional para "Aguardando" - só leads que não foram transferidos/convertidos/perdidos
      if (activeTab === 'pending') {
        items = items.filter(
          (lead) =>
            lead.status !== 'handed_off' &&
            lead.status !== 'converted' &&
            lead.status !== 'lost' &&
            !lead.assigned_seller_id
        );
      }

      setData({
        ...(leadsResponse as LeadsResponse),
        items,
        total: items.length,
      });
      setSellers((sellersResponse as any).sellers || []);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  }

  // Recarrega quando muda activeTab ou filtros
  useEffect(() => {
    loadData();
  }, [activeTab, filters.search, filters.qualification, filters.status, filters.page]);

  // Handler para atribuição simples (sem handoff)
  async function handleAssignSeller(leadId: number, sellerId: number) {
    try {
      await assignLeadToSeller(leadId, sellerId);
      await loadData();
    } catch (error) {
      console.error('Erro ao atribuir vendedor:', error);
      alert('Erro ao atribuir vendedor');
    }
  }

  // Handler para atribuição com opções (handoff + notificação)
  async function handleAssignWithOptions(
    sellerId: number,
    options: { notes: string; notifySeller: boolean; executeHandoff: boolean }
  ) {
    if (!assignModalLeadId) return;
    setAssignModalLoading(true);

    try {
      if (options.executeHandoff) {
        const result = await assignAndHandoff(assignModalLeadId, sellerId, {
          notes: options.notes,
          notifySeller: options.notifySeller,
        });

        if (result.seller_notified) {
          console.log('Vendedor notificado com sucesso!');
        } else if (result.seller_notification_error) {
          console.warn('Erro ao notificar vendedor:', result.seller_notification_error);
          alert(`Lead atribuído, mas houve erro ao notificar: ${result.seller_notification_error}`);
        }
      } else {
        await assignLeadToSeller(assignModalLeadId, sellerId);
      }

      await loadData();
      setAssignModalLeadId(null);
    } catch (error: any) {
      console.error('Erro ao processar atribuição:', error);
      alert(error.message || 'Erro ao processar atribuição');
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
    const total = data?.total || leads.length;
    const hot = leads.filter((l) =>
      ['hot', 'quente'].includes(l.qualification)
    ).length;
    const warm = leads.filter((l) =>
      ['warm', 'morno'].includes(l.qualification)
    ).length;
    const cold = leads.filter((l) =>
      ['cold', 'frio'].includes(l.qualification)
    ).length;
    
    const pending = leads.filter(
      (l) =>
        l.status !== 'handed_off' &&
        l.status !== 'converted' &&
        l.status !== 'lost' &&
        !l.assigned_seller_id
    ).length;

    return { total, hot, warm, cold, pending };
  }, [data]);

  const currentLeads = data?.items || [];

  const assignModalLead =
    assignModalLeadId != null
      ? currentLeads.find((l) => l.id === assignModalLeadId) || null
      : null;

  return (
    <>
      {/* CORREÇÃO: Container principal sem overflow hidden */}
      <div className="min-h-screen bg-gray-50 pb-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-4 sm:space-y-6">
          
          {/* Header + switch de visualização */}
          <div className="flex flex-col gap-3 sm:gap-4 pt-4 sm:pt-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <LeadsHeader
                total={stats.total}
                hot={stats.hot}
                warm={stats.warm}
                cold={stats.cold}
              />
              <LeadsViewSwitch value={view} onChange={setView} />
            </div>
          </div>

          {/* Tabs de Status - CORRIGIDO */}
          <div className="relative -mx-4 sm:mx-0">
            <div className="overflow-x-auto pb-2 px-4 sm:px-0 hide-scrollbar">
              <div className="flex gap-2 min-w-max sm:min-w-0">
                {tabConfig.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;

                  return (
                    <button
                      key={tab.id}
                      onClick={() => handleTabChange(tab.id)}
                      className={`
                        flex flex-col items-center justify-center gap-1.5
                        min-w-[80px] sm:min-w-[90px] px-3 sm:px-4 py-2.5 sm:py-3
                        rounded-xl font-medium transition-all duration-200
                        flex-shrink-0
                        ${
                          isActive
                            ? 'bg-blue-600 text-white shadow-md scale-[1.02]'
                            : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                        }
                      `}
                    >
                      <Icon
                        className={`w-5 h-5 ${
                          isActive ? 'text-white' : tab.color
                        }`}
                      />
                      <span className="text-xs sm:text-sm whitespace-nowrap">
                        {tab.shortLabel}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
            
            {/* Gradient fade nas bordas */}
            <div className="absolute top-0 left-0 w-8 h-full bg-gradient-to-r from-gray-50 to-transparent pointer-events-none sm:hidden" />
            <div className="absolute top-0 right-0 w-8 h-full bg-gradient-to-l from-gray-50 to-transparent pointer-events-none sm:hidden" />
          </div>

          {/* Alerta para leads aguardando */}
          {activeTab === 'pending' && stats.pending > 0 && (
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 p-4 bg-orange-50 border border-orange-200 rounded-lg">
              <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0">
                <Flame className="w-5 h-5 text-orange-500" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-orange-800 text-sm sm:text-base">
                  {stats.pending} {stats.pending === 1 ? 'lead quente aguardando' : 'leads quentes aguardando'} atribuição
                </p>
                <p className="text-xs sm:text-sm text-orange-600 mt-0.5">
                  Atribua um vendedor para iniciar o atendimento humano
                </p>
              </div>
            </div>
          )}

          {/* Filtros */}
          <Card>
            <div className="p-4 space-y-3">
              {/* Search */}
              <div className="relative w-full">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar por nome, telefone..."
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  value={filters.search}
                  onChange={(e) =>
                    setFilters({ ...filters, search: e.target.value, page: 1 })
                  }
                />
              </div>
              
              {/* Selects - só aparecem na aba "Todos" */}
              {activeTab === 'all' && (
                <div className="grid grid-cols-2 sm:flex gap-2 sm:gap-3">
                  <select
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                    value={filters.qualification}
                    onChange={(e) =>
                      setFilters({
                        ...filters,
                        qualification: e.target.value,
                        page: 1,
                      })
                    }
                  >
                    <option value="">Qualificação</option>
                    <option value="hot">🔥 Quente</option>
                    <option value="warm">🌡️ Morno</option>
                    <option value="cold">❄️ Frio</option>
                  </select>
                  <select
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                    value={filters.status}
                    onChange={(e) =>
                      setFilters({ ...filters, status: e.target.value, page: 1 })
                    }
                  >
                    <option value="">Status</option>
                    <option value="new">Novo</option>
                    <option value="in_progress">Em Atendimento</option>
                    <option value="qualified">Qualificado</option>
                    <option value="handed_off">Transferido</option>
                    <option value="converted">Convertido</option>
                    <option value="lost">Perdido</option>
                  </select>
                </div>
              )}
            </div>
          </Card>

          {/* CORREÇÃO: Card sem overflow hidden */}
          <Card className="relative">
            <CardHeader 
              title={
                activeTab === 'pending' 
                  ? `${stats.pending} leads aguardando`
                  : `${data?.total || 0} leads`
              } 
            />
            {loading ? (
              <div className="text-center py-12 text-gray-500">
                <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm">Carregando...</p>
              </div>
            ) : (
              <>
                {view === 'table' && (
                  <div className="overflow-x-auto">
                    <LeadsTable
                      leads={currentLeads}
                      sellers={sellers}
                      onAssignSeller={handleAssignSeller}
                      onUnassignSeller={handleUnassignSeller}
                      onUpdateLead={loadData}
                      onOpenAssignModal={(leadId) => setAssignModalLeadId(leadId)}
                      showHandoffButton={activeTab === 'pending'}
                    />
                  </div>
                )}

                {view === 'kanban' && (
                  <div className="overflow-x-auto pb-4">
                    <LeadsKanban
                      leads={currentLeads}
                      onSelectLead={setSelectedLead}
                      onOpenAssignModal={(leadId) => setAssignModalLeadId(leadId)}
                    />
                  </div>
                )}

                {view === 'insights' && (
                  <div className="p-4">
                    <LeadsInsights leads={currentLeads} />
                  </div>
                )}

                {/* Paginação */}
                {data && data.pages > 1 && (
                  <div className="flex justify-center gap-1 sm:gap-2 mt-6 px-4 pb-4">
                    {Array.from({ length: data.pages }, (_, i) => i + 1).map(
                      (page) => (
                        <button
                          key={page}
                          onClick={() => setFilters({ ...filters, page })}
                          className={`
                            px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-colors
                            ${
                              filters.page === page
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }
                          `}
                        >
                          {page}
                        </button>
                      )
                    )}
                  </div>
                )}

                {/* Empty State */}
                {activeTab === 'pending' && currentLeads.length === 0 && !loading && (
                  <div className="text-center py-12 px-4">
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <CheckCircle className="w-8 h-8 text-green-500" />
                    </div>
                    <p className="text-lg font-medium text-gray-800">Tudo em dia! 🎉</p>
                    <p className="text-gray-500 mt-1 text-sm sm:text-base">
                      Não há leads quentes aguardando atribuição no momento.
                    </p>
                  </div>
                )}
              </>
            )}
          </Card>
        </div>
      </div>

      {/* CORREÇÃO: Modais renderizados FORA do container principal */}
      {/* Quickview lateral */}
      <LeadsQuickview
        lead={selectedLead}
        onClose={() => setSelectedLead(null)}
        onOpenAssignModal={(leadId) => setAssignModalLeadId(leadId)}
      />

      {/* Modal de atribuição - DEVE renderizar com portal */}
      <AssignSellerModal
        open={assignModalLeadId !== null}
        leadName={assignModalLead?.name}
        leadQualification={assignModalLead?.qualification}
        sellers={sellers}
        loading={assignModalLoading}
        onClose={() => setAssignModalLeadId(null)}
        onAssign={handleAssignWithOptions}
      />
    </>
  );
}