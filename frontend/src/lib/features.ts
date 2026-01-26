/**
 * API Client: Feature Flags (Centro de Controle)
 * ================================================
 *
 * Gerencia as funcionalidades que podem ser ativadas/desativadas
 * pelo gestor no Centro de Controle.
 */

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token');
}

export interface Features {
  // Core Features
  calendar_enabled: boolean;
  templates_enabled: boolean;
  notes_enabled: boolean;
  attachments_enabled: boolean;

  // Advanced Features
  sse_enabled: boolean;
  search_enabled: boolean;
  metrics_enabled: boolean;
  archive_enabled: boolean;
  voice_response_enabled: boolean;

  // Experimental Features
  ai_guard_enabled: boolean;
  reengagement_enabled: boolean;
  knowledge_base_enabled: boolean;
}

/**
 * Carrega feature flags do tenant atual.
 *
 * @returns Features habilitadas/desabilitadas
 */
export async function getFeatures(): Promise<Features> {
  const token = getToken();
  if (!token) {
    throw new Error('Não autenticado');
  }

  const response = await fetch(`${API_URL}/v1/settings/features`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Erro ao carregar features');
  }

  return response.json();
}

/**
 * Atualiza feature flags (apenas admin/manager).
 *
 * @param features - Features a atualizar (parcial ou completo)
 * @returns Confirmação de sucesso com features atualizadas
 */
export async function updateFeatures(features: Partial<Features>): Promise<{
  success: boolean;
  message: string;
  features: Features;
}> {
  const token = getToken();
  if (!token) {
    throw new Error('Não autenticado');
  }

  const response = await fetch(`${API_URL}/v1/settings/features`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(features),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao atualizar features');
  }

  return response.json();
}

/**
 * Verifica se uma feature específica está habilitada.
 *
 * @param featureName - Nome da feature (ex: "calendar_enabled")
 * @returns True se habilitada, false caso contrário
 */
export async function isFeatureEnabled(featureName: keyof Features): Promise<boolean> {
  const features = await getFeatures();
  return features[featureName] ?? false;
}
