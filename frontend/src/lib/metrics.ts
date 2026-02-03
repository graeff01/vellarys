/**
 * Metrics Types & API Client
 * ===========================
 *
 * Types e funções para métricas de vendedores e empresa
 */

import { getToken } from './auth';

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== 'undefined' ? getToken() : null;
  const url = `${API_URL}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...options?.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    throw new Error(`API Error: ${response.status}`);
  }

  return response.json();
}

// ============================================================================
// TYPES
// ============================================================================

/**
 * Métricas pessoais do vendedor
 */
export interface SellerMetrics {
  total_leads: number | null;
  active_conversations: number | null;
  total_messages: number | null;
  avg_first_response_time_seconds: number | null;
  conversion_rate: number | null;
  sla_compliance: number | null;
}

/**
 * Métricas consolidadas da empresa (apenas gestor)
 */
export interface CompanyMetrics {
  total_leads: number;
  active_conversations: number;
  total_messages: number;
  avg_first_response_time_seconds: number;
  conversion_rate: number;
  sla_compliance: number;
  total_sellers: number;
  active_sellers: number;
  total_conversions: number;
  revenue_generated: number;
}

/**
 * Item do ranking de vendedores
 */
export interface RankingEntry {
  seller_id: number;
  seller_name: string;
  total_leads: number;
  conversions: number;
  conversion_rate: number;
  avg_response_time_seconds: number;
  sla_compliance: number;
  rank: number;
  is_current_user?: boolean;
}

/**
 * Meta do vendedor
 */
export interface Goal {
  id: number;
  seller_id: number;
  goal_type: 'conversions' | 'leads' | 'sla' | 'response_time' | 'revenue';
  target_value: number;
  current_value: number;
  period: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  start_date: string;
  end_date: string;
  created_by_id: number;
  created_by_name: string;
}

/**
 * Métricas de um vendedor específico (visão do gestor)
 */
export interface SellerAnalytics extends SellerMetrics {
  seller_id: number;
  seller_name: string;
  seller_email: string;
  total_conversions: number;
  revenue_generated: number;
  active_since: string;
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Busca métricas pessoais do vendedor
 */
export async function getSellerMetrics(): Promise<SellerMetrics> {
  return request('/seller/inbox/metrics');
}

/**
 * Busca métricas consolidadas da empresa (apenas gestor)
 */
export async function getCompanyMetrics(): Promise<CompanyMetrics> {
  // TODO: Implementar endpoint no backend
  // Por enquanto, retorna dados mock
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        total_leads: 1247,
        active_conversations: 89,
        total_messages: 5432,
        avg_first_response_time_seconds: 180,
        conversion_rate: 28.5,
        sla_compliance: 87.3,
        total_sellers: 12,
        active_sellers: 8,
        total_conversions: 356,
        revenue_generated: 2847500,
      });
    }, 500);
  });
}

/**
 * Busca ranking de vendedores
 */
export async function getSellerRanking(currentUserId?: number): Promise<RankingEntry[]> {
  // TODO: Implementar endpoint no backend
  // Por enquanto, retorna dados mock
  return new Promise((resolve) => {
    setTimeout(() => {
      const mockData: RankingEntry[] = [
        {
          seller_id: 1,
          seller_name: 'João Silva',
          total_leads: 145,
          conversions: 52,
          conversion_rate: 35.9,
          avg_response_time_seconds: 120,
          sla_compliance: 92.5,
          rank: 1,
        },
        {
          seller_id: 2,
          seller_name: 'Maria Santos',
          total_leads: 132,
          conversions: 45,
          conversion_rate: 34.1,
          avg_response_time_seconds: 135,
          sla_compliance: 89.3,
          rank: 2,
        },
        {
          seller_id: 3,
          seller_name: 'Pedro Costa',
          total_leads: 118,
          conversions: 38,
          conversion_rate: 32.2,
          avg_response_time_seconds: 145,
          sla_compliance: 85.7,
          rank: 3,
        },
        {
          seller_id: 4,
          seller_name: 'Ana Lima',
          total_leads: 95,
          conversions: 28,
          conversion_rate: 29.5,
          avg_response_time_seconds: 160,
          sla_compliance: 82.1,
          rank: 4,
        },
        {
          seller_id: 5,
          seller_name: 'Carlos Oliveira',
          total_leads: 87,
          conversions: 24,
          conversion_rate: 27.6,
          avg_response_time_seconds: 175,
          sla_compliance: 78.9,
          rank: 5,
        },
      ];

      // Marca o usuário atual
      if (currentUserId) {
        mockData.forEach(entry => {
          if (entry.seller_id === currentUserId) {
            entry.is_current_user = true;
          }
        });
      }

      resolve(mockData);
    }, 500);
  });
}

/**
 * Busca metas do vendedor
 */
export async function getSellerGoals(sellerId?: number): Promise<Goal[]> {
  // TODO: Implementar endpoint no backend
  // Por enquanto, retorna dados mock
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve([
        {
          id: 1,
          seller_id: sellerId || 1,
          goal_type: 'conversions',
          target_value: 50,
          current_value: 35,
          period: 'monthly',
          start_date: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString(),
          end_date: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString(),
          created_by_id: 1,
          created_by_name: 'Gestor Principal',
        },
        {
          id: 2,
          seller_id: sellerId || 1,
          goal_type: 'leads',
          target_value: 150,
          current_value: 120,
          period: 'monthly',
          start_date: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString(),
          end_date: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString(),
          created_by_id: 1,
          created_by_name: 'Gestor Principal',
        },
        {
          id: 3,
          seller_id: sellerId || 1,
          goal_type: 'sla',
          target_value: 85,
          current_value: 92,
          period: 'monthly',
          start_date: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString(),
          end_date: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString(),
          created_by_id: 1,
          created_by_name: 'Gestor Principal',
        },
      ]);
    }, 500);
  });
}

/**
 * Busca análise de todos os vendedores (apenas gestor)
 */
export async function getTeamAnalytics(): Promise<SellerAnalytics[]> {
  // TODO: Implementar endpoint no backend
  // Por enquanto, retorna dados mock
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve([
        {
          seller_id: 1,
          seller_name: 'João Silva',
          seller_email: 'joao@example.com',
          total_leads: 145,
          active_conversations: 12,
          total_messages: 823,
          avg_first_response_time_seconds: 120,
          conversion_rate: 35.9,
          sla_compliance: 92.5,
          total_conversions: 52,
          revenue_generated: 487500,
          active_since: '2024-01-15',
        },
        {
          seller_id: 2,
          seller_name: 'Maria Santos',
          seller_email: 'maria@example.com',
          total_leads: 132,
          active_conversations: 10,
          total_messages: 745,
          avg_first_response_time_seconds: 135,
          conversion_rate: 34.1,
          sla_compliance: 89.3,
          total_conversions: 45,
          revenue_generated: 421250,
          active_since: '2024-02-01',
        },
        {
          seller_id: 3,
          seller_name: 'Pedro Costa',
          seller_email: 'pedro@example.com',
          total_leads: 118,
          active_conversations: 9,
          total_messages: 654,
          avg_first_response_time_seconds: 145,
          conversion_rate: 32.2,
          sla_compliance: 85.7,
          total_conversions: 38,
          revenue_generated: 356000,
          active_since: '2024-01-20',
        },
      ]);
    }, 500);
  });
}

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Formata tempo em segundos para legível
 */
export function formatTime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}min`;
  return `${Math.round(seconds / 3600)}h`;
}

/**
 * Formata valor monetário
 */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
}

/**
 * Calcula progresso percentual
 */
export function calculateProgress(current: number, target: number): number {
  if (target === 0) return 0;
  return Math.min(Math.round((current / target) * 100), 100);
}

/**
 * Retorna label do tipo de meta
 */
export function getGoalTypeLabel(type: Goal['goal_type']): string {
  const labels = {
    conversions: 'Conversões',
    leads: 'Leads',
    sla: 'SLA',
    response_time: 'Tempo de Resposta',
    revenue: 'Receita',
  };
  return labels[type] || type;
}

/**
 * Retorna label do período
 */
export function getPeriodLabel(period: Goal['period']): string {
  const labels = {
    daily: 'Diária',
    weekly: 'Semanal',
    monthly: 'Mensal',
    quarterly: 'Trimestral',
  };
  return labels[period] || period;
}
