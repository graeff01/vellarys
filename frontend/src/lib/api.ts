import { getToken, getUser } from './auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

function getTenantSlug(): string {
  if (typeof window === 'undefined') return 'imob-teste';
  const user = getUser();
  return user?.tenant?.slug || 'imob-teste';
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

// === MÉTRICAS ===
export async function getMetrics() {
  const slug = getTenantSlug();
  return request(`/metrics?tenant_slug=${slug}`);
}

// === LEADS ===
export async function getLeads(params?: {
  page?: number;
  status?: string;
  qualification?: string;
  search?: string;
  assigned_seller_id?: number;
  unassigned?: boolean;
}) {
  const slug = getTenantSlug();
  const searchParams = new URLSearchParams({ tenant_slug: slug });

  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.status) searchParams.set('status', params.status);
  if (params?.qualification) searchParams.set('qualification', params.qualification);
  if (params?.search) searchParams.set('search', params.search);
  if (params?.assigned_seller_id) searchParams.set('assigned_seller_id', params.assigned_seller_id.toString());
  if (params?.unassigned) searchParams.set('unassigned', 'true');

  return request(`/leads?${searchParams}`);
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