'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader } from '@/components/ui/card';
import { MetricsCards } from '@/components/dashboard/metrics-cards';
import { QualificationDonut } from '@/components/dashboard/qualification-donut';
import { ROICard } from '@/components/dashboard/roi-card';
import { LeadsTable } from '@/components/dashboard/leads-table';
import { PlanUsageCard } from '@/components/dashboard/plan-usage-card';
import { getMetrics, getLeads } from '@/lib/api';
import { getSellers } from '@/lib/sellers';
import { getUser } from '@/lib/auth';
import { Flame, TrendingUp, Target } from 'lucide-react';

interface Metrics {
  total_leads: number;
  leads_today: number;
  leads_this_week: number;
  leads_this_month: number;
  conversion_rate: number;
  avg_qualification_time_hours: number;
  by_qualification: Record<string, number>;
  by_status: Record<string, number>;
}

interface Lead {
  id: number;
  name: string | null;
  phone: string | null;
  qualification: string;
  status: string;
  created_at: string;
  assigned_seller?: { id: number; name: string; whatsapp: string } | null;
}

interface Seller {
  id: number;
  name: string;
  whatsapp: string;
  available: boolean;
  active: boolean;
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);

  useEffect(() => {
    const user = getUser();
    setIsSuperAdmin(user?.role === 'superadmin');

    async function loadData() {
      try {
        const [metricsData, leadsData, sellersData] = await Promise.all([
          getMetrics(),
          getLeads({ page: 1 }),
          getSellers(),
        ]);
        setMetrics(metricsData as Metrics);
        setLeads((leadsData as { items: Lead[] }).items);
        setSellers((sellersData as any).sellers || []);
      } catch (error) {
        console.error('Erro ao carregar dados:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Carregando...</div>
      </div>
    );
  }

  // Calcula métricas para os cards
  const leadsHot = metrics?.by_qualification?.hot || metrics?.by_qualification?.quente || 0;
  const leadsCold = metrics?.by_qualification?.cold || metrics?.by_qualification?.frio || 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Acompanhe o desempenho da sua IA de atendimento</p>
      </div>

      {/* Cards principais */}
      {metrics && <MetricsCards metrics={metrics} />}

      {/* Seção de destaque - ROI, Qualificação e Uso do Plano */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card de ROI - Ocupa 1 coluna */}
        <ROICard
          totalLeads={metrics?.total_leads || 0}
          leadsFiltered={leadsCold}
          leadsHot={leadsHot}
        />

        {/* Card de Qualificação - Ocupa 1 coluna */}
        <Card>
          <CardHeader 
            title="Qualificação dos Leads" 
            subtitle="Distribuição por temperatura"
          />
          {metrics && <QualificationDonut data={metrics.by_qualification} />}
        </Card>

        {/* Card de Uso do Plano OU Destaques da IA */}
        {!isSuperAdmin ? (
          // Para GESTOR: Mostra o card de uso do plano
          <PlanUsageCard />
        ) : (
          // Para SUPERADMIN: Mostra os destaques (não faz sentido ver "seu plano")
          <Card>
            <CardHeader 
              title="Destaques da IA" 
              subtitle="Performance do atendimento"
            />
            <div className="space-y-4">
              <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-red-50 to-orange-50 rounded-lg border border-red-100">
                <div className="p-3 bg-red-100 rounded-full">
                  <Flame className="w-6 h-6 text-red-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Leads Quentes este mês</p>
                  <p className="text-2xl font-bold text-red-600">{leadsHot}</p>
                </div>
              </div>

              <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border border-green-100">
                <div className="p-3 bg-green-100 rounded-full">
                  <TrendingUp className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Taxa de Qualificação</p>
                  <p className="text-2xl font-bold text-green-600">
                    {metrics?.total_leads ? Math.round((leadsHot / metrics.total_leads) * 100) : 0}%
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-100">
                <div className="p-3 bg-blue-100 rounded-full">
                  <Target className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Leads Atendidos</p>
                  <p className="text-2xl font-bold text-blue-600">{metrics?.total_leads || 0}</p>
                </div>
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Leads Recentes */}
      <Card overflow>
        <CardHeader 
          title="Leads Recentes" 
          subtitle="Últimos leads que entraram em contato"
        />
        <LeadsTable 
          leads={leads.slice(0, 5)} 
          sellers={sellers}
        />
      </Card>
    </div>
  );
}