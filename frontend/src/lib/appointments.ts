/**
 * API Client: Appointments (Agendamentos)
 * ========================================
 *
 * Gerencia agendamentos de compromissos entre vendedores e leads.
 */

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token');
}

export interface Appointment {
  id: number;
  tenant_id: number;
  lead_id: number;
  lead_name: string;
  lead_phone?: string;
  seller_id: number;
  seller_name: string;
  created_by: number;

  title: string;
  description?: string;
  appointment_type: 'visit' | 'call' | 'meeting' | 'demo' | 'videocall';
  scheduled_at: string;
  duration_minutes: number;
  timezone: string;

  location?: string;
  location_lat?: number;
  location_lng?: number;

  status: 'scheduled' | 'confirmed' | 'completed' | 'cancelled' | 'no_show';
  confirmed_by_lead: boolean;
  confirmed_at?: string;

  outcome?: 'sale' | 'follow_up' | 'not_interested' | 'rescheduled';
  outcome_notes?: string;
  completed_at?: string;

  reminder_sent: boolean;
  reminded_at?: string;

  created_at: string;
  updated_at: string;
}

export interface CreateAppointmentPayload {
  lead_id: number;
  seller_id: number;
  title: string;
  description?: string;
  appointment_type?: 'visit' | 'call' | 'meeting' | 'demo' | 'videocall';
  scheduled_at: string;
  duration_minutes?: number;
  timezone?: string;
  location?: string;
  location_lat?: number;
  location_lng?: number;
}

export interface UpdateAppointmentPayload {
  title?: string;
  description?: string;
  appointment_type?: 'visit' | 'call' | 'meeting' | 'demo' | 'videocall';
  scheduled_at?: string;
  duration_minutes?: number;
  location?: string;
  location_lat?: number;
  location_lng?: number;
  status?: 'scheduled' | 'confirmed' | 'completed' | 'cancelled' | 'no_show';
}

export interface ListAppointmentsFilters {
  seller_id?: number;
  lead_id?: number;
  status?: 'scheduled' | 'confirmed' | 'completed' | 'cancelled' | 'no_show';
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export interface CalendarData {
  [date: string]: Appointment[];
}

/**
 * Lista agendamentos com filtros opcionais.
 *
 * @param filters - Filtros de busca
 * @returns Lista de agendamentos
 */
export async function getAppointments(filters?: ListAppointmentsFilters): Promise<Appointment[]> {
  const token = getToken();
  if (!token) {
    throw new Error('Não autenticado');
  }

  const params = new URLSearchParams();
  if (filters?.seller_id) params.append('seller_id', filters.seller_id.toString());
  if (filters?.lead_id) params.append('lead_id', filters.lead_id.toString());
  if (filters?.status) params.append('status', filters.status);
  if (filters?.date_from) params.append('date_from', filters.date_from);
  if (filters?.date_to) params.append('date_to', filters.date_to);
  if (filters?.limit) params.append('limit', filters.limit.toString());
  if (filters?.offset) params.append('offset', filters.offset.toString());

  const queryString = params.toString();
  const url = `${API_URL}/v1/appointments${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Erro ao carregar agendamentos');
  }

  return response.json();
}

/**
 * Retorna agendamentos formatados para calendário (agrupados por dia).
 *
 * @param month - Mês (1-12)
 * @param year - Ano (ex: 2026)
 * @param sellerId - Filtro opcional por vendedor
 * @returns Objeto com agendamentos agrupados por data
 */
export async function getCalendarView(
  month: number,
  year: number,
  sellerId?: number
): Promise<CalendarData> {
  const token = getToken();
  if (!token) {
    throw new Error('Não autenticado');
  }

  const params = new URLSearchParams({
    month: month.toString(),
    year: year.toString(),
  });

  if (sellerId) {
    params.append('seller_id', sellerId.toString());
  }

  const response = await fetch(`${API_URL}/v1/appointments/calendar?${params.toString()}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Erro ao carregar calendário');
  }

  return response.json();
}

/**
 * Retorna detalhes de um agendamento específico.
 *
 * @param id - ID do agendamento
 * @returns Dados do agendamento
 */
export async function getAppointment(id: number): Promise<Appointment> {
  const token = getToken();
  if (!token) {
    throw new Error('Não autenticado');
  }

  const response = await fetch(`${API_URL}/v1/appointments/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Agendamento não encontrado');
  }

  return response.json();
}

/**
 * Cria novo agendamento.
 *
 * @param payload - Dados do agendamento
 * @returns Agendamento criado
 */
export async function createAppointment(payload: CreateAppointmentPayload): Promise<Appointment> {
  const token = getToken();
  if (!token) {
    throw new Error('Não autenticado');
  }

  const response = await fetch(`${API_URL}/v1/appointments`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao criar agendamento');
  }

  return response.json();
}

/**
 * Atualiza agendamento existente.
 *
 * @param id - ID do agendamento
 * @param payload - Dados a atualizar
 * @returns Agendamento atualizado
 */
export async function updateAppointment(
  id: number,
  payload: UpdateAppointmentPayload
): Promise<Appointment> {
  const token = getToken();
  if (!token) {
    throw new Error('Não autenticado');
  }

  const response = await fetch(`${API_URL}/v1/appointments/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao atualizar agendamento');
  }

  return response.json();
}

/**
 * Deleta agendamento.
 *
 * @param id - ID do agendamento
 */
export async function deleteAppointment(id: number): Promise<void> {
  const token = getToken();
  if (!token) {
    throw new Error('Não autenticado');
  }

  const response = await fetch(`${API_URL}/v1/appointments/${id}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao deletar agendamento');
  }
}

/**
 * Confirma agendamento.
 *
 * @param id - ID do agendamento
 * @returns Agendamento confirmado
 */
export async function confirmAppointment(id: number): Promise<Appointment> {
  const token = getToken();
  if (!token) {
    throw new Error('Não autenticado');
  }

  const response = await fetch(`${API_URL}/v1/appointments/${id}/confirm`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao confirmar agendamento');
  }

  return response.json();
}

/**
 * Marca agendamento como completo com resultado.
 *
 * @param id - ID do agendamento
 * @param outcome - Resultado (sale, follow_up, not_interested, rescheduled)
 * @param notes - Notas opcionais
 * @returns Agendamento completo
 */
export async function completeAppointment(
  id: number,
  outcome: 'sale' | 'follow_up' | 'not_interested' | 'rescheduled',
  notes?: string
): Promise<Appointment> {
  const token = getToken();
  if (!token) {
    throw new Error('Não autenticado');
  }

  const response = await fetch(`${API_URL}/v1/appointments/${id}/complete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      outcome,
      outcome_notes: notes,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao completar agendamento');
  }

  return response.json();
}

/**
 * Cancela agendamento.
 *
 * @param id - ID do agendamento
 * @param reason - Motivo do cancelamento (opcional)
 * @returns Agendamento cancelado
 */
export async function cancelAppointment(id: number, reason?: string): Promise<Appointment> {
  const token = getToken();
  if (!token) {
    throw new Error('Não autenticado');
  }

  const response = await fetch(`${API_URL}/v1/appointments/${id}/cancel`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      reason,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao cancelar agendamento');
  }

  return response.json();
}

/**
 * Marca agendamento como "no show" (lead não compareceu).
 *
 * @param id - ID do agendamento
 * @returns Agendamento marcado como no_show
 */
export async function markNoShow(id: number): Promise<Appointment> {
  const token = getToken();
  if (!token) {
    throw new Error('Não autenticado');
  }

  const response = await fetch(`${API_URL}/v1/appointments/${id}/no-show`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao marcar no-show');
  }

  return response.json();
}
