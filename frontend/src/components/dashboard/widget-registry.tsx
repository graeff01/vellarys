'use client';

/**
 * WIDGET REGISTRY
 * ================
 *
 * Define todos os widgets disponíveis para o dashboard customizável.
 * Agora com suporte a grid layout (react-grid-layout).
 */

import {
  BarChart3,
  PieChart,
  Filter,
  MessageSquare,
  Sparkles,
  Users,
  CreditCard,
  Flame,
  Target,
  TrendingUp,
  CheckCircle,
  DollarSign,
  Trophy,
  Calendar,
  Percent,
  Zap,
  Activity,
  LucideIcon,
} from 'lucide-react';

// =============================================
// TIPOS
// =============================================

export type WidgetCategory = 'metricas' | 'vendas' | 'alertas' | 'sistema';

export interface GridDimensions {
  // Tamanho padrão
  w: number;           // Largura em colunas (1-12)
  h: number;           // Altura em rows

  // Limites
  minW: number;        // Largura mínima
  maxW: number;        // Largura máxima
  minH: number;        // Altura mínima
  maxH: number;        // Altura máxima
}

export interface WidgetMeta {
  id: string;
  name: string;
  description: string;
  category: WidgetCategory;
  icon: LucideIcon;

  // Configurações de grid
  grid: GridDimensions;

  // Preview image (opcional)
  previewBg?: string;
}

// =============================================
// CONFIGURAÇÕES
// =============================================

// Mapeamento de categorias para labels
export const CATEGORY_LABELS: Record<WidgetCategory, string> = {
  alertas: '🔔 Alertas',
  metricas: '📊 Métricas Gerais',
  vendas: '💰 Métricas de Vendas',
  sistema: '⚙️ Sistema',
};

// Cores por categoria
export const CATEGORY_COLORS: Record<WidgetCategory, { bg: string; border: string; text: string }> = {
  alertas: { bg: 'bg-rose-50', border: 'border-rose-200', text: 'text-rose-700' },
  metricas: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700' },
  vendas: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700' },
  sistema: { bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-700' },
};

// Ordem de categorias
export const CATEGORY_ORDER: WidgetCategory[] = ['alertas', 'vendas', 'metricas', 'sistema'];

// Limites livres para todos os widgets (permite total personalização)
const FREE_SIZE_LIMITS = { minW: 1, maxW: 12, minH: 1, maxH: 100 };

// =============================================
// REGISTRY DE WIDGETS
// =============================================

export const WIDGET_REGISTRY: Record<string, WidgetMeta> = {
  // === ALERTAS ===
  hot_leads_cta: {
    id: 'hot_leads_cta',
    name: 'Alerta Leads Quentes',
    description: 'CTA de destaque quando há leads quentes aguardando atendimento',
    category: 'alertas',
    icon: Flame,
    previewBg: 'bg-gradient-to-r from-rose-500 to-orange-500',
    grid: { w: 12, h: 1, ...FREE_SIZE_LIMITS },
  },

  // === MÉTRICAS GERAIS ===
  metrics_cards: {
    id: 'metrics_cards',
    name: 'KPIs Principais',
    description: 'Cards com métricas de atendimento, leads e transferências',
    category: 'metricas',
    icon: BarChart3,
    previewBg: 'bg-gradient-to-br from-blue-500 to-indigo-600',
    grid: { w: 12, h: 2, ...FREE_SIZE_LIMITS },
  },

  qualification_donut: {
    id: 'qualification_donut',
    name: 'Qualificação de Leads',
    description: 'Gráfico de pizza com distribuição quente/morno/frio',
    category: 'metricas',
    icon: PieChart,
    previewBg: 'bg-gradient-to-br from-violet-500 to-purple-600',
    grid: { w: 4, h: 3, ...FREE_SIZE_LIMITS },
  },

  funnel: {
    id: 'funnel',
    name: 'Funil de Atendimento',
    description: 'Visualização do funil de conversão completo',
    category: 'metricas',
    icon: Filter,
    previewBg: 'bg-gradient-to-br from-cyan-500 to-blue-600',
    grid: { w: 6, h: 3, ...FREE_SIZE_LIMITS },
  },

  topics_heatmap: {
    id: 'topics_heatmap',
    name: 'Interesses e Dúvidas',
    description: 'Tópicos mais frequentes identificados pela IA',
    category: 'metricas',
    icon: MessageSquare,
    previewBg: 'bg-gradient-to-br from-amber-500 to-orange-600',
    grid: { w: 6, h: 3, ...FREE_SIZE_LIMITS },
  },

  impact_velaris: {
    id: 'impact_velaris',
    name: 'Impacto Velaris IA',
    description: 'ROI, tempo economizado e velocidade de resposta',
    category: 'metricas',
    icon: Sparkles,
    previewBg: 'bg-gradient-to-br from-indigo-500 to-purple-600',
    grid: { w: 8, h: 2, ...FREE_SIZE_LIMITS },
  },

  leads_table: {
    id: 'leads_table',
    name: 'Leads Recentes',
    description: 'Tabela com os últimos leads recebidos',
    category: 'metricas',
    icon: Users,
    previewBg: 'bg-gradient-to-br from-slate-600 to-slate-800',
    grid: { w: 8, h: 3, ...FREE_SIZE_LIMITS },
  },

  // === SISTEMA ===
  plan_usage: {
    id: 'plan_usage',
    name: 'Uso do Plano',
    description: 'Consumo de limites e features do plano atual',
    category: 'sistema',
    icon: CreditCard,
    previewBg: 'bg-gradient-to-br from-slate-500 to-slate-700',
    grid: { w: 4, h: 2, ...FREE_SIZE_LIMITS },
  },

  // === VENDAS ===
  sales_goal: {
    id: 'sales_goal',
    name: 'Meta Mensal',
    description: 'Progresso visual da meta de vendas do mês',
    category: 'vendas',
    icon: Target,
    previewBg: 'bg-gradient-to-br from-emerald-500 to-teal-600',
    grid: { w: 4, h: 2, ...FREE_SIZE_LIMITS },
  },

  sales_progress: {
    id: 'sales_progress',
    name: 'Progresso de Vendas',
    description: 'Quanto já vendeu e quanto falta para a meta',
    category: 'vendas',
    icon: TrendingUp,
    previewBg: 'bg-gradient-to-br from-green-500 to-emerald-600',
    grid: { w: 4, h: 2, ...FREE_SIZE_LIMITS },
  },

  deals_closed: {
    id: 'deals_closed',
    name: 'Vendas Fechadas',
    description: 'Contador de vendas fechadas no período',
    category: 'vendas',
    icon: CheckCircle,
    previewBg: 'bg-gradient-to-br from-teal-500 to-cyan-600',
    grid: { w: 3, h: 2, ...FREE_SIZE_LIMITS },
  },

  average_ticket: {
    id: 'average_ticket',
    name: 'Ticket Médio',
    description: 'Valor médio por venda fechada',
    category: 'vendas',
    icon: DollarSign,
    previewBg: 'bg-gradient-to-br from-yellow-500 to-amber-600',
    grid: { w: 3, h: 2, ...FREE_SIZE_LIMITS },
  },

  month_projection: {
    id: 'month_projection',
    name: 'Projeção do Mês',
    description: 'Estimativa de fechamento baseada no ritmo atual',
    category: 'vendas',
    icon: TrendingUp,
    previewBg: 'bg-gradient-to-br from-blue-500 to-indigo-600',
    grid: { w: 4, h: 2, ...FREE_SIZE_LIMITS },
  },

  seller_ranking: {
    id: 'seller_ranking',
    name: 'Ranking de Vendedores',
    description: 'Top vendedores por vendas e conversão',
    category: 'vendas',
    icon: Trophy,
    previewBg: 'bg-gradient-to-br from-amber-500 to-yellow-600',
    grid: { w: 6, h: 3, ...FREE_SIZE_LIMITS },
  },

  days_remaining: {
    id: 'days_remaining',
    name: 'Dias Restantes',
    description: 'Urgência visual dos dias até fim do mês',
    category: 'vendas',
    icon: Calendar,
    previewBg: 'bg-gradient-to-br from-rose-500 to-pink-600',
    grid: { w: 3, h: 2, ...FREE_SIZE_LIMITS },
  },

  conversion_rate: {
    id: 'conversion_rate',
    name: 'Taxa de Conversão',
    description: 'Percentual de leads que se tornaram vendas',
    category: 'vendas',
    icon: Percent,
    previewBg: 'bg-gradient-to-br from-violet-500 to-purple-600',
    grid: { w: 3, h: 2, ...FREE_SIZE_LIMITS },
  },

  revenue_attribution: {
    id: 'revenue_attribution',
    name: 'Mapa de ROI (Canais)',
    description: 'Atribuição de receita por canal de origem',
    category: 'vendas',
    icon: PieChart,
    previewBg: 'bg-gradient-to-br from-indigo-500 to-emerald-600',
    grid: { w: 6, h: 3, ...FREE_SIZE_LIMITS },
  },

  propensity_ranking: {
    id: 'propensity_ranking',
    name: 'Top Oportunidades (IA)',
    description: 'Leads com maior probabilidade de fechamento',
    category: 'vendas',
    icon: Zap,
    previewBg: 'bg-gradient-to-br from-amber-400 to-orange-500',
    grid: { w: 6, h: 3, ...FREE_SIZE_LIMITS },
  },

  sales_pulse: {
    id: 'sales_pulse',
    name: 'Pulse de Atividade',
    description: 'Feed em tempo real das ações de venda',
    category: 'vendas',
    icon: Activity,
    previewBg: 'bg-gradient-to-br from-rose-500 to-indigo-600',
    grid: { w: 6, h: 3, ...FREE_SIZE_LIMITS },
  },
};

// =============================================
// HELPERS
// =============================================

/**
 * Retorna widgets agrupados por categoria
 */
export function getWidgetsByCategory(): Record<WidgetCategory, WidgetMeta[]> {
  const byCategory: Record<string, WidgetMeta[]> = {};

  Object.values(WIDGET_REGISTRY).forEach(widget => {
    if (!byCategory[widget.category]) {
      byCategory[widget.category] = [];
    }
    byCategory[widget.category].push(widget);
  });

  return byCategory as Record<WidgetCategory, WidgetMeta[]>;
}

/**
 * Retorna metadata de um widget pelo ID
 */
export function getWidgetMeta(id: string): WidgetMeta | undefined {
  return WIDGET_REGISTRY[id];
}

/**
 * Retorna todos os widgets como array
 */
export function getAllWidgets(): WidgetMeta[] {
  return Object.values(WIDGET_REGISTRY);
}

/**
 * Gera configurações de grid para um novo widget
 */
export function createWidgetGridConfig(widgetId: string, existingWidgets: { y: number; h: number }[]) {
  const meta = getWidgetMeta(widgetId);
  if (!meta) return null;

  // Calcula Y (posição vertical) baseado nos widgets existentes
  const maxY = existingWidgets.reduce((max, w) => Math.max(max, w.y + w.h), 0);

  return {
    i: `${widgetId}_${Date.now()}`,
    type: widgetId,
    x: 0,
    y: maxY,
    w: meta.grid.w,
    h: meta.grid.h,
    minW: meta.grid.minW,
    maxW: meta.grid.maxW,
    minH: meta.grid.minH,
    maxH: meta.grid.maxH,
  };
}

/**
 * Layout padrão para novos dashboards
 */
export function getDefaultLayout() {
  return [
    { i: 'hot_leads_cta_default', type: 'hot_leads_cta', x: 0, y: 0, w: 12, h: 1, ...FREE_SIZE_LIMITS },
    { i: 'metrics_cards_default', type: 'metrics_cards', x: 0, y: 1, w: 12, h: 2, ...FREE_SIZE_LIMITS },
    { i: 'sales_goal_default', type: 'sales_goal', x: 0, y: 3, w: 4, h: 2, ...FREE_SIZE_LIMITS },
    { i: 'sales_progress_default', type: 'sales_progress', x: 4, y: 3, w: 4, h: 2, ...FREE_SIZE_LIMITS },
    { i: 'days_remaining_default', type: 'days_remaining', x: 8, y: 3, w: 4, h: 2, ...FREE_SIZE_LIMITS },
    { i: 'qualification_donut_default', type: 'qualification_donut', x: 0, y: 5, w: 4, h: 3, ...FREE_SIZE_LIMITS },
    { i: 'funnel_default', type: 'funnel', x: 4, y: 5, w: 8, h: 3, ...FREE_SIZE_LIMITS },
    { i: 'leads_table_default', type: 'leads_table', x: 0, y: 8, w: 8, h: 3, ...FREE_SIZE_LIMITS },
    { i: 'plan_usage_default', type: 'plan_usage', x: 8, y: 8, w: 4, h: 3, ...FREE_SIZE_LIMITS },
  ];
}

// Mantém compatibilidade com código antigo
export type WidgetSize = 'full' | 'two_thirds' | 'half' | 'third';

export function getSizeClasses(size: WidgetSize): string {
  switch (size) {
    case 'full': return 'col-span-12';
    case 'two_thirds': return 'col-span-12 lg:col-span-8';
    case 'half': return 'col-span-12 lg:col-span-6';
    case 'third': return 'col-span-12 md:col-span-6 lg:col-span-4';
    default: return 'col-span-12';
  }
}

export const SIZE_LABELS: Record<WidgetSize, string> = {
  full: 'Largura Total',
  two_thirds: '2/3 da Largura',
  half: 'Metade',
  third: '1/3 da Largura',
};
