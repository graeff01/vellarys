import { getToken } from './auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface DistributionConfig {
  method: string;
  fallback: string;
  respect_daily_limit: boolean;
  respect_availability: boolean;
  notify_manager_copy: boolean;
  last_seller_index: number;
}

export interface DistributionMethod {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface FallbackOption {
  id: string;
  name: string;
  description: string;
}

export interface TenantSettings {
  // Básico
  niche: string;
  company_name: string;
  tone: string;
  
  // Personalização
  custom_questions: string[];
  custom_rules: string[];
  
  // Handoff
  manager_whatsapp: string;
  manager_name: string;
  handoff_enabled: boolean;
  handoff_triggers: string[];
  max_messages_before_handoff: number;
  
  // Horário
  business_hours_enabled: boolean;
  business_hours: Record<string, {open: string, close: string, enabled: boolean}>;
  out_of_hours_message: string;
  
  // FAQ
  faq_enabled: boolean;
  faq_items: Array<{question: string, answer: string}>;
  
  // Escopo
  scope_enabled: boolean;
  scope_description: string;
  out_of_scope_message: string;
  
  // Distribuição
  distribution: DistributionConfig;
}

export interface SettingsResponse {
  tenant: {
    id: number;
    name: string;
    slug: string;
    plan: string;
  };
  settings: TenantSettings;
  available_niches: Array<{
    id: string;
    name: string;
    description: string;
  }>;
  distribution_methods: DistributionMethod[];
  fallback_options: FallbackOption[];
}

export async function getSettings(): Promise<SettingsResponse> {
  const token = getToken();
  
  const response = await fetch(`${API_URL}/settings`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('Erro ao carregar configurações');
  }

  return response.json();
}

export async function updateSettings(data: Partial<TenantSettings> & { name?: string }): Promise<void> {
  const token = getToken();
  
  const response = await fetch(`${API_URL}/settings`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error('Erro ao salvar configurações');
  }
}