'use client';

/**
 * LEAD PAGE WIDGET REGISTRY
 * ==========================
 *
 * Define todos os widgets disponíveis para a página de detalhes do lead.
 * Usa o mesmo sistema de grid customizável do dashboard.
 */

import {
  User,
  UserCheck,
  Sparkles,
  Briefcase,
  History,
  FileText,
  MessageSquare,
  LucideIcon,
} from 'lucide-react';

// =============================================
// TIPOS
// =============================================

export type LeadWidgetCategory = 'info' | 'vendas' | 'historico' | 'comunicacao';

export interface LeadWidgetMeta {
  id: string;
  name: string;
  description: string;
  category: LeadWidgetCategory;
  icon: LucideIcon;
  grid: {
    w: number;
    h: number;
    minW: number;
    maxW: number;
    minH: number;
    maxH: number;
  };
  previewBg?: string;
}

// =============================================
// CONFIGURAÇÕES
// =============================================

export const CATEGORY_LABELS: Record<LeadWidgetCategory, string> = {
  info: 'Informações',
  vendas: 'Vendas',
  historico: 'Histórico',
  comunicacao: 'Comunicação',
};

export const CATEGORY_COLORS: Record<LeadWidgetCategory, { bg: string; border: string; text: string }> = {
  info: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700' },
  vendas: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700' },
  historico: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700' },
  comunicacao: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700' },
};

// Limites livres para todos os widgets
const FREE_SIZE_LIMITS = { minW: 2, maxW: 12, minH: 1, maxH: 8 };

// =============================================
// REGISTRY DE WIDGETS
// =============================================

export const LEAD_WIDGET_REGISTRY: Record<string, LeadWidgetMeta> = {
  // === INFO ===
  lead_contact: {
    id: 'lead_contact',
    name: 'Contato',
    description: 'Informações de contato do lead',
    category: 'info',
    icon: User,
    previewBg: 'bg-gradient-to-br from-blue-500 to-indigo-600',
    grid: { w: 4, h: 2, ...FREE_SIZE_LIMITS },
  },

  lead_seller: {
    id: 'lead_seller',
    name: 'Vendedor',
    description: 'Vendedor atribuído ao lead',
    category: 'info',
    icon: UserCheck,
    previewBg: 'bg-gradient-to-br from-emerald-500 to-green-600',
    grid: { w: 4, h: 2, ...FREE_SIZE_LIMITS },
  },

  lead_insights: {
    id: 'lead_insights',
    name: 'IA Insights',
    description: 'Resumo e insights gerados pela IA',
    category: 'info',
    icon: Sparkles,
    previewBg: 'bg-gradient-to-br from-violet-500 to-purple-600',
    grid: { w: 4, h: 2, ...FREE_SIZE_LIMITS },
  },

  // === VENDAS ===
  lead_opportunities: {
    id: 'lead_opportunities',
    name: 'Oportunidades',
    description: 'Negócios/oportunidades do lead',
    category: 'vendas',
    icon: Briefcase,
    previewBg: 'bg-gradient-to-br from-teal-500 to-cyan-600',
    grid: { w: 4, h: 4, ...FREE_SIZE_LIMITS, minH: 2 },
  },

  // === HISTÓRICO ===
  lead_timeline: {
    id: 'lead_timeline',
    name: 'Timeline',
    description: 'Histórico de eventos do lead',
    category: 'historico',
    icon: History,
    previewBg: 'bg-gradient-to-br from-amber-500 to-orange-600',
    grid: { w: 4, h: 3, ...FREE_SIZE_LIMITS, minH: 2 },
  },

  lead_notes: {
    id: 'lead_notes',
    name: 'Notas',
    description: 'Notas e anotações do lead',
    category: 'historico',
    icon: FileText,
    previewBg: 'bg-gradient-to-br from-cyan-500 to-blue-600',
    grid: { w: 4, h: 3, ...FREE_SIZE_LIMITS, minH: 2 },
  },

  // === COMUNICAÇÃO ===
  lead_chat: {
    id: 'lead_chat',
    name: 'Conversas',
    description: 'Chat/mensagens com o lead',
    category: 'comunicacao',
    icon: MessageSquare,
    previewBg: 'bg-gradient-to-br from-indigo-500 to-blue-600',
    grid: { w: 4, h: 10, ...FREE_SIZE_LIMITS, minH: 4, minW: 3 },
  },
};

// =============================================
// HELPERS
// =============================================

export function getLeadWidgetsByCategory(): Record<LeadWidgetCategory, LeadWidgetMeta[]> {
  const byCategory: Record<string, LeadWidgetMeta[]> = {};

  Object.values(LEAD_WIDGET_REGISTRY).forEach(widget => {
    if (!byCategory[widget.category]) {
      byCategory[widget.category] = [];
    }
    byCategory[widget.category].push(widget);
  });

  return byCategory as Record<LeadWidgetCategory, LeadWidgetMeta[]>;
}

export function getLeadWidgetMeta(id: string): LeadWidgetMeta | undefined {
  return LEAD_WIDGET_REGISTRY[id];
}

export function getAllLeadWidgets(): LeadWidgetMeta[] {
  return Object.values(LEAD_WIDGET_REGISTRY);
}

export function createLeadWidgetGridConfig(widgetId: string, existingWidgets: { y: number; h: number }[]) {
  const meta = getLeadWidgetMeta(widgetId);
  if (!meta) return null;

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

export function getDefaultLeadPageLayout() {
  return [
    { i: 'lead_contact_default', type: 'lead_contact', x: 0, y: 0, w: 4, h: 2, ...FREE_SIZE_LIMITS },
    { i: 'lead_seller_default', type: 'lead_seller', x: 0, y: 2, w: 4, h: 2, ...FREE_SIZE_LIMITS },
    { i: 'lead_insights_default', type: 'lead_insights', x: 0, y: 4, w: 4, h: 2, ...FREE_SIZE_LIMITS },
    { i: 'lead_opportunities_default', type: 'lead_opportunities', x: 4, y: 0, w: 4, h: 4, ...FREE_SIZE_LIMITS, minH: 2 },
    { i: 'lead_timeline_default', type: 'lead_timeline', x: 4, y: 4, w: 4, h: 3, ...FREE_SIZE_LIMITS, minH: 2 },
    { i: 'lead_notes_default', type: 'lead_notes', x: 4, y: 7, w: 4, h: 3, ...FREE_SIZE_LIMITS, minH: 2 },
    { i: 'lead_chat_default', type: 'lead_chat', x: 8, y: 0, w: 4, h: 10, ...FREE_SIZE_LIMITS, minH: 4, minW: 3 },
  ];
}
