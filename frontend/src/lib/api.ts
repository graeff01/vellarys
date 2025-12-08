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

// === EMPREENDIMENTOS (apenas para imobiliárias) ===

export interface Empreendimento {
  id: number;
  nome: string;
  slug: string;
  status: string;
  status_label?: string;
  ativo: boolean;
  url_landing_page?: string;
  imagem_destaque?: string;
  gatilhos: string[];
  prioridade: number;
  endereco?: string;
  bairro?: string;
  cidade?: string;
  estado?: string;
  cep?: string;
  descricao_localizacao?: string;
  descricao?: string;
  tipologias: string[];
  metragem_minima?: number;
  metragem_maxima?: number;
  faixa_metragem?: string;
  torres?: number;
  andares?: number;
  unidades_por_andar?: number;
  total_unidades?: number;
  vagas_minima?: number;
  vagas_maxima?: number;
  previsao_entrega?: string;
  preco_minimo?: number;
  preco_maximo?: number;
  faixa_preco?: string;
  aceita_financiamento: boolean;
  aceita_fgts: boolean;
  aceita_permuta: boolean;
  aceita_consorcio: boolean;
  condicoes_especiais?: string;
  itens_lazer: string[];
  diferenciais: string[];
  perguntas_qualificacao: string[];
  instrucoes_ia?: string;
  vendedor_id?: number;
  vendedor_nome?: string;
  metodo_distribuicao?: string;
  notificar_gestor: boolean;
  whatsapp_notificacao?: string;
  total_leads: number;
  leads_qualificados: number;
  leads_convertidos: number;
  taxa_conversao?: number;
  created_at?: string;
  updated_at?: string;
}

export interface EmpreendimentoCreate {
  nome: string;
  status?: string;
  url_landing_page?: string;
  imagem_destaque?: string;
  gatilhos?: string[];
  prioridade?: number;
  endereco?: string;
  bairro?: string;
  cidade?: string;
  estado?: string;
  cep?: string;
  descricao_localizacao?: string;
  descricao?: string;
  tipologias?: string[];
  metragem_minima?: number;
  metragem_maxima?: number;
  torres?: number;
  andares?: number;
  unidades_por_andar?: number;
  total_unidades?: number;
  vagas_minima?: number;
  vagas_maxima?: number;
  previsao_entrega?: string;
  preco_minimo?: number;
  preco_maximo?: number;
  aceita_financiamento?: boolean;
  aceita_fgts?: boolean;
  aceita_permuta?: boolean;
  aceita_consorcio?: boolean;
  condicoes_especiais?: string;
  itens_lazer?: string[];
  diferenciais?: string[];
  perguntas_qualificacao?: string[];
  instrucoes_ia?: string;
  vendedor_id?: number;
  metodo_distribuicao?: string;
  notificar_gestor?: boolean;
  whatsapp_notificacao?: string;
}

// Verifica se tenant tem acesso a empreendimentos
export async function checkEmpreendimentosAccess() {
  const slug = getTenantSlug();
  return request(`/empreendimentos/check-access?tenant_slug=${slug}`);
}


// Estatísticas dos empreendimentos
export async function getEmpreendimentosStats() {
  return request('/empreendimentos/stats');
}

// Lista empreendimentos
export async function getEmpreendimentos(params?: {
  ativo?: boolean;
  status?: string;
  search?: string;
}): Promise<{ empreendimentos: Empreendimento[]; total: number }> {
  const searchParams = new URLSearchParams();
  
  if (params?.ativo !== undefined) searchParams.set('ativo', params.ativo.toString());
  if (params?.status) searchParams.set('status', params.status);
  if (params?.search) searchParams.set('search', params.search);
  
  const query = searchParams.toString();
  return request(`/empreendimentos${query ? `?${query}` : ''}`);
}

// Busca empreendimento por ID
export async function getEmpreendimento(id: number): Promise<Empreendimento> {
  return request(`/empreendimentos/${id}`);
}

// Cria empreendimento
export async function createEmpreendimento(data: EmpreendimentoCreate) {
  return request('/empreendimentos', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// Atualiza empreendimento
export async function updateEmpreendimento(id: number, data: Partial<EmpreendimentoCreate>) {
  return request(`/empreendimentos/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// Remove empreendimento
export async function deleteEmpreendimento(id: number) {
  return request(`/empreendimentos/${id}`, {
    method: 'DELETE',
  });
}

// Ativa/desativa empreendimento
export async function toggleEmpreendimentoStatus(id: number) {
  return request(`/empreendimentos/${id}/toggle-status`, {
    method: 'POST',
  });
}

// Testa detecção de gatilhos (debug)
export async function detectEmpreendimento(message: string) {
  return request(`/empreendimentos/detect?message=${encodeURIComponent(message)}`, {
    method: 'POST',
  });
}

