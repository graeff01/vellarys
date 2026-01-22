'use client';

/**
 * WIDGET REGISTRY
 * ================
 *
 * Define todos os widgets disponíveis para o dashboard customizável.
 * Cada widget tem:
 * - Metadata (nome, descrição, categoria, ícone)
 * - Componente de renderização
 * - Tamanhos permitidos
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
  LucideIcon,
} from 'lucide-react';

// Tipos
export type WidgetSize = 'full' | 'two_thirds' | 'half' | 'third';

export interface WidgetMeta {
  id: string;
  name: string;
  description: string;
  category: 'metricas' | 'vendas' | 'alertas' | 'sistema';
  icon: LucideIcon;
  defaultSize: WidgetSize;
  allowedSizes: WidgetSize[];
}

// Mapeamento de categorias para labels
export const CATEGORY_LABELS: Record<string, string> = {
  alertas: '🔔 Alertas',
  metricas: '📊 Métricas Gerais',
  vendas: '💰 Métricas de Vendas',
  sistema: '⚙️ Sistema',
};

// Ordem de categorias
export const CATEGORY_ORDER = ['alertas', 'metricas', 'vendas', 'sistema'];

// Registry de widgets
export const WIDGET_REGISTRY: Record<string, WidgetMeta> = {
  // === ALERTAS ===
  hot_leads_cta: {
    id: 'hot_leads_cta',
    name: 'Alerta Leads Quentes',
    description: 'CTA de destaque para leads quentes aguardando',
    category: 'alertas',
    icon: Flame,
    defaultSize: 'full',
    allowedSizes: ['full'],
  },

  // === MÉTRICAS GERAIS ===
  metrics_cards: {
    id: 'metrics_cards',
    name: 'Métricas Principais',
    description: 'KPIs de atendimento total, leads quentes e transferidos',
    category: 'metricas',
    icon: BarChart3,
    defaultSize: 'full',
    allowedSizes: ['full'],
  },
  qualification_donut: {
    id: 'qualification_donut',
    name: 'Qualificação de Leads',
    description: 'Gráfico de pizza com distribuição quente/morno/frio',
    category: 'metricas',
    icon: PieChart,
    defaultSize: 'third',
    allowedSizes: ['third', 'half'],
  },
  funnel: {
    id: 'funnel',
    name: 'Funil de Atendimento',
    description: 'Visualização do funil de conversão',
    category: 'metricas',
    icon: Filter,
    defaultSize: 'half',
    allowedSizes: ['half', 'full'],
  },
  topics_heatmap: {
    id: 'topics_heatmap',
    name: 'Interesses e Dúvidas',
    description: 'Nuvem de palavras com tópicos mais frequentes',
    category: 'metricas',
    icon: MessageSquare,
    defaultSize: 'half',
    allowedSizes: ['half', 'full'],
  },
  impact_velaris: {
    id: 'impact_velaris',
    name: 'Impacto Velaris IA',
    description: 'ROI, tempo economizado e velocidade de resposta',
    category: 'metricas',
    icon: Sparkles,
    defaultSize: 'two_thirds',
    allowedSizes: ['two_thirds', 'full'],
  },
  leads_table: {
    id: 'leads_table',
    name: 'Leads Recentes',
    description: 'Tabela com últimos leads',
    category: 'metricas',
    icon: Users,
    defaultSize: 'two_thirds',
    allowedSizes: ['two_thirds', 'full'],
  },

  // === SISTEMA ===
  plan_usage: {
    id: 'plan_usage',
    name: 'Uso do Plano',
    description: 'Limites e consumo do plano atual',
    category: 'sistema',
    icon: CreditCard,
    defaultSize: 'third',
    allowedSizes: ['third', 'half'],
  },

  // === VENDAS ===
  sales_goal: {
    id: 'sales_goal',
    name: 'Meta Mensal',
    description: 'Progresso da meta de vendas do mês',
    category: 'vendas',
    icon: Target,
    defaultSize: 'third',
    allowedSizes: ['third', 'half'],
  },
  sales_progress: {
    id: 'sales_progress',
    name: 'Progresso de Vendas',
    description: 'Quanto falta para bater a meta',
    category: 'vendas',
    icon: TrendingUp,
    defaultSize: 'third',
    allowedSizes: ['third', 'half'],
  },
  deals_closed: {
    id: 'deals_closed',
    name: 'Vendas Fechadas',
    description: 'Número de vendas no período',
    category: 'vendas',
    icon: CheckCircle,
    defaultSize: 'third',
    allowedSizes: ['third', 'half'],
  },
  average_ticket: {
    id: 'average_ticket',
    name: 'Ticket Médio',
    description: 'Valor médio das vendas',
    category: 'vendas',
    icon: DollarSign,
    defaultSize: 'third',
    allowedSizes: ['third', 'half'],
  },
  month_projection: {
    id: 'month_projection',
    name: 'Projeção do Mês',
    description: 'Estimativa de fechamento baseada na velocidade atual',
    category: 'vendas',
    icon: TrendingUp,
    defaultSize: 'third',
    allowedSizes: ['third', 'half'],
  },
  seller_ranking: {
    id: 'seller_ranking',
    name: 'Ranking de Vendedores',
    description: 'Top vendedores por conversão ou vendas',
    category: 'vendas',
    icon: Trophy,
    defaultSize: 'half',
    allowedSizes: ['half', 'full'],
  },
  days_remaining: {
    id: 'days_remaining',
    name: 'Dias Restantes',
    description: 'Urgência visual de dias até fim do mês',
    category: 'vendas',
    icon: Calendar,
    defaultSize: 'third',
    allowedSizes: ['third'],
  },
  conversion_rate: {
    id: 'conversion_rate',
    name: 'Taxa de Conversão',
    description: 'Percentual de leads convertidos em vendas',
    category: 'vendas',
    icon: Percent,
    defaultSize: 'third',
    allowedSizes: ['third', 'half'],
  },
};

// Helper para obter widgets por categoria
export function getWidgetsByCategory(): Record<string, WidgetMeta[]> {
  const byCategory: Record<string, WidgetMeta[]> = {};

  Object.values(WIDGET_REGISTRY).forEach(widget => {
    if (!byCategory[widget.category]) {
      byCategory[widget.category] = [];
    }
    byCategory[widget.category].push(widget);
  });

  return byCategory;
}

// Helper para obter widget por ID
export function getWidgetMeta(id: string): WidgetMeta | undefined {
  return WIDGET_REGISTRY[id];
}

// Helper para converter size para classes Tailwind
export function getSizeClasses(size: WidgetSize): string {
  switch (size) {
    case 'full':
      return 'col-span-12';
    case 'two_thirds':
      return 'col-span-12 lg:col-span-8';
    case 'half':
      return 'col-span-12 lg:col-span-6';
    case 'third':
      return 'col-span-12 md:col-span-6 lg:col-span-4';
    default:
      return 'col-span-12';
  }
}

// Helper para labels de tamanho
export const SIZE_LABELS: Record<WidgetSize, string> = {
  full: 'Largura Total',
  two_thirds: '2/3 da Largura',
  half: 'Metade',
  third: '1/3 da Largura',
};
