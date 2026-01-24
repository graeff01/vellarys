/**
 * API Client - Seller Inbox
 *
 * Funções para interagir com o CRM Inbox dos corretores
 */

import { api } from './api';

// ============================================================================
// TYPES
// ============================================================================

export interface InboxLead {
  id: number;
  name: string;
  phone: string;
  status: string;
  qualification: string | null;
  attended_by: string | null;

  // Métricas da conversa
  unread_messages: number;
  last_message_at: string | null;
  last_message_preview: string | null;

  // Informações do lead
  city: string | null;
  interest: string | null;
  budget: string | null;

  // Controle
  is_taken_over: boolean;
  seller_took_over_at: string | null;
}

export interface InboxMessage {
  id: number;
  role: string;
  content: string;
  created_at: string;
  sender_type: string | null;
  sender_user_id: number | null;
  sender_name: string | null;
}

export interface SellerInfo {
  user_id: number;
  user_name: string;
  user_email: string;
  user_role: string;

  seller_id: number | null;
  seller_name: string | null;
  seller_whatsapp: string | null;
  seller_active: boolean | null;

  tenant_id: number;
  tenant_name: string;
  tenant_slug: string;
  handoff_mode: string;

  total_leads: number | null;
  leads_today: number | null;
  conversion_rate: number | null;

  is_linked: boolean;
  can_use_inbox: boolean;
}

export interface TakeOverResponse {
  success: boolean;
  message: string;
  lead_id: number;
  attended_by: string;
  took_over_at: string;
}

export interface SendMessageResponse {
  success: boolean;
  message: string;
  message_id: number;
  sent_at: string;
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Verifica se o inbox está disponível para o corretor atual
 */
export async function checkInboxAvailable(): Promise<{
  available: boolean;
  reason: string;
  handoff_mode: string | null;
  seller_id?: number;
  seller_name?: string;
}> {
  const response = await api.get('/seller/info/check-inbox-available');
  return response.data;
}

/**
 * Busca informações completas do corretor logado
 */
export async function getSellerInfo(): Promise<SellerInfo> {
  const response = await api.get('/seller/info/me');
  return response.data;
}

/**
 * Lista leads atribuídos ao corretor
 */
export async function getInboxLeads(params?: {
  status_filter?: string;
  attended_filter?: 'ai' | 'seller' | 'all';
}): Promise<InboxLead[]> {
  const response = await api.get('/seller/inbox/leads', { params });
  return response.data;
}

/**
 * Busca histórico de mensagens de um lead
 */
export async function getLeadMessages(leadId: number): Promise<InboxMessage[]> {
  const response = await api.get(`/seller/inbox/leads/${leadId}/messages`);
  return response.data;
}

/**
 * Corretor assume a conversa (IA para de responder)
 */
export async function takeOverLead(leadId: number): Promise<TakeOverResponse> {
  const response = await api.post(`/seller/inbox/leads/${leadId}/take-over`);
  return response.data;
}

/**
 * Envia mensagem como corretor
 */
export async function sendMessage(
  leadId: number,
  content: string
): Promise<SendMessageResponse> {
  const response = await api.post(`/seller/inbox/leads/${leadId}/send-message`, {
    content,
  });
  return response.data;
}

/**
 * Devolve lead para a IA
 */
export async function returnToAI(leadId: number): Promise<{
  success: boolean;
  message: string;
  attended_by: string;
}> {
  const response = await api.post(`/seller/inbox/leads/${leadId}/return-to-ai`);
  return response.data;
}

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Formata a data relativa (ex: "5 min atrás")
 */
export function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return 'Nunca';

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Agora mesmo';
  if (diffMins < 60) return `${diffMins} min atrás`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h atrás`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d atrás`;

  return date.toLocaleDateString('pt-BR');
}

/**
 * Retorna cor baseada na qualificação
 */
export function getQualificationColor(qualification: string | null): string {
  switch (qualification?.toLowerCase()) {
    case 'quente':
    case 'hot':
      return 'text-red-600 bg-red-50';
    case 'morno':
    case 'warm':
      return 'text-orange-600 bg-orange-50';
    case 'frio':
    case 'cold':
      return 'text-blue-600 bg-blue-50';
    default:
      return 'text-gray-600 bg-gray-50';
  }
}

/**
 * Retorna ícone/emoji baseado na qualificação
 */
export function getQualificationEmoji(qualification: string | null): string {
  switch (qualification?.toLowerCase()) {
    case 'quente':
    case 'hot':
      return '🔥';
    case 'morno':
    case 'warm':
      return '☀️';
    case 'frio':
    case 'cold':
      return '❄️';
    default:
      return '📋';
  }
}
