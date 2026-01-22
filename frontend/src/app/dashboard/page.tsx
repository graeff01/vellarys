'use client';

/**
 * DASHBOARD PAGE - CUSTOMIZÁVEL
 * ==============================
 *
 * Dashboard com sistema de widgets personalizáveis.
 * O gestor pode escolher quais métricas quer ver.
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { CEODashboard } from '@/components/ceo/ceo-dashboard';
import { DashboardCustomizer } from '@/components/dashboard/dashboard-customizer';
import { WidgetRenderer } from '@/components/dashboard/widget-renderer';
import { useSalesData } from '@/components/dashboard/sales-widgets';
import {
  getMetrics,
  getLeads,
  getDashboardConfig,
  WidgetConfig,
} from '@/lib/api';
import { getSellers } from '@/lib/sellers';
import { getUser } from '@/lib/auth';
import {
  AlertCircle,
  RefreshCw,
  Settings,
} from 'lucide-react';

// =============================================
// TIPOS
// =============================================

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
  funnel?: {
    total: number;
    engaged: number;
    qualified: number;
    converted: number;
  };
  top_topics?: { topic: string; count: number }[];
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

// =============================================
// ERROR STATE
// =============================================

function ErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] space-y-4">
      <div className="p-4 bg-rose-50 rounded-2xl border border-rose-100 shadow-lg">
        <AlertCircle className="w-10 h-10 text-rose-600" />
      </div>
      <div className="text-center max-w-sm">
        <h3 className="text-lg font-extrabold text-slate-900 mb-2">
          Houve um contratempo
        </h3>
        <p className="text-sm text-slate-500 font-medium mb-4">{error}</p>
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-6 py-2.5 bg-slate-900 text-white rounded-xl font-bold shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all mx-auto"
        >
          <RefreshCw className="w-4 h-4" />
          Tentar Novamente
        </button>
      </div>
    </div>
  );
}

// =============================================
// LOADING STATE
// =============================================

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] gap-3">
      <div className="w-10 h-10 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin"></div>
      <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px]">Sincronizando Dashboard...</p>
    </div>
  );
}

// =============================================
// GESTOR DASHBOARD (CUSTOMIZÁVEL)
// =============================================

function GestorDashboard() {
  const router = useRouter();

  // Estados de dados
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estados de configuração
  const [widgets, setWidgets] = useState<WidgetConfig[]>([]);
  const [configLoading, setConfigLoading] = useState(true);
  const [customizerOpen, setCustomizerOpen] = useState(false);

  // Hook de dados de vendas
  const salesData = useSalesData();

  // Carrega configuração do dashboard
  const loadConfig = useCallback(async () => {
    try {
      setConfigLoading(true);
      const config = await getDashboardConfig();
      setWidgets(config.widgets);
    } catch (err) {
      console.error('Erro carregando config:', err);
      // Usa widgets padrão se falhar
      setWidgets([]);
    } finally {
      setConfigLoading(false);
    }
  }, []);

  // Carrega dados do dashboard
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [metricsData, leadsData, sellersData] = await Promise.all([
        getMetrics(),
        getLeads({ page: 1 }),
        getSellers(),
      ]);

      if (!metricsData) throw new Error('Métricas não disponíveis');

      setMetrics(metricsData as Metrics);
      setLeads((leadsData as { items: Lead[] }).items || []);
      setSellers((sellersData as { sellers: Seller[] }).sellers || []);
    } catch (err: unknown) {
      console.error('Erro dashboard:', err);
      const errorMessage = err instanceof Error ? err.message : 'Erro ao carregar dados';

      if (errorMessage.includes('401')) {
        setError('Sessão expirada. Redirecionando...');
        setTimeout(() => router.push('/login'), 2000);
      } else {
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  }, [router]);

  // Carrega tudo ao montar
  useEffect(() => {
    loadConfig();
    loadData();
  }, [loadConfig, loadData]);

  // Callbacks
  const handleSaveConfig = (newWidgets: WidgetConfig[]) => {
    setWidgets(newWidgets);
  };

  // Estados de loading
  if (loading || configLoading) {
    return <LoadingState />;
  }

  if (error) {
    return <ErrorState error={error} onRetry={loadData} />;
  }

  if (!metrics) return null;

  // Filtra e ordena widgets ativos
  const activeWidgets = widgets
    .filter(w => w.enabled)
    .sort((a, b) => a.position - b.position);

  return (
    <div className="space-y-3 animate-in fade-in duration-700">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">Visão Geral</h1>
          <p className="text-sm text-slate-500 font-medium">Análise estratégica de desempenho do Velaris AI</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Botão Personalizar */}
          <button
            onClick={() => setCustomizerOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-600 hover:bg-slate-50 hover:border-slate-300 transition-all shadow-sm"
          >
            <Settings className="w-4 h-4" />
            <span className="hidden sm:inline">Personalizar</span>
          </button>

          {/* Status */}
          <div className="bg-white border border-slate-200 rounded-xl px-3 py-1.5 shadow-sm flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">Sistema Operante</span>
          </div>
        </div>
      </div>

      {/* Grid de Widgets */}
      <div className="grid grid-cols-12 gap-3">
        {activeWidgets.map(widget => (
          <WidgetRenderer
            key={widget.id}
            config={widget}
            metrics={metrics}
            leads={leads}
            sellers={sellers}
            salesData={{
              goal: salesData.goal,
              metrics: salesData.metrics,
              reload: salesData.reload,
            }}
          />
        ))}
      </div>

      {/* Mensagem se não tiver widgets */}
      {activeWidgets.length === 0 && (
        <div className="text-center py-12 bg-slate-50 rounded-2xl border border-slate-200">
          <Settings className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-slate-700 mb-2">Dashboard Vazio</h3>
          <p className="text-sm text-slate-500 mb-4">Adicione widgets para personalizar sua visão geral</p>
          <button
            onClick={() => setCustomizerOpen(true)}
            className="px-6 py-2 bg-indigo-600 text-white rounded-xl font-bold text-sm hover:bg-indigo-700 transition-colors"
          >
            Personalizar Dashboard
          </button>
        </div>
      )}

      {/* Modal de Personalização */}
      <DashboardCustomizer
        isOpen={customizerOpen}
        onClose={() => setCustomizerOpen(false)}
        widgets={widgets}
        onSave={handleSaveConfig}
      />
    </div>
  );
}

// =============================================
// PÁGINA PRINCIPAL
// =============================================

export default function DashboardPage() {
  const [userRole, setUserRole] = useState<string | undefined>(undefined);

  useEffect(() => {
    const user = getUser();
    setUserRole(user?.role || 'guest');
  }, []);

  if (userRole === undefined) return null;

  const isSuperAdmin = userRole === 'superadmin';

  return (
    <div className="p-3 md:p-4 lg:p-5 max-w-screen-2xl mx-auto">
      {isSuperAdmin ? <CEODashboard /> : <GestorDashboard />}
    </div>
  );
}
