'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader } from '@/components/ui/card';
import { MetricsCards } from '@/components/dashboard/metrics-cards';
import { QualificationDonut } from '@/components/dashboard/qualification-donut';
import { ROICard } from '@/components/dashboard/roi-card';
import { LeadsTable } from '@/components/dashboard/leads-table';
import { PlanUsageCard } from '@/components/dashboard/plan-usage-card';
import { CEODashboard } from '@/components/ceo/ceo-dashboard';
import { getMetrics, getLeads } from '@/lib/api';
import { getSellers } from '@/lib/sellers';
import { getUser } from '@/lib/auth';
import {
  Flame,
  TrendingUp,
  Clock,
  DollarSign,
  Moon,
  Zap,
  ArrowRight,
  AlertCircle,
  RefreshCw
} from 'lucide-react';

interface TimeSaved {
  hours_saved: number;
  cost_saved_brl: number;
  leads_handled: number;
}

interface Metrics {
  total_leads: number;
  leads_today: number;
  leads_this_week: number;
  leads_this_month: number;
  conversion_rate: number;
  avg_qualification_time_hours: number;
  avg_response_time_minutes: number;
  engagement_rate: number;
  by_qualification: Record<string, number>;
  by_status: Record<string, number>;
  time_saved: TimeSaved;
  after_hours_leads: number;
  growth_percentage: number;
  hot_leads_waiting: number;
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

// =============================================================================
// COMPONENTE DE ERRO
// =============================================================================

function ErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 space-y-4">
      <div className="p-4 bg-red-50 rounded-full">
        <AlertCircle className="w-12 h-12 text-red-600" />
      </div>
      <div className="text-center">
        <h3 className="text-xl font-semibold text-gray-900 mb-2">
          Erro ao carregar dashboard
        </h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors mx-auto"
        >
          <RefreshCw className="w-5 h-5" />
          Tentar Novamente
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// DASHBOARD DO GESTOR (cliente normal)
// =============================================================================

function GestorDashboard() {
  const router = useRouter();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [metricsData, leadsData, sellersData] = await Promise.all([
        getMetrics(),
        getLeads({ page: 1 }),
        getSellers(),
      ]);

      // ✅ VALIDAÇÃO: Verifica se dados vieram corretamente
      if (!metricsData) {
        throw new Error('Métricas não disponíveis');
      }

      setMetrics(metricsData as Metrics);
      setLeads((leadsData as { items: Lead[] }).items || []);
      setSellers((sellersData as any).sellers || []);
      setRetryCount(0); // Reset retry count on success
    } catch (err: any) {
      console.error('❌ Erro ao carregar dashboard:', err);
      
      // Mensagens de erro específicas
      if (err.message?.includes('401') || err.message?.includes('Unauthorized')) {
        setError('Sessão expirada. Faça login novamente.');
        setTimeout(() => router.push('/login'), 2000);
      } else if (err.message?.includes('Failed to fetch')) {
        setError('Sem conexão com servidor. Verifique sua internet.');
      } else {
        setError(err.message || 'Erro desconhecido. Tente novamente.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // ✅ RETRY AUTOMÁTICO (após 3 segundos, máximo 3 tentativas)
  useEffect(() => {
    if (error && retryCount < 3) {
      const timer = setTimeout(() => {
        console.log(`🔄 Tentativa ${retryCount + 1}/3 de reconexão...`);
        setRetryCount(prev => prev + 1);
        loadData();
      }, 3000);
      
      return () => clearTimeout(timer);
    }
  }, [error, retryCount]);

  // Estados de loading e erro
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <div className="text-gray-500">Carregando dashboard...</div>
          {retryCount > 0 && (
            <div className="text-sm text-gray-400">
              Tentativa {retryCount}/3
            </div>
          )}
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} onRetry={loadData} />;
  }

  if (!metrics) {
    return <ErrorState error="Nenhum dado disponível" onRetry={loadData} />;
  }

  // ✅ VALORES SEGUROS (com fallbacks)
  const leadsHot = metrics.by_qualification?.quente || 0;
  const leadsCold = metrics.by_qualification?.frio || 0;
  const timeSaved = metrics.time_saved || { hours_saved: 0, cost_saved_brl: 0, leads_handled: 0 };
  const afterHoursLeads = metrics.after_hours_leads || 0;
  const growthPercentage = metrics.growth_percentage || 0;
  const hotLeadsWaiting = metrics.hot_leads_waiting || 0;
  const avgResponseTime = metrics.avg_response_time_minutes || 0;
  const engagementRate = metrics.engagement_rate || 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Acompanhe o desempenho da sua IA de atendimento</p>
      </div>

      {/* Cards principais */}
      <MetricsCards metrics={metrics} />

      {/* CARDS DE VALOR AGREGADO */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

        {/* 1. Economia de Tempo */}
        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-gradient-to-br from-green-100 to-emerald-100 rounded-xl">
                <Clock className="w-6 h-6 text-green-600" />
              </div>
              {growthPercentage > 0 && (
                <div className="flex items-center gap-1 text-green-600 text-sm font-semibold">
                  <TrendingUp className="w-4 h-4" />
                  +{growthPercentage.toFixed(0)}%
                </div>
              )}
            </div>
            <h3 className="text-sm font-medium text-gray-600 mb-2">Tempo Economizado</h3>
            <p className="text-3xl font-bold text-gray-900 mb-1">
              {timeSaved.hours_saved.toFixed(1)}h
            </p>
            <p className="text-xs text-gray-500">
              Este mês • {timeSaved.leads_handled} leads atendidos
            </p>
          </div>
        </Card>

        {/* 2. Economia em R$ */}
        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-xl">
                <DollarSign className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <h3 className="text-sm font-medium text-gray-600 mb-2">Economia em Dinheiro</h3>
            <p className="text-3xl font-bold text-blue-600 mb-1">
              R$ {timeSaved.cost_saved_brl.toFixed(0)}
            </p>
            <p className="text-xs text-gray-500">
              vs atendimento humano tradicional
            </p>
          </div>
        </Card>

        {/* 3. Leads Fora do Horário */}
        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-gradient-to-br from-purple-100 to-pink-100 rounded-xl">
                <Moon className="w-6 h-6 text-purple-600" />
              </div>
            </div>
            <h3 className="text-sm font-medium text-gray-600 mb-2">Leads Fora do Horário</h3>
            <p className="text-3xl font-bold text-purple-600 mb-1">
              {afterHoursLeads}
            </p>
            <p className="text-xs text-gray-500">
              Capturados fora do expediente
            </p>
          </div>
        </Card>

        {/* 4. Velocidade de Resposta */}
        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-gradient-to-br from-orange-100 to-red-100 rounded-xl">
                <Zap className="w-6 h-6 text-orange-600" />
              </div>
            </div>
            <h3 className="text-sm font-medium text-gray-600 mb-2">Velocidade de Resposta</h3>
            <p className="text-3xl font-bold text-orange-600 mb-1">
              {avgResponseTime.toFixed(1)}min
            </p>
            <p className="text-xs text-gray-500">
              Resposta instantânea 24/7
            </p>
          </div>
        </Card>
      </div>

      {/* CTA: LEADS QUENTES AGUARDANDO */}
      {hotLeadsWaiting > 0 && (
        <Card className="border-2 border-red-200 bg-gradient-to-r from-red-50 to-orange-50">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-4 bg-red-100 rounded-full animate-pulse">
                  <Flame className="w-8 h-8 text-red-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900 mb-1">
                    {hotLeadsWaiting} Lead{hotLeadsWaiting !== 1 ? 's' : ''} Quente{hotLeadsWaiting !== 1 ? 's' : ''} Aguardando!
                  </h3>
                  <p className="text-gray-600">
                    Esses leads estão prontos para fechar. Entre em contato agora!
                  </p>
                </div>
              </div>
              <button
                onClick={() => router.push('/dashboard/leads?qualification=quente')}
                className="flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition-colors"
              >
                Ver Leads Quentes
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* Seção de destaque - ROI, Qualificação e Uso do Plano */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card de ROI */}
        <ROICard
          totalLeads={metrics.total_leads}
          leadsFiltered={leadsCold}
          leadsHot={leadsHot}
        />

        {/* Card de Qualificação */}
        <Card>
          <CardHeader
            title="Qualificação dos Leads"
            subtitle="Distribuição por temperatura"
          />
          <QualificationDonut data={metrics.by_qualification} />
        </Card>

        {/* Card de Uso do Plano */}
        <PlanUsageCard />
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

// =============================================================================
// PÁGINA PRINCIPAL - DETECTA ROLE
// =============================================================================

export default function DashboardPage() {
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const user = getUser();
    setIsSuperAdmin(user?.role === 'superadmin');
    setLoading(false);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Se for SUPERADMIN, mostra o Dashboard CEO
  if (isSuperAdmin) {
    return <CEODashboard />;
  }

  // Se for gestor normal, mostra o Dashboard padrão
  return <GestorDashboard />;
}