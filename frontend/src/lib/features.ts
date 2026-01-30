/**
 * API Client: Feature Flags
 * ===========================
 *
 * Cliente para gerenciar feature flags do Centro de Controle.
 */

import { getToken } from './auth';

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

interface FeatureFlagsResponse {
  plan_features: Record<string, boolean>;
  overrides: Record<string, boolean>;
  team_features: Record<string, boolean>;
  final_features: Record<string, boolean>;
  plan_name: string;
  user_role: string;
  can_edit: boolean;
}

/**
 * Busca as feature flags do tenant atual.
 */
export async function getFeatures(): Promise<FeatureFlagsResponse> {
  const token = getToken();

  const response = await fetch(`${API_URL}/v1/settings/features`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch features: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Atualiza as feature flags do tenant atual.
 *
 * Apenas admins e gestores podem atualizar.
 */
export async function updateFeatures(features: Record<string, boolean>): Promise<void> {
  const token = getToken();

  const response = await fetch(`${API_URL}/v1/settings/features`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(features),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to update features');
  }
}
