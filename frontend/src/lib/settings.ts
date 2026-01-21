import { getToken } from './auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// =============================================================================
// TYPES - IDENTIDADE EMPRESARIAL
// =============================================================================

export interface ToneStyle {
  tone: 'formal' | 'cordial' | 'informal' | 'tecnico';
  personality_traits: string[];
  communication_style: string;
  avoid_phrases: string[];
  use_phrases: string[];
}

export interface TargetAudience {
  description: string;
  segments: string[];
  pain_points: string[];
}

export interface IdentitySettings {
  description: string;
  products_services: string[];
  not_offered: string[];
  tone_style: ToneStyle;
  target_audience: TargetAudience;
  business_rules: string[];
  differentials: string[];
  keywords: string[];
  required_questions: string[];
  required_info: string[];
  additional_context: string;
}

// =============================================================================
// TYPES - CONFIGURAÇÕES GERAIS
// =============================================================================

export interface BasicSettings {
  niche: string;
  company_name: string;
}

export interface AIBehaviorSettings {
  custom_questions: string[];
  custom_rules: string[];
  greeting_message: string;
  farewell_message: string;
}

export interface HandoffSettings {
  enabled: boolean;
  manager_whatsapp: string;
  manager_name: string;
  triggers: string[];
  max_messages_before_handoff: number;
  transfer_message: string;
}

export interface DaySchedule {
  open: string;
  close: string;
  enabled: boolean;
}

export interface BusinessHoursSettings {
  enabled: boolean;
  timezone: string;
  schedule: Record<string, DaySchedule>;
  out_of_hours_message: string;
  out_of_hours_behavior: 'message_only' | 'collect_info' | 'redirect';
}

export interface FAQItem {
  question: string;
  answer: string;
}

export interface FAQSettings {
  enabled: boolean;
  items: FAQItem[];
}

export interface ScopeSettings {
  enabled: boolean;
  description: string;
  allowed_topics: string[];
  blocked_topics: string[];
  out_of_scope_message: string;
}

export interface DistributionSettings {
  method: string;
  fallback: string;
  respect_daily_limit: boolean;
  respect_availability: boolean;
  notify_manager_copy: boolean;
  notify_broker_raiox: boolean;
  min_messages_broker_raiox: number;
  last_seller_index: number;
}

export interface PriceGuard {
  enabled: boolean;
  behavior: 'redirect' | 'collect_first' | 'allow';
  message: string;
}

export interface CompetitorGuard {
  enabled: boolean;
  competitors: string[];
  behavior: 'neutral' | 'redirect' | 'highlight_differentials';
}

export interface ScopeGuard {
  enabled: boolean;
  strictness: 'low' | 'medium' | 'high';
}

export interface InsistGuard {
  enabled: boolean;
  max_attempts: number;
  escalate_after: boolean;
}

export interface GuardrailsSettings {
  price_guard: PriceGuard;
  competitor_guard: CompetitorGuard;
  scope_guard: ScopeGuard;
  insist_guard: InsistGuard;
}

export interface MessagesSettings {
  greeting: string;
  farewell: string;
  out_of_hours: string;
  out_of_scope: string;
  handoff_notice: string;
  qualification_complete: string;
  waiting_response: string;
}

// =============================================================================
// TYPES - FOLLOW-UP AUTOMÁTICO (NOVO)
// =============================================================================

export interface FollowUpMessages {
  attempt_1: string;
  attempt_2: string;
  attempt_3: string;
}

export interface FollowUpAllowedHours {
  start: string;
  end: string;
}

export interface FollowUpSettings {
  enabled: boolean;
  inactivity_hours: number;
  max_attempts: number;
  interval_hours: number;
  respect_business_hours: boolean;
  messages: FollowUpMessages;
  exclude_statuses: string[];
  exclude_qualifications: string[];
  allowed_hours: FollowUpAllowedHours;
}

// =============================================================================
// TYPES - VOICE-FIRST / RESPOSTA EM ÁUDIO (NOVO)
// =============================================================================

export interface VoiceResponseSettings {
  enabled: boolean;
  voice: string;
  speed: number;
  always_audio: boolean;
  max_chars_for_audio: number;
  persona_name: string;
}

export interface VoiceOption {
  id: string;
  name: string;
  description: string;
  gender: string;
  recommended: boolean;
  preview_text?: string;
}

// =============================================================================
// TYPES - SETTINGS COMPLETO
// =============================================================================

export interface TenantSettings {
  identity: IdentitySettings;
  basic: BasicSettings;
  ai_behavior: AIBehaviorSettings;
  handoff: HandoffSettings;
  business_hours: BusinessHoursSettings;
  faq: FAQSettings;
  scope: ScopeSettings;
  distribution: DistributionSettings;
  guardrails: GuardrailsSettings;
  messages: MessagesSettings;
  follow_up: FollowUpSettings;
  voice_response: VoiceResponseSettings;  // Voice-First
}

// =============================================================================
// TYPES - OPÇÕES
// =============================================================================

export interface ToneOption {
  id: string;
  name: string;
  description: string;
  icon: string;
  examples: string[];
}

export interface PersonalityTrait {
  id: string;
  name: string;
  description: string;
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

export interface NicheOption {
  id: string;
  name: string;
  description: string;
  icon?: string;
}

export interface RequiredInfoOption {
  id: string;
  name: string;
  description: string;
}

export interface SettingsOptions {
  niches: NicheOption[];
  tones: ToneOption[];
  personality_traits: PersonalityTrait[];
  distribution_methods: DistributionMethod[];
  fallback_options: FallbackOption[];
  required_info_options: RequiredInfoOption[];
  voice_options: VoiceOption[];  // Voice-First
}

// =============================================================================
// TYPES - RESPONSES
// =============================================================================

export interface TenantInfo {
  id: number;
  name: string;
  slug: string;
  plan: string;
}

export interface SettingsResponse {
  tenant: TenantInfo;
  settings: TenantSettings;
  options: SettingsOptions;
}

export interface IdentityResponse {
  identity: IdentitySettings;
  basic: BasicSettings;
  options: {
    tones: ToneOption[];
    personality_traits: PersonalityTrait[];
    required_info_options: RequiredInfoOption[];
  };
}

export interface UpdateResponse {
  success: boolean;
  message: string;
  tenant: TenantInfo;
  settings: TenantSettings;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

export async function getSettings(targetTenantId?: number): Promise<SettingsResponse> {
  const token = getToken();
  const url = new URL(`${API_URL}/settings`);
  if (targetTenantId) {
    url.searchParams.set('target_tenant_id', targetTenantId.toString());
  }

  const response = await fetch(url.toString(), {
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

export async function updateSettings(
  data: Partial<TenantSettings> & { tenant_name?: string },
  targetTenantId?: number
): Promise<UpdateResponse> {
  const token = getToken();
  const url = new URL(`${API_URL}/settings`);
  if (targetTenantId) {
    url.searchParams.set('target_tenant_id', targetTenantId.toString());
  }

  const response = await fetch(url.toString(), {
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

  return response.json();
}

export async function getIdentitySettings(targetTenantId?: number): Promise<IdentityResponse> {
  const token = getToken();
  const url = new URL(`${API_URL}/settings/identity`);
  if (targetTenantId) {
    url.searchParams.set('target_tenant_id', targetTenantId.toString());
  }

  const response = await fetch(url.toString(), {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('Erro ao carregar identidade');
  }

  return response.json();
}

export async function updateIdentitySettings(data: {
  identity?: Partial<IdentitySettings>;
  basic?: Partial<BasicSettings>;
}): Promise<{ success: boolean; identity: IdentitySettings; basic: BasicSettings }> {
  const token = getToken();

  const response = await fetch(`${API_URL}/settings/identity`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error('Erro ao salvar identidade');
  }

  return response.json();
}

export async function getAIContext(): Promise<Record<string, unknown>> {
  const token = getToken();

  const response = await fetch(`${API_URL}/settings/ai-context`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('Erro ao carregar contexto da IA');
  }

  return response.json();
}

export async function getNiches(): Promise<NicheOption[]> {
  const token = getToken();

  const response = await fetch(`${API_URL}/settings/niches`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('Erro ao carregar nichos');
  }

  return response.json();
}

export async function getDistributionOptions(): Promise<{
  methods: DistributionMethod[];
  fallbacks: FallbackOption[];
}> {
  const token = getToken();

  const response = await fetch(`${API_URL}/settings/distribution-options`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('Erro ao carregar opções de distribuição');
  }

  return response.json();
}

export async function getToneOptions(): Promise<{
  tones: ToneOption[];
  personality_traits: PersonalityTrait[];
}> {
  const response = await fetch(`${API_URL}/settings/tone-options`, {
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('Erro ao carregar opções de tom');
  }

  return response.json();
}

// =============================================================================
// HELPERS
// =============================================================================

export const DEFAULT_IDENTITY: IdentitySettings = {
  description: '',
  products_services: [],
  not_offered: [],
  tone_style: {
    tone: 'cordial',
    personality_traits: [],
    communication_style: '',
    avoid_phrases: [],
    use_phrases: [],
  },
  target_audience: {
    description: '',
    segments: [],
    pain_points: [],
  },
  business_rules: [],
  differentials: [],
  keywords: [],
  required_questions: [],
  required_info: [],
  additional_context: '',
};

export const DEFAULT_BASIC: BasicSettings = {
  niche: 'services',
  company_name: '',
};

export const DEFAULT_FOLLOW_UP: FollowUpSettings = {
  enabled: false,
  inactivity_hours: 24,
  max_attempts: 3,
  interval_hours: 24,
  respect_business_hours: true,
  messages: {
    attempt_1: "Oi {nome}! Vi que você se interessou por {interesse}. Posso te ajudar com mais alguma informação? 😊",
    attempt_2: "Oi {nome}! Ainda está procurando {interesse}? Estou aqui se precisar!",
    attempt_3: "{nome}, vou encerrar nosso atendimento por aqui. Se precisar, é só chamar novamente! 👋",
  },
  exclude_statuses: ['converted', 'lost', 'handed_off'],
  exclude_qualifications: [],
  allowed_hours: {
    start: "08:00",
    end: "20:00",
  },
};

export const DEFAULT_VOICE_RESPONSE: VoiceResponseSettings = {
  enabled: false,
  voice: 'nova',
  speed: 0.95,  // Velocidade ligeiramente mais lenta para soar mais natural
  always_audio: false,
  max_chars_for_audio: 500,
  persona_name: 'Ana',
};

export const DEFAULT_VOICE_OPTIONS: VoiceOption[] = [
  {
    id: 'nova',
    name: 'Nova',
    description: 'Feminina, jovem e natural',
    gender: 'female',
    recommended: true,
  },
  {
    id: 'shimmer',
    name: 'Shimmer',
    description: 'Feminina, calorosa e acolhedora',
    gender: 'female',
    recommended: false,
  },
  {
    id: 'alloy',
    name: 'Alloy',
    description: 'Neutra, clara e amigável',
    gender: 'neutral',
    recommended: false,
  },
  {
    id: 'echo',
    name: 'Echo',
    description: 'Masculina, confiante e amigável',
    gender: 'male',
    recommended: false,
  },
  {
    id: 'onyx',
    name: 'Onyx',
    description: 'Masculina, séria e profissional',
    gender: 'male',
    recommended: false,
  },
  {
    id: 'fable',
    name: 'Fable',
    description: 'Expressiva, dinâmica e entusiasmada',
    gender: 'neutral',
    recommended: false,
  },
];