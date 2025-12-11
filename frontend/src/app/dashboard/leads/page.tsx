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

const tabConfig: { id: TabFilter; label: string; icon: React.ElementType; color: string }[] = [
  { id: 'all', label: 'Todos', icon: Users, color: 'text-gray-600' },
  { id: 'pending', label: 'Aguardando', icon: Flame, color: 'text-orange-500' },
  { id: 'in_progress', label: 'Em Atendimento', icon: Clock, color: 'text-blue-500' },
  { id: 'handed_off', label: 'Transferidos', icon: CheckCircle, color: 'text-green-500' },
  { id: 'converted', label: 'Convertidos', icon: CheckCircle, color: 'text-emerald-500' },
  { id: 'lost', label: 'Perdidos', icon: XCircle, color: 'text-red-500' },
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

  // Atualiza filtros baseado na aba ativa
  useEffect(() => {
    switch (activeTab) {
      case 'pending':
        setFilters((prev) => ({ ...prev, status: '', qualification: 'hot', page: 1 }));
        break;
      case 'in_progress':
        setFilters((prev) => ({ ...prev, status: 'in_progress', qualification: '', page: 1 }));
        break;
      case 'handed_off':
        setFilters((prev) => ({ ...prev, status: 'handed_off', qualification: '', page: 1 }));
        break;
      case 'converted':
        setFilters((prev) => ({ ...prev, status: 'converted', qualification: '', page: 1 }));
        break;
      case 'lost':
        setFilters((prev) => ({ ...prev, status: 'lost', qualification: '', page: 1 }));
        break;
      default:
        setFilters((prev) => ({ ...prev, status: '', qualification: '', page: 1 }));
    }
  }, [activeTab]);

  async function loadData() {
    setLoading(true);
    try {
      const params: Record<string, any> = { ...filters };
      
      // Para aba "Aguardando", buscar leads quentes sem vendedor e não transferidos
      if (activeTab === 'pending') {
        params.qualification = 'hot';
        params.unassigned = true;
      }

      const [leadsResponse, sellersResponse] = await Promise.all([
        getLeads(params),
        getSellers(),
      ]);
      
      let items = (leadsResponse as LeadsResponse).items;
      
      // Filtrar localmente para "Aguardando" - leads quentes que não foram transferidos
      if (activeTab === 'pending') {
        items = items.filter(
          (lead) =>
            ['hot', 'quente'].includes(lead.qualification) &&
            lead.status !== 'handed_off' &&
            lead.status !== 'converted' &&
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

  useEffect(() => {
    loadData();
  }, [filters, activeTab]);

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
        // Usa o novo endpoint que faz tudo junto
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
        // Apenas atribui sem handoff
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
    
    // Leads quentes aguardando handoff
    const pending = leads.filter(
      (l) =>
        ['hot', 'quente'].includes(l.qualification) &&
        l.status !== 'handed_off' &&
        l.status !== 'converted' &&
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

      {/* Tabs de Status */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {tabConfig.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          const count =
            tab.id === 'pending'
              ? stats.pending
              : tab.id === 'all'
              ? stats.total
              : null;

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium text-sm whitespace-nowrap transition
                ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-white text-gray-600 hover:bg-gray-50 border'
                }
              `}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-white' : tab.color}`} />
              {tab.label}
              {count !== null && count > 0 && (
                <span
                  className={`
                    px-1.5 py-0.5 rounded-full text-xs font-bold
                    ${
                      isActive
                        ? 'bg-white/20 text-white'
                        : tab.id === 'pending'
                        ? 'bg-orange-100 text-orange-600'
                        : 'bg-gray-100 text-gray-600'
                    }
                  `}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Alerta para leads aguardando */}
      {activeTab === 'pending' && stats.pending > 0 && (
        <div className="flex items-center gap-3 p-4 bg-orange-50 border border-orange-200 rounded-lg">
          <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
            <Flame className="w-5 h-5 text-orange-500" />
          </div>
          <div className="flex-1">
            <p className="font-medium text-orange-800">
              {stats.pending} {stats.pending === 1 ? 'lead quente aguardando' : 'leads quentes aguardando'} atribuição
            </p>
            <p className="text-sm text-orange-600">
              Atribua um vendedor para iniciar o atendimento humano
            </p>
          </div>
        </div>
      )}

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
          
          {activeTab === 'all' && (
            <>
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
                <option value="hot">🔥 Quente</option>
                <option value="warm">🌡️ Morno</option>
                <option value="cold">❄️ Frio</option>
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
                <option value="converted">Convertido</option>
                <option value="lost">Perdido</option>
              </select>
            </>
          )}
        </div>
      </Card>

      {/* Conteúdo principal */}
      <Card>
        <CardHeader 
          title={
            activeTab === 'pending' 
              ? `${stats.pending} leads aguardando atribuição`
              : `${data?.total || 0} leads encontrados`
          } 
        />
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
                onOpenAssignModal={(leadId) => setAssignModalLeadId(leadId)}
                showHandoffButton={activeTab === 'pending'}
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

            {/* Empty State para Aguardando */}
            {activeTab === 'pending' && currentLeads.length === 0 && !loading && (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CheckCircle className="w-8 h-8 text-green-500" />
                </div>
                <p className="text-lg font-medium text-gray-800">Tudo em dia! 🎉</p>
                <p className="text-gray-500 mt-1">
                  Não há leads quentes aguardando atribuição no momento.
                </p>
              </div>
            )}
          </>
        )}
      </Card>

      {/* Quickview lateral */}
      <LeadsQuickview
        lead={selectedLead}
        onClose={() => setSelectedLead(null)}
        onOpenAssignModal={(leadId) => setAssignModalLeadId(leadId)}
      />

      {/* Modal de atribuição melhorado */}
      <AssignSellerModal
        open={assignModalLeadId !== null}
        leadName={assignModalLead?.name}
        leadQualification={assignModalLead?.qualification}
        sellers={sellers}
        loading={assignModalLoading}
        onClose={() => setAssignModalLeadId(null)}
        onAssign={handleAssignWithOptions}
      />
    </div>
  );
}