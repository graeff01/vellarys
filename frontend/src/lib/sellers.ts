/**
 * API de Vendedores
 * 
 * Funções para gerenciar a equipe de vendas.
 */

import { getToken } from './auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// ==========================================
// TIPOS
// ==========================================

export interface Seller {
  id: number;
  name: string;
  whatsapp: string;
  email: string | null;
  cities: string[];
  specialties: string[];
  active: boolean;
  available: boolean;
  max_leads_per_day: number;
  leads_today: number;
  total_leads: number;
  converted_leads: number;
  conversion_rate: number;
  priority: number;
  on_vacation: boolean;
  vacation_until: string | null;
  notification_channels: string[];
  last_lead_at: string | null;
  created_at: string;
}

export interface SellerCreate {
  name: string;
  whatsapp: string;
  email?: string;
  cities?: string[];
  specialties?: string[];
  max_leads_per_day?: number;
  priority?: number;
  notification_channels?: string[];
}

export interface SellerUpdate {
  name?: string;
  whatsapp?: string;
  email?: string;
  cities?: string[];
  specialties?: string[];
  max_leads_per_day?: number;
  priority?: number;
  active?: boolean;
  available?: boolean;
  on_vacation?: boolean;
  vacation_until?: string;
  notification_channels?: string[];
}

export interface SellersResponse {
  sellers: Seller[];
  total: number;
}

export interface SellerStats {
  total_sellers: number;
  active_sellers: number;
  available_sellers: number;
  total_leads_distributed: number;
  total_conversions: number;
  avg_conversion_rate: number;
}



// ==========================================
// FUNÇÕES
// ==========================================

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  
  const response = await fetch(`${API_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
    throw new Error(error.detail || 'Erro na requisição');
  }

  return response.json();
}

/**
 * Lista todos os vendedores
 */
export async function getSellers(
  activeOnly: boolean = false,
  availableOnly: boolean = false
): Promise<SellersResponse> {
  const params = new URLSearchParams();
  if (activeOnly) params.append('active_only', 'true');
  if (availableOnly) params.append('available_only', 'true');
  
  const query = params.toString();
  return request<SellersResponse>(`/sellers${query ? `?${query}` : ''}`);
}

/**
 * Busca um vendedor específico
 */
export async function getSeller(id: number): Promise<Seller> {
  return request<Seller>(`/sellers/${id}`);
}

/**
 * Cria um novo vendedor
 */
export async function createSeller(data: SellerCreate): Promise<{ success: boolean; seller: Seller }> {
  return request(`/sellers`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Atualiza um vendedor
 */
export async function updateSeller(id: number, data: SellerUpdate): Promise<{ success: boolean }> {
  return request(`/sellers/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}


/**
 * Remove um vendedor
 */
export async function deleteSeller(id: number): Promise<{ success: boolean }> {
  return request(`/sellers/${id}`, {
    method: 'DELETE',
  });
}

/**
 * Alterna disponibilidade do vendedor
 */
export async function toggleSellerAvailability(id: number): Promise<{ success: boolean; available: boolean }> {
  return request(`/sellers/${id}/toggle-availability`, {
    method: 'POST',
  });
}

/**
 * Busca estatísticas dos vendedores
 */
export async function getSellerStats(): Promise<SellerStats> {
  return request<SellerStats>(`/sellers/stats/summary`);
}

/**
 * Busca configuração de especialidades do nicho
 */
export async function getSpecialtiesConfig(): Promise<{
  niche: string;
  specialties: Array<{ value: string; label: string }>;
  allow_custom: boolean;
}> {
  return request(`/sellers/config/specialties`);
  
}

/**
 * Atribui um lead a um vendedor
 */
export async function assignLeadToSeller(leadId: number, sellerId: number): Promise<{ success: boolean }> {
  return request(`/leads/${leadId}/assign-seller`, {
    method: 'POST',
    body: JSON.stringify({ seller_id: sellerId }),
  });
}

/**
 * Remove atribuição de vendedor de um lead
 */
export async function unassignLeadFromSeller(leadId: number): Promise<{ success: boolean }> {
  return request(`/leads/${leadId}/assign-seller`, {
    method: 'DELETE',
  });
}



