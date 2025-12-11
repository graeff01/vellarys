/**
 * API de Handoff
 * 
 * Funções para gerenciar transferência de leads para vendedores
 * com notificação via WhatsApp.
 */

import { getToken } from './auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// ==========================================
// TIPOS
// ==========================================

export interface AssignAndHandoffRequest {
  seller_id: number;
  notes?: string;
  notify_seller?: boolean;
}

export interface AssignAndHandoffResponse {
  success: boolean;
  lead_id: number;
  status: string;
  assigned_seller_id: number;
  assigned_seller_name: string;
  seller_notified: boolean;
  seller_notification_error?: string | null;
}

export interface PendingHandoffLead {
  id: number;
  name: string | null;
  phone: string | null;
  qualification: string;
  status: string;
  summary: string | null;
  custom_data: Record<string, unknown>;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface PendingHandoffResponse {
  leads: PendingHandoffLead[];
  total: number;
}

export interface HandoffHistoryItem {
  id: number;
  lead_id: number;
  from_status: string;
  to_status: string;
  seller_id: number | null;
  seller_name: string | null;
  performed_by: number | null;
  performed_by_name: string | null;
  notes: string | null;
  seller_notified: boolean;
  created_at: string;
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
 * Atribui vendedor ao lead (sem handoff)
 * Use quando quiser apenas vincular o vendedor sem mudar status
 */
export async function assignSellerToLead(
  leadId: number, 
  sellerId: number,
  notes?: string
): Promise<{ success: boolean; message: string }> {
  return request(`/leads/${leadId}/assign`, {
    method: 'POST',
    body: JSON.stringify({ 
      seller_id: sellerId,
      notes 
    }),
  });
}

/**
 * Executa handoff de lead que já tem vendedor
 * Use quando o lead já foi atribuído e você quer transferir
 */
export async function executeHandoff(
  leadId: number,
  notes?: string
): Promise<{ success: boolean; message: string }> {
  return request(`/leads/${leadId}/handoff`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}

/**
 * ⭐ PRINCIPAL: Atribui vendedor + executa handoff + notifica via WhatsApp
 * Use esta função quando gestor atribui um lead quente para vendedor
 */
export async function assignAndHandoff(
  leadId: number,
  sellerId: number,
  options?: {
    notes?: string;
    notifySeller?: boolean;
  }
): Promise<AssignAndHandoffResponse> {
  return request(`/leads/${leadId}/assign-and-handoff`, {
    method: 'POST',
    body: JSON.stringify({
      seller_id: sellerId,
      notes: options?.notes || '',
      notify_seller: options?.notifySeller ?? true,
    }),
  });
}

/**
 * Lista leads quentes aguardando handoff
 */
export async function getPendingHandoffLeads(): Promise<PendingHandoffResponse> {
  return request('/leads/pending-handoff');
}

/**
 * Busca histórico de handoffs de um lead
 */
export async function getHandoffHistory(leadId: number): Promise<HandoffHistoryItem[]> {
  return request(`/leads/${leadId}/handoff-history`);
}

/**
 * Reabre um lead que foi transferido
 */
export async function reopenLead(
  leadId: number,
  reason?: string
): Promise<{ success: boolean; message: string }> {
  return request(`/leads/${leadId}/reopen`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}