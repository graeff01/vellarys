/**
 * API Client: Commercial Proposals (Propostas Comerciais)
 * =========================================================
 *
 * Gerenciamento de propostas imobiliárias.
 */

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token');
}

export interface PropertyInfo {
  type: string;
  address: string;
  size?: string;
  rooms?: number;
  bathrooms?: number;
  parking?: number;
  features: string[];
  images: string[];
}

export interface TimelineEvent {
  date: string;
  event: string;
  value?: number;
  note?: string;
}

export interface CommercialProposal {
  id: number;
  lead_id: number;
  lead_name: string;
  seller_id?: number;
  seller_name?: string;
  property_info: PropertyInfo;
  asked_value: number;
  offered_value: number;
  final_value?: number;
  status: string;
  deadline?: string;
  timeline: TimelineEvent[];
  notes?: string;
  created_at: string;
  updated_at: string;
  closed_at?: string;
  diff_value: number;
  diff_percentage: number;
}

export interface CreateProposalPayload {
  lead_id: number;
  seller_id?: number;
  property_info: PropertyInfo;
  asked_value: number;
  offered_value: number;
  deadline_hours?: number;
  notes?: string;
}

/**
 * Lista propostas com filtros
 */
export async function getProposals(filters?: {
  status?: string;
  lead_id?: number;
  seller_id?: number;
  property_type?: string;
  min_value?: number;
  max_value?: number;
}): Promise<CommercialProposal[]> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const params = new URLSearchParams();
  if (filters?.status) params.append('status', filters.status);
  if (filters?.lead_id) params.append('lead_id', filters.lead_id.toString());
  if (filters?.seller_id) params.append('seller_id', filters.seller_id.toString());
  if (filters?.property_type) params.append('property_type', filters.property_type);
  if (filters?.min_value) params.append('min_value', filters.min_value.toString());
  if (filters?.max_value) params.append('max_value', filters.max_value.toString());

  const response = await fetch(
    `${API_URL}/v1/proposals?${params.toString()}`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  if (!response.ok) throw new Error('Erro ao carregar propostas');
  return response.json();
}

/**
 * Busca proposta por ID
 */
export async function getProposal(id: number): Promise<CommercialProposal> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const response = await fetch(
    `${API_URL}/v1/proposals/${id}`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  if (!response.ok) throw new Error('Proposta não encontrada');
  return response.json();
}

/**
 * Cria nova proposta
 */
export async function createProposal(payload: CreateProposalPayload): Promise<CommercialProposal> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const response = await fetch(
    `${API_URL}/v1/proposals`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao criar proposta');
  }

  return response.json();
}

/**
 * Adiciona evento à timeline
 */
export async function addTimelineEvent(
  proposalId: number,
  event: string,
  value?: number,
  note?: string
): Promise<CommercialProposal> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const response = await fetch(
    `${API_URL}/v1/proposals/${proposalId}/timeline`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ event, value, note })
    }
  );

  if (!response.ok) throw new Error('Erro ao adicionar evento');
  return response.json();
}

/**
 * Fecha proposta como aceita
 */
export async function closeProposal(
  proposalId: number,
  finalValue: number,
  note?: string
): Promise<CommercialProposal> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const params = new URLSearchParams();
  params.append('final_value', finalValue.toString());
  if (note) params.append('note', note);

  const response = await fetch(
    `${API_URL}/v1/proposals/${proposalId}/close?${params.toString()}`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  if (!response.ok) throw new Error('Erro ao fechar proposta');
  return response.json();
}

/**
 * Deleta proposta
 */
export async function deleteProposal(id: number): Promise<void> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const response = await fetch(
    `${API_URL}/v1/proposals/${id}`,
    {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  if (!response.ok) throw new Error('Erro ao deletar proposta');
}

/**
 * Estatísticas de propostas
 */
export async function getProposalsStats(): Promise<{
  total_proposals: number;
  closed: number;
  pending: number;
  rejected: number;
  conversion_rate: number;
  avg_offered_value: number;
  avg_asked_value: number;
  avg_final_value: number;
}> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const response = await fetch(
    `${API_URL}/v1/proposals/stats/summary`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  if (!response.ok) throw new Error('Erro ao carregar estatísticas');
  return response.json();
}
