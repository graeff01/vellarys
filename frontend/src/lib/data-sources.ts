/**
 * DATA SOURCES API
 * =================
 *
 * Funções para gerenciar fontes de dados configuráveis.
 */

import { getToken } from './auth';

declare const process: any;

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

// =============================================================================
// TIPOS
// =============================================================================

export type DataSourceType = 'portal_api' | 'custom_api' | 'webhook' | 'manual';

export interface DataSource {
  id: number;
  tenant_id: number;
  name: string;
  slug: string;
  description?: string;
  type: DataSourceType;
  active: boolean;
  priority: number;
  config: Record<string, any>;
  has_credentials: boolean;
  field_mapping?: Record<string, string>;
  cache_ttl_seconds: number;
  cache_strategy: 'memory' | 'redis' | 'none';
  last_sync_at?: string;
  last_sync_status?: 'success' | 'partial' | 'failed';
  last_sync_count: number;
  last_error?: string;
  created_at: string;
  updated_at: string;
}

export interface DataSourceCreate {
  name: string;
  type: DataSourceType;
  description?: string;
  active?: boolean;
  priority?: number;
  config: Record<string, any>;
  credentials?: Record<string, any>;
  field_mapping?: Record<string, string>;
  cache_ttl_seconds?: number;
  cache_strategy?: 'memory' | 'redis' | 'none';
}

export interface DataSourceUpdate extends Partial<DataSourceCreate> { }

export interface DataSourceTestResult {
  success: boolean;
  message: string;
  details: Record<string, any>;
}

export interface DataSourceSyncResult {
  success: boolean;
  count: number;
  errors: Array<{ region?: string; error: string }>;
}

export interface DataSourceTypeInfo {
  id: string;
  name: string;
  description: string;
  icon: string;
  config_fields: string[];
}

// =============================================================================
// HELPERS
// =============================================================================

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
    const error = new Error(`API Error: ${response.status}`);
    (error as any).status = response.status;
    throw error;
  }

  return response.json();
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

/**
 * Lista tipos de data source disponíveis
 */
export async function getDataSourceTypes(): Promise<{ types: DataSourceTypeInfo[] }> {
  return request('/v1/data-sources/types');
}

/**
 * Lista todas as fontes de dados do tenant
 */
export async function getDataSources(activeOnly: boolean = false, tenantId?: number): Promise<{
  data_sources: DataSource[];
  total: number;
}> {
  const params = new URLSearchParams();
  if (activeOnly) params.append('active_only', 'true');
  if (tenantId) params.append('target_tenant_id', tenantId.toString());

  return request(`/v1/data-sources?${params.toString()}`);
}

/**
 * Obtém detalhes de uma fonte de dados
 */
export async function getDataSource(id: number): Promise<DataSource> {
  return request(`/v1/data-sources/${id}`);
}

/**
 * Cria uma nova fonte de dados
 */
export async function createDataSource(data: DataSourceCreate, tenantId?: number): Promise<{
  success: boolean;
  data_source: DataSource;
}> {
  const query = tenantId ? `?target_tenant_id=${tenantId}` : '';
  return request(`/v1/data-sources${query}`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Atualiza uma fonte de dados
 */
export async function updateDataSource(id: number, data: DataSourceUpdate, tenantId?: number): Promise<{
  success: boolean;
  data_source: DataSource;
}> {
  const query = tenantId ? `?target_tenant_id=${tenantId}` : '';
  return request(`/v1/data-sources/${id}${query}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Remove uma fonte de dados
 */
export async function deleteDataSource(id: number, tenantId?: number): Promise<{
  success: boolean;
  message: string;
}> {
  const query = tenantId ? `?target_tenant_id=${tenantId}` : '';
  return request(`/v1/data-sources/${id}${query}`, {
    method: 'DELETE',
  });
}

/**
 * Testa conexão com uma fonte de dados
 */
export async function testDataSource(id: number, tenantId?: number): Promise<DataSourceTestResult> {
  const query = tenantId ? `?target_tenant_id=${tenantId}` : '';
  return request(`/v1/data-sources/${id}/test${query}`, {
    method: 'POST',
  });
}

/**
 * Inicia sincronização de uma fonte de dados
 */
export async function syncDataSource(id: number, tenantId?: number): Promise<{
  success: boolean;
  message: string;
  source_id: number;
}> {
  const query = tenantId ? `?target_tenant_id=${tenantId}` : '';
  return request(`/v1/data-sources/${id}/sync${query}`, {
    method: 'POST',
  });
}

/**
 * Busca um imóvel/produto pelo código (para debug)
 */
export async function lookupProperty(sourceId: number, code: string): Promise<{
  success: boolean;
  property?: Record<string, any>;
  message?: string;
}> {
  return request(`/v1/data-sources/${sourceId}/lookup/${code}`);
}

// =============================================================================
// CONSTANTES PARA UI
// =============================================================================

export const DATA_SOURCE_TYPE_OPTIONS = [
  {
    id: 'portal_api' as DataSourceType,
    name: 'Portal API',
    description: 'API JSON de portal imobiliario',
    icon: 'globe',
  },
  {
    id: 'custom_api' as DataSourceType,
    name: 'API Personalizada',
    description: 'Qualquer API REST com autenticacao configuravel',
    icon: 'code',
  },
  {
    id: 'webhook' as DataSourceType,
    name: 'Webhook',
    description: 'Recebe dados via POST do sistema do cliente',
    icon: 'webhook',
  },
  {
    id: 'manual' as DataSourceType,
    name: 'Manual',
    description: 'Usa apenas produtos cadastrados no sistema',
    icon: 'database',
  },
];

export const DEFAULT_FIELD_MAPPING: Record<string, string> = {
  codigo: 'code',
  titulo: 'title',
  tipo: 'type',
  regiao: 'region',
  preco: 'price',
  quartos: 'bedrooms',
  banheiros: 'bathrooms',
  vagas: 'parking',
  metragem: 'area',
  descricao: 'description',
};
