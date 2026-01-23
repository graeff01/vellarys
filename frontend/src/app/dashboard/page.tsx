'use client';

/**
 * DASHBOARD PAGE - DRAG & DROP
 * ============================
 *
 * Dashboard com sistema de widgets drag-and-drop inspirado no Monday.com.
 * Features:
 * - Arrastar widgets para reposicionar
 * - Redimensionar widgets nos cantos/bordas
 * - Catálogo visual para adicionar novos widgets
 * - Layout responsivo com breakpoints
 * - Auto-save de configurações
 */

import { useEffect, useState, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { CEODashboard } from '@/components/ceo/ceo-dashboard';
import { WidgetCatalog } from '@/components/dashboard/widget-catalog';
import { WidgetRenderer } from '@/components/dashboard/widget-renderer';
import { useSalesData } from '@/components/dashboard/sales-widgets';
import {
  getDefaultLayout,
  createWidgetGridConfig,
  getWidgetMeta,
} from '@/components/dashboard/widget-registry';
import type { GridWidget } from '@/components/dashboard/draggable-grid';
import {
  getMetrics,
  getLeads,
  getDashboardConfig,
  updateDashboardConfig,
} from '@/lib/api';
import { getSellers } from '@/lib/sellers';
import { getUser } from '@/lib/auth';
import {
  AlertCircle,
  RefreshCw,
  Zap,
} from 'lucide-react';

// Import dinâmico do DraggableGrid (client-only por causa do react-grid-layout)
const DraggableGrid = dynamic(
  () => import('@/components/dashboard/draggable-grid'),
  { ssr: false }
);

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
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
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
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-slate-200 rounded-full"></div>
        <div className="absolute top-0 left-0 w-16 h-16 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
      <div className="text-center">
        <p className="text-slate-700 font-bold">Carregando Dashboard</p>
        <p className="text-slate-400 text-sm">Sincronizando dados...</p>
      </div>
    </div>
  );
}

// =============================================
// GESTOR DASHBOARD (DRAG & DROP)
// =============================================

function GestorDashboard() {
  const router = useRouter();

  // Estados de dados
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estados de configuração do grid
  const [widgets, setWidgets] = useState<GridWidget[]>([]);
  const [originalWidgets, setOriginalWidgets] = useState<GridWidget[]>([]);
  const [configLoading, setConfigLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [saving, setSaving] = useState(false);
  const [catalogOpen, setCatalogOpen] = useState(false);

  // Hook de dados de vendas
  const salesData = useSalesData();

  // Detecta mudanças não salvas
  const hasChanges = useMemo(() => {
    return JSON.stringify(widgets) !== JSON.stringify(originalWidgets);
  }, [widgets, originalWidgets]);

  // Lista de tipos de widgets existentes
  const existingWidgetTypes = useMemo(() => {
    return widgets.map(w => w.type);
  }, [widgets]);

  // Carrega configuração do dashboard
  const loadConfig = useCallback(async () => {
    try {
      setConfigLoading(true);
      const config = await getDashboardConfig();

      // VALIDAÇÃO: Filtra widgets que não pertencem a este dashboard
      // Isso corrige o problema onde widgets da página de leads (lead_*) aparecem aqui
      const validWidgets = (config.widgets || []).filter((w: any) => {
        return !!getWidgetMeta(w.type);
      });

      // Se após filtrar não sobrar nada (ou se o config original estava vazio), usa o default
      if (!validWidgets || validWidgets.length === 0) {
        const defaultLayout = getDefaultLayout();
        setWidgets(defaultLayout);
        setOriginalWidgets(defaultLayout);
        setConfigLoading(false);
        return;
      }

      // Converte formato antigo para novo (se necessário)
      let gridWidgets: GridWidget[];

      // Verifica se já está no formato novo (tem propriedade 'i')
      const firstWidget = validWidgets[0] as any;
      if (firstWidget.i && firstWidget.x !== undefined) {
        gridWidgets = (validWidgets as unknown as GridWidget[]).map(w => ({
          ...w,
          minW: 1,
          maxW: 12,
          minH: 1,
          maxH: 100
        }));
      } else {
        // Converte formato antigo
        gridWidgets = validWidgets.map((w: any, index: number) => {
          const meta = getWidgetMeta(w.type);
          return {
            i: w.id || `${w.type}_${index}`,
            type: w.type,
            x: 0,
            y: index * 2,
            w: meta?.grid.w || 6,
            h: meta?.grid.h || 2,
            minW: meta?.grid.minW || 1,
            maxW: meta?.grid.maxW || 12,
            minH: meta?.grid.minH || 1,
            maxH: meta?.grid.maxH || 100,
          };
        });
      }

      setWidgets(gridWidgets);
      setOriginalWidgets(gridWidgets);
    } catch (err) {
      console.error('Erro carregando config:', err);
      // Usa layout padrão se falhar
      const defaultLayout = getDefaultLayout();
      setWidgets(defaultLayout);
      setOriginalWidgets(defaultLayout);
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

  // Handlers
  const handleLayoutChange = useCallback((newWidgets: GridWidget[]) => {
    setWidgets(newWidgets);
  }, []);

  const handleRemoveWidget = useCallback((widgetId: string) => {
    setWidgets(prev => prev.filter(w => w.i !== widgetId));
  }, []);

  const handleAddWidget = useCallback((widgetId: string) => {
    const newWidget = createWidgetGridConfig(widgetId, widgets);
    if (newWidget) {
      setWidgets(prev => [...prev, newWidget as GridWidget]);
    }
    setCatalogOpen(false);
  }, [widgets]);

  const handleSave = useCallback(async () => {
    try {
      setSaving(true);

      // Converte para formato da API
      const widgetsForApi = widgets.map((w, index) => ({
        id: w.i,
        type: w.type,
        enabled: true,
        position: index,
        size: 'full', // Mantém compatibilidade
        settings: {
          gridX: w.x,
          gridY: w.y,
          gridW: w.w,
          gridH: w.h,
        },
        // Dados do novo formato
        i: w.i,
        x: w.x,
        y: w.y,
        w: w.w,
        h: w.h,
        minW: w.minW,
        maxW: w.maxW,
        minH: w.minH,
        maxH: w.maxH,
      }));

      await updateDashboardConfig(widgetsForApi, {}, 'v2');
      setOriginalWidgets(widgets);
      setEditMode(false);
    } catch (err) {
      console.error('Erro salvando:', err);
    } finally {
      setSaving(false);
    }
  }, [widgets]);

  const handleReset = useCallback(() => {
    const defaultLayout = getDefaultLayout();
    setWidgets(defaultLayout);
  }, []);

  const handleToggleEditMode = useCallback(() => {
    if (editMode && hasChanges) {
      // Se está saindo do modo edição com mudanças, pergunta se quer salvar
      if (confirm('Você tem alterações não salvas. Deseja salvar?')) {
        handleSave();
      } else {
        setWidgets(originalWidgets);
      }
    }
    setEditMode(!editMode);
  }, [editMode, hasChanges, handleSave, originalWidgets]);

  // Renderiza widget
  const renderWidget = useCallback((widget: GridWidget) => {
    if (!metrics) return null;

    return (
      <WidgetRenderer
        config={{
          id: widget.i,
          type: widget.type,
          enabled: true,
          position: 0,
          size: 'full',
          settings: {},
        }}
        metrics={metrics}
        leads={leads}
        sellers={sellers}
        salesData={{
          goal: salesData.goal,
          metrics: salesData.metrics,
          reload: salesData.reload,
        }}
        isGridMode={true}
      />
    );
  }, [metrics, leads, sellers, salesData]);

  // Estados de loading
  if (loading || configLoading) {
    return <LoadingState />;
  }

  if (error) {
    return <ErrorState error={error} onRetry={loadData} />;
  }

  if (!metrics) return null;

  return (
    <div className="space-y-4 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-3">
            Visão Geral
            <span className="px-2 py-1 bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-[10px] font-bold rounded-lg uppercase tracking-wider shadow-lg">
              Drag & Drop
            </span>
          </h1>
          <p className="text-sm text-slate-500 font-medium mt-1">
            {editMode
              ? '🎨 Arraste e redimensione os widgets para personalizar'
              : 'Análise estratégica de desempenho do Velaris AI'}
          </p>
        </div>

        {/* Status Badge */}
        <div className="flex items-center gap-2">
          <div className="bg-white border border-slate-200 rounded-xl px-3 py-1.5 shadow-sm flex items-center gap-2">
            <Zap className="w-4 h-4 text-emerald-500" />
            <span className="text-xs font-bold text-slate-600">Sistema Operante</span>
          </div>
        </div>
      </div>

      {/* Grid de Widgets */}
      <DraggableGrid
        widgets={widgets}
        onLayoutChange={handleLayoutChange}
        onRemoveWidget={handleRemoveWidget}
        onAddWidget={() => setCatalogOpen(true)}
        renderWidget={renderWidget}
        editMode={editMode}
        onToggleEditMode={handleToggleEditMode}
        onSave={handleSave}
        onReset={handleReset}
        hasChanges={hasChanges}
        saving={saving}
      />

      {/* Catálogo de Widgets */}
      <WidgetCatalog
        isOpen={catalogOpen}
        onClose={() => setCatalogOpen(false)}
        onAddWidget={handleAddWidget}
        existingWidgetTypes={existingWidgetTypes}
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
    <div className="p-3 md:p-4 lg:p-6 max-w-screen-2xl mx-auto">
      {isSuperAdmin ? <CEODashboard /> : <GestorDashboard />}
    </div>
  );
}
