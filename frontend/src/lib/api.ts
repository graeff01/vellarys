import { getToken, getUser } from './auth';

// ✅ CORREÇÃO 1: Remover /v1 da base URL
const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

// ✅ RESTAURAR: Função getTenantSlug (removida por engano pelo Jules)
function getTenantSlug(): string {
  if (typeof window === 'undefined') return '';
  const user = getUser();
  return user?.tenant?.slug || '';
}

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

    // Tentar extrair detalhes do erro do backend
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: `HTTP ${response.status}` };
    }

    const error = new Error(`API Error: ${response.status}`);
    (error as any).status = response.status;
    (error as any).response = { data: errorData };
    throw error;
  }

  return response.json();
}

// Export api object for generic requests
export const api = {
  get: <T = any>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),
  post: <T = any>(endpoint: string, data?: any) => request<T>(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  }),
  put: <T = any>(endpoint: string, data?: any) => request<T>(endpoint, {
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  }),
  patch: <T = any>(endpoint: string, data?: any) => request<T>(endpoint, {
    method: 'PATCH',
    body: data ? JSON.stringify(data) : undefined,
  }),
  delete: <T = any>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
};

// ✅ CORREÇÃO 2 e 3: Endpoint correto + sem tenant_slug (usa token)
export async function getMetrics() {
  return request('/v1/dashboard/metrics');  // ✅ Token já tem tenant_id!
}

// ✅ CORREÇÃO 4: Atualizar também leads-by-day
export async function getLeadsByDay(days: number = 7) {
  return request<any[]>(`/v1/dashboard/leads-by-day?days=${days}`);  // ✅ Sem tenant_slug
}

// === LEADS ===
export async function getLeads(params?: {
  page?: number;
  status?: string;
  qualification?: string;
  search?: string;
  sort_by?: string;
}) {
  const searchParams = new URLSearchParams();

  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.status) searchParams.set('status', params.status);
  if (params?.qualification) searchParams.set('qualification', params.qualification);
  if (params?.search) searchParams.set('search', params.search);
  if (params?.sort_by) searchParams.set('sort_by', params.sort_by);

  const queryString = searchParams.toString();
  return request(`/v1/leads${queryString ? `?${queryString}` : ''}`);
}

export async function getLead(id: number) {
  const slug = getTenantSlug();
  return request(`/v1/leads/${id}?tenant_slug=${slug}`);
}

export async function getLeadMessages(id: number) {
  const slug = getTenantSlug();
  return request(`/v1/leads/${id}/messages?tenant_slug=${slug}`);
}

export async function updateLead(id: number, data: Record<string, unknown>) {
  const slug = getTenantSlug();
  return request(`/v1/leads/${id}?tenant_slug=${slug}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// NOVA FUNÇÃO — ATRIBUIÇÃO MANUAL DE VENDEDOR
export async function assignLeadToSeller(leadId: number, sellerId: number) {
  return request(`/v1/${leadId}/assign`, {
    method: 'POST',
    body: JSON.stringify({ seller_id: sellerId }),
  });
}

// Função para remover atribuição (caso precise no futuro)
export async function unassignLeadFromSeller(leadId: number) {
  return request(`/v1/${leadId}/assign-seller`, {
    method: 'DELETE',
  });
}

// === TENANTS ===
export async function getTenant() {
  const slug = getTenantSlug();
  return request(`/v1/tenants/${slug}`);
}

export async function getNiches() {
  return request('/v1/tenants/niches');
}

// === PRODUCTS (Genérico) ===

export interface Product {
  id: number;
  name: string;
  slug: string;
  status: string;
  status_label?: string;
  active: boolean;
  url_landing_page?: string;
  image_url?: string;
  triggers: string[];
  priority: number;
  description?: string;
  ai_instructions?: string;
  qualification_questions: string[];
  seller_id?: number;
  seller_name?: string;
  distribution_method?: string;
  notify_manager: boolean;
  total_leads: number;
  qualified_leads: number;
  converted_leads: number;
  attributes: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface ProductCreate {
  name: string;
  status?: string;
  url_landing_page?: string;
  image_url?: string;
  triggers?: string[];
  priority?: number;
  description?: string;
  ai_instructions?: string;
  qualification_questions?: string[];
  seller_id?: number;
  distribution_method?: string;
  notify_manager?: boolean;
  attributes?: Record<string, any>;
}

// Retrocompatibilidade
export type Empreendimento = Product;
export type EmpreendimentoCreate = ProductCreate;

// Verifica se tenant tem acesso a produtos
export async function checkProductsAccess(): Promise<{ has_access: boolean; niche: string }> {
  return request('/v1/products/check-access');
}

// Estatísticas dos produtos
export async function getProductsStats() {
  return request('/v1/products/stats');
}

// Lista produtos
export async function getProducts(params?: {
  active?: boolean;
  status?: string;
  search?: string;
}): Promise<{ products: Product[]; total: number }> {
  const searchParams = new URLSearchParams();

  if (params?.active !== undefined) searchParams.set('active', params.active.toString());
  if (params?.status) searchParams.set('status', params.status);
  if (params?.search) searchParams.set('search', params.search);

  const query = searchParams.toString();
  return request(`/v1/products${query ? `?${query}` : ''}`);
}

// Busca produto por ID
export async function getProduct(id: number): Promise<Product> {
  return request(`/v1/products/${id}`);
}

// Cria produto
export async function createProduct(data: ProductCreate) {
  return request('/v1/products', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// Atualiza produto
export async function updateProduct(id: number, data: Partial<ProductCreate>) {
  return request(`/v1/products/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// Remove produto
export async function deleteProduct(id: number) {
  return request(`/v1/products/${id}`, {
    method: 'DELETE',
  });
}

// Ativa/desativa produto
export async function toggleProductStatus(id: number) {
  return request(`/v1/products/${id}/toggle-status`, {
    method: 'POST',
  });
}

// Testa detecção de gatilhos (debug)
export async function detectProduct(message: string) {
  return request(`/v1/products/detect?message=${encodeURIComponent(message)}`, {
    method: 'POST',
  });
}

// Atalhos para retrocompatibilidade (Frontend ainda referenciando Empreendimento)
export const getEmpreendimentos = getProducts;
export const getEmpreendimento = getProduct;
export const createEmpreendimento = createProduct;
export const updateEmpreendimento = updateProduct;
export const deleteEmpreendimento = deleteProduct;
export const toggleEmpreendimentoStatus = toggleProductStatus;
// ===============================================
// 🆕 NOVAS FUNÇÕES - MELHORIAS LEAD DETAIL V2.0
// ===============================================

// Busca eventos/timeline do lead
export async function getLeadEvents(leadId: number) {
  const slug = getTenantSlug();
  return request(`/v1/leads/${leadId}/events?tenant_slug=${slug}`);
}

// Atribui vendedor ao lead (COM NOTIFICAÇÃO AUTOMÁTICA!)
export async function assignSellerToLead(leadId: number, sellerId: number, reason?: string) {
  return request(`/v1/leads/${leadId}/assign-seller`, {
    method: 'POST',
    body: JSON.stringify({
      seller_id: sellerId,
      reason: reason || 'Atribuição manual via dashboard'
    }),
  });
}

// Remove atribuição de vendedor
export async function unassignSellerFromLead(leadId: number) {
  return request(`/v1/leads/${leadId}/assign-seller`, {
    method: 'DELETE',
  });
}

// Atualiza custom_data (para notas e tags)
export async function updateLeadCustomData(leadId: number, customData: Record<string, any>) {
  const slug = getTenantSlug();
  return request(`/v1/leads/${leadId}?tenant_slug=${slug}`, {
    method: 'PATCH',
    body: JSON.stringify({ custom_data: customData }),
  });
}

// Busca lista de vendedores
export async function getSellers() {
  const slug = getTenantSlug();
  return request(`/v1/sellers?tenant_slug=${slug}`);
}

// === PUSH NOTIFICATIONS ===
export async function savePushSubscription(subscription: any) {
  return request('/notifications/subscribe', {
    method: 'POST',
    body: JSON.stringify(subscription),
  });
}

// === DASHBOARD CONFIG ===
export interface WidgetConfig {
  id: string;
  type: string;
  enabled: boolean;
  position: number;
  size: string;
  settings?: Record<string, any>;

  // Grid layout fields (react-grid-layout) - v2
  i?: string;      // ID único para o grid
  x?: number;      // Posição X (coluna)
  y?: number;      // Posição Y (linha)
  w?: number;      // Largura em colunas
  h?: number;      // Altura em rows
  minW?: number;
  maxW?: number;
  minH?: number;
  maxH?: number;
  static?: boolean; // Widget fixo (não arrastável)
}

export interface DashboardConfigResponse {
  id: number | null;
  widgets: WidgetConfig[];
  settings: Record<string, any>;
  is_default: boolean;
  layout_version?: 'v1' | 'v2'; // v1 = position/size, v2 = grid layout
}

export interface WidgetType {
  id: string;
  name: string;
  description: string;
  category: string;
  default_size: string;
  icon: string;
}

export async function getDashboardConfig(): Promise<DashboardConfigResponse> {
  return request('/v1/dashboard/config');
}

export async function updateDashboardConfig(
  widgets: WidgetConfig[],
  settings?: Record<string, any>,
  layoutVersion: 'v1' | 'v2' = 'v2'
): Promise<DashboardConfigResponse> {
  return request('/v1/dashboard/config', {
    method: 'PUT',
    body: JSON.stringify({
      widgets,
      settings: settings || {},
      layout_version: layoutVersion,
    }),
  });
}

export async function getAvailableWidgets(): Promise<WidgetType[]> {
  return request('/v1/dashboard/widgets');
}

export async function resetDashboardConfig(): Promise<DashboardConfigResponse> {
  return request('/v1/dashboard/config/reset', {
    method: 'POST',
  });
}

// === SALES & GOALS ===
export interface SalesGoal {
  id: number | null;
  period: string;
  revenue_goal: number | null;
  revenue_actual: number;
  revenue_progress: number;
  deals_goal: number | null;
  deals_actual: number;
  deals_progress: number;
  leads_goal: number | null;
  leads_actual: number;
  leads_progress: number;
  days_remaining: number;
  days_passed: number;
  total_days: number;
}

export interface SalesMetrics {
  total_deals: number;
  total_revenue: number;
  average_ticket: number;
  conversion_rate: number;
  goal: SalesGoal | null;
  projected_deals: number;
  projected_revenue: number;
  on_track: boolean;
  seller_ranking: Array<{
    seller_id: number;
    seller_name: string;
    deals_count: number;
    conversion_rate: number;
    leads_assigned: number;
  }>;
  days_remaining: number;
  deals_today: number;
  deals_this_week: number;
  revenue_by_source?: Record<string, number>;
  pulse?: Array<{
    id: number;
    type: string;
    lead_name: string;
    description: string;
    created_at: string;
  }>;
}

export async function getSalesGoal(period?: string): Promise<SalesGoal> {
  const query = period ? `?period=${period}` : '';
  return request(`/v1/sales/goals${query}`);
}

export async function setSalesGoal(data: {
  revenue_goal?: number;
  deals_goal?: number;
  leads_goal?: number;
  period?: string;
}): Promise<SalesGoal> {
  return request('/v1/sales/goals', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getSalesMetrics(period?: string): Promise<SalesMetrics> {
  const query = period ? `?period=${period}` : '';
  return request(`/v1/sales/metrics${query}`);
}

export async function registerDeal(leadId: number, revenue: number, notes?: string) {
  return request('/v1/sales/deal', {
    method: 'PUT',
    body: JSON.stringify({ lead_id: leadId, revenue, notes }),
  });
}

// === OPPORTUNITIES ===
export interface Opportunity {
  id: number;
  lead_id: number;
  tenant_id: number;
  title: string;
  value: number;
  status: 'novo' | 'negociacao' | 'proposta' | 'ganho' | 'perdido';
  product_id?: number;
  product_name?: string;
  seller_id?: number;
  seller_name?: string;
  expected_close_date?: string;
  won_at?: string;
  lost_at?: string;
  lost_reason?: string;
  notes?: string;
  custom_data?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface OpportunityCreate {
  title: string;
  product_id?: number;
  seller_id?: number;
  value?: number;
  expected_close_date?: string;
  notes?: string;
  custom_data?: Record<string, any>;
}

export interface OpportunityUpdate {
  title?: string;
  product_id?: number;
  seller_id?: number;
  value?: number;
  status?: string;
  expected_close_date?: string;
  notes?: string;
  custom_data?: Record<string, any>;
}

export interface OpportunityMetrics {
  total: number;
  by_status: Record<string, number>;
  total_value: number;
  won_value: number;
  lost_count: number;
  conversion_rate: number;
}

export async function getOpportunities(params?: {
  page?: number;
  per_page?: number;
  status?: string;
  seller_id?: number;
}): Promise<{ items: Opportunity[]; total: number; page: number; per_page: number }> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString());
  if (params?.status) searchParams.set('status', params.status);
  if (params?.seller_id) searchParams.set('seller_id', params.seller_id.toString());
  const query = searchParams.toString();
  return request(`/v1/opportunities${query ? `?${query}` : ''}`);
}

export async function getOpportunity(id: number): Promise<Opportunity> {
  return request(`/v1/opportunities/${id}`);
}

export async function updateOpportunity(id: number, data: OpportunityUpdate): Promise<Opportunity> {
  return request(`/v1/opportunities/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteOpportunity(id: number): Promise<{ success: boolean }> {
  return request(`/v1/opportunities/${id}`, {
    method: 'DELETE',
  });
}

export async function winOpportunity(id: number, notes?: string): Promise<Opportunity> {
  return request(`/v1/opportunities/${id}/win`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}

export async function loseOpportunity(id: number, reason: string, notes?: string): Promise<Opportunity> {
  return request(`/v1/opportunities/${id}/lose`, {
    method: 'POST',
    body: JSON.stringify({ reason, notes }),
  });
}

export async function getLeadOpportunities(leadId: number): Promise<Opportunity[]> {
  return request(`/v1/leads/${leadId}/opportunities`);
}

export async function createLeadOpportunity(leadId: number, data: OpportunityCreate): Promise<Opportunity> {
  return request(`/v1/leads/${leadId}/opportunities`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getOpportunityMetrics(): Promise<OpportunityMetrics> {
  return request('/v1/opportunities/metrics/summary');
}

// === LEAD PAGE LAYOUT CONFIG ===
export interface LeadPageConfig {
  id: number | null;
  widgets: WidgetConfig[];
  settings: Record<string, any>;
  is_default: boolean;
}

export async function getLeadPageConfig(): Promise<LeadPageConfig> {
  return request('/v1/dashboard/lead-page-config');
}

export async function updateLeadPageConfig(
  widgets: WidgetConfig[],
  settings?: Record<string, any>
): Promise<LeadPageConfig> {
  return request('/v1/dashboard/lead-page-config', {
    method: 'PUT',
    body: JSON.stringify({ widgets, settings: settings || {} }),
  });
}