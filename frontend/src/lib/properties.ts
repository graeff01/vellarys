/**
 * API Client: Properties & AI Match (Imóveis e Match Automático)
 * ================================================================
 *
 * Catálogo de imóveis + Match automático com IA.
 */

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token');
}

export interface Property {
  id: number;
  title: string;
  description?: string;
  property_type: string;
  address: string;
  neighborhood?: string;
  city: string;
  state: string;
  size_sqm?: number;
  rooms?: number;
  bathrooms?: number;
  parking_spots?: number;
  features: string[];
  sale_price?: number;
  rent_price?: number;
  condo_fee?: number;
  iptu?: number;
  images: string[];
  video_url?: string;
  virtual_tour_url?: string;
  is_active: boolean;
  is_available: boolean;
}

export interface PropertyMatch extends Property {
  match_score?: number;
}

export interface MatchCriteria {
  property_type?: string;
  min_rooms?: number;
  max_rooms?: number;
  min_price?: number;
  max_price?: number;
  neighborhoods: string[];
  cities: string[];
  required_features: string[];
}

export interface MatchResult {
  message: string;
  criteria: MatchCriteria;
  properties: PropertyMatch[];
  count: number;
}

export interface CreatePropertyPayload {
  title: string;
  description?: string;
  property_type: string;
  address: string;
  neighborhood?: string;
  city: string;
  state: string;
  zip_code?: string;
  latitude?: number;
  longitude?: number;
  size_sqm?: number;
  rooms?: number;
  bathrooms?: number;
  parking_spots?: number;
  floor?: number;
  total_floors?: number;
  features?: string[];
  sale_price?: number;
  rent_price?: number;
  condo_fee?: number;
  iptu?: number;
  images?: string[];
  video_url?: string;
  virtual_tour_url?: string;
}

/**
 * Lista imóveis com filtros
 */
export async function getProperties(filters?: {
  property_type?: string;
  city?: string;
  neighborhood?: string;
  min_rooms?: number;
  max_rooms?: number;
  min_price?: number;
  max_price?: number;
  is_available?: boolean;
}): Promise<Property[]> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const params = new URLSearchParams();
  if (filters?.property_type) params.append('property_type', filters.property_type);
  if (filters?.city) params.append('city', filters.city);
  if (filters?.neighborhood) params.append('neighborhood', filters.neighborhood);
  if (filters?.min_rooms) params.append('min_rooms', filters.min_rooms.toString());
  if (filters?.max_rooms) params.append('max_rooms', filters.max_rooms.toString());
  if (filters?.min_price) params.append('min_price', filters.min_price.toString());
  if (filters?.max_price) params.append('max_price', filters.max_price.toString());
  if (filters?.is_available !== undefined) params.append('is_available', filters.is_available.toString());

  const response = await fetch(
    `${API_URL}/v1/properties?${params.toString()}`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  if (!response.ok) throw new Error('Erro ao carregar imóveis');
  return response.json();
}

/**
 * Busca imóvel por ID
 */
export async function getProperty(id: number): Promise<Property> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const response = await fetch(
    `${API_URL}/v1/properties/${id}`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  if (!response.ok) throw new Error('Imóvel não encontrado');
  return response.json();
}

/**
 * Cria novo imóvel
 */
export async function createProperty(payload: CreatePropertyPayload): Promise<Property> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const response = await fetch(
    `${API_URL}/v1/properties`,
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
    throw new Error(error.detail || 'Erro ao criar imóvel');
  }

  return response.json();
}

/**
 * Atualiza imóvel
 */
export async function updateProperty(
  id: number,
  payload: Partial<CreatePropertyPayload>
): Promise<Property> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const response = await fetch(
    `${API_URL}/v1/properties/${id}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    }
  );

  if (!response.ok) throw new Error('Erro ao atualizar imóvel');
  return response.json();
}

/**
 * Deleta imóvel
 */
export async function deleteProperty(id: number): Promise<void> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const response = await fetch(
    `${API_URL}/v1/properties/${id}`,
    {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  if (!response.ok) throw new Error('Erro ao deletar imóvel');
}

/**
 * Match automático com IA
 *
 * Recebe mensagem do lead e retorna imóveis compatíveis.
 *
 * Exemplo:
 * "Procuro casa 3 quartos zona norte até 500k"
 * → Retorna imóveis que correspondem aos critérios
 */
export async function matchProperties(message: string): Promise<MatchResult> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const response = await fetch(
    `${API_URL}/v1/properties/match`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ message })
    }
  );

  if (!response.ok) throw new Error('Erro no match automático');
  return response.json();
}

/**
 * Extrai critérios de busca de uma mensagem
 */
export async function extractCriteria(message: string): Promise<MatchCriteria> {
  const token = getToken();
  if (!token) throw new Error('Não autenticado');

  const response = await fetch(
    `${API_URL}/v1/properties/extract-criteria`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ message })
    }
  );

  if (!response.ok) throw new Error('Erro ao extrair critérios');
  return response.json();
}
