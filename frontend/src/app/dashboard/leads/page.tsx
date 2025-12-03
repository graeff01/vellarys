'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader } from '@/components/ui/card';
import { LeadsTable } from '@/components/dashboard/leads-table';
import { getLeads } from '@/lib/api';
import { getSellers, assignLeadToSeller, unassignLeadFromSeller } from '@/lib/sellers';
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

export default function LeadsPage() {
  const [data, setData] = useState<LeadsResponse | null>(null);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ search: '', qualification: '', status: '', page: 1 });

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
      // Recarrega a lista para atualizar
      await loadData();
    } catch (error) {
      console.error('Erro ao atribuir vendedor:', error);
      alert('Erro ao atribuir vendedor');
    }
  }

  async function handleUnassignSeller(leadId: number) {
    try {
      await unassignLeadFromSeller(leadId);
      // Recarrega a lista para atualizar
      await loadData();
    } catch (error) {
      console.error('Erro ao remover atribuição:', error);
      alert('Erro ao remover atribuição');
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Leads</h1>
        <p className="text-gray-500">Gerencie seus leads</p>
      </div>
      
      <Card>
        <div className="flex flex-wrap gap-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por nome, telefone..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value, page: 1 })}
            />
          </div>
          <select
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            value={filters.qualification}
            onChange={(e) => setFilters({ ...filters, qualification: e.target.value, page: 1 })}
          >
            <option value="">Todas qualificações</option>
            <option value="hot">Quente</option>
            <option value="warm">Morno</option>
            <option value="cold">Frio</option>
          </select>
          <select
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value, page: 1 })}
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
      
      <Card overflow>
        <CardHeader title={`${data?.total || 0} leads encontrados`} />
        {loading ? (
          <div className="text-center py-8 text-gray-500">Carregando...</div>
        ) : (
          <>
            <LeadsTable
              leads={data?.items || []}
              sellers={sellers}
              onAssignSeller={handleAssignSeller}
              onUnassignSeller={handleUnassignSeller}
            />
            {data && data.pages > 1 && (
              <div className="flex justify-center gap-2 mt-6">
                {Array.from({ length: data.pages }, (_, i) => i + 1).map((page) => (
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
                ))}
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}