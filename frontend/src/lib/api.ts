import { getToken, getUser } from './auth';

// ✅ CORREÇÃO 1: Remover /v1 da base URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

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
    const error = new Error(`API Error: ${response.status}`);
    (error as any).status = response.status;
    throw error;
  }

  return response.json();
}

// ✅ CORREÇÃO 2 e 3: Endpoint correto + sem tenant_slug (usa token)
export async function getMetrics() {
  return request('/dashboard/metrics');  // ✅ Token já tem tenant_id!
}

// ✅ CORREÇÃO 4: Atualizar também leads-by-day
export async function getLeadsByDay(days: number = 7) {
  return request<any[]>(`/dashboard/leads-by-day?days=${days}`);  // ✅ Sem tenant_slug
}

// === LEADS ===
export async function getLeads(params?: {
  page?: number;
  status?: string;
  qualification?: string;
  search?: string;
}) {
  const searchParams = new URLSearchParams();

  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.status) searchParams.set('status', params.status);
  if (params?.qualification) searchParams.set('qualification', params.qualification);
  if (params?.search) searchParams.set('search', params.search);

  const queryString = searchParams.toString();
  return request(`/leads${queryString ? `?${queryString}` : ''}`);
}

export async function getLead(id: number) {
  const slug = getTenantSlug();
  return request(`/leads/${id}?tenant_slug=${slug}`);
}

export async function getLeadMessages(id: number) {
  const slug = getTenantSlug();
  return request(`/leads/${id}/messages?tenant_slug=${slug}`);
}

export async function updateLead(id: number, data: Record<string, unknown>) {
  const slug = getTenantSlug();
  return request(`/leads/${id}?tenant_slug=${slug}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// NOVA FUNÇÃO — ATRIBUIÇÃO MANUAL DE VENDEDOR
export async function assignLeadToSeller(leadId: number, sellerId: number) {
  return request(`/${leadId}/assign`, {
    method: 'POST',
    body: JSON.stringify({ seller_id: sellerId }),
  });
}

// Função para remover atribuição (caso precise no futuro)
export async function unassignLeadFromSeller(leadId: number) {
  return request(`/${leadId}/assign-seller`, {
    method: 'DELETE',
  });
}

// === TENANTS ===
export async function getTenant() {
  const slug = getTenantSlug();
  return request(`/tenants/${slug}`);
}

export async function getNiches() {
  return request('/tenants/niches');
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
  return request('/products/check-access');
}

// Estatísticas dos produtos
export async function getProductsStats() {
  return request('/products/stats');
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
  return request(`/products${query ? `?${query}` : ''}`);
}

// Busca produto por ID
export async function getProduct(id: number): Promise<Product> {
  return request(`/products/${id}`);
}

// Cria produto
export async function createProduct(data: ProductCreate) {
  return request('/products', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// Atualiza produto
export async function updateProduct(id: number, data: Partial<ProductCreate>) {
  return request(`/products/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// Remove produto
export async function deleteProduct(id: number) {
  return request(`/products/${id}`, {
    method: 'DELETE',
  });
}

// Ativa/desativa produto
export async function toggleProductStatus(id: number) {
  return request(`/products/${id}/toggle-status`, {
    method: 'POST',
  });
}

// Testa detecção de gatilhos (debug)
export async function detectProduct(message: string) {
  return request(`/products/detect?message=${encodeURIComponent(message)}`, {
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
  return request(`/leads/${leadId}/events?tenant_slug=${slug}`);
}

// Atribui vendedor ao lead (COM NOTIFICAÇÃO AUTOMÁTICA!)
export async function assignSellerToLead(leadId: number, sellerId: number, reason?: string) {
  return request(`/leads/${leadId}/assign-seller`, {
    method: 'POST',
    body: JSON.stringify({
      seller_id: sellerId,
      reason: reason || 'Atribuição manual via dashboard'
    }),
  });
}

// Remove atribuição de vendedor
export async function unassignSellerFromLead(leadId: number) {
  return request(`/leads/${leadId}/assign-seller`, {
    method: 'DELETE',
  });
}

// Atualiza custom_data (para notas e tags)
export async function updateLeadCustomData(leadId: number, customData: Record<string, any>) {
  const slug = getTenantSlug();
  return request(`/leads/${leadId}?tenant_slug=${slug}`, {
    method: 'PATCH',
    body: JSON.stringify({ custom_data: customData }),
  });
}

// Busca lista de vendedores
export async function getSellers() {
  const slug = getTenantSlug();
  return request(`/sellers?tenant_slug=${slug}`);
}