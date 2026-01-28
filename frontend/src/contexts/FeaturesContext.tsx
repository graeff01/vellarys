'use client';

/**
 * FeaturesContext - Sistema de Controle de Acesso por Features
 * ============================================================
 *
 * Inspirado em grandes players:
 * - Salesforce: Permission hierarchy
 * - HubSpot: Feature tiers com graceful degradation
 * - Intercom: Real-time feature flags
 *
 * Este context gerencia todas as features disponíveis para o tenant,
 * permitindo controle granular do que cada usuário pode acessar.
 */

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

// ============================================================================
// TIPOS E INTERFACES
// ============================================================================

/**
 * Lista completa de features do sistema.
 * Sincronizada com o backend (settings.py)
 */
export interface Features {
  // Core Business - Básico (todos os planos)
  calendar_enabled: boolean;
  templates_enabled: boolean;
  notes_enabled: boolean;
  attachments_enabled: boolean;

  // Communication
  sse_enabled: boolean;
  search_enabled: boolean;

  // Analytics & Intelligence (Premium+)
  metrics_enabled: boolean;
  archive_enabled: boolean;
  voice_response_enabled: boolean;

  // AI Features (Premium+)
  ai_auto_handoff_enabled: boolean;
  ai_sentiment_alerts_enabled: boolean;
  copilot_enabled: boolean;

  // Governance & Security (Premium+)
  security_ghost_mode_enabled: boolean;
  security_export_lock_enabled: boolean;
  distrib_auto_assign_enabled: boolean;

  // Enterprise Features
  ai_guard_enabled: boolean;
  reengagement_enabled: boolean;
  knowledge_base_enabled: boolean;

  // Extras
  simulator_enabled: boolean;
  reports_enabled: boolean;
  api_access_enabled: boolean;
}

/**
 * Metadata de cada feature para UI
 */
export interface FeatureMetadata {
  key: keyof Features;
  name: string;
  description: string;
  category: 'core' | 'communication' | 'analytics' | 'ai' | 'security' | 'enterprise';
  minPlan: 'starter' | 'premium' | 'enterprise';
  icon?: string;
}

/**
 * Estado do context
 */
interface FeaturesState {
  features: Features | null;
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  plan: string | null;
}

/**
 * Ações disponíveis no context
 */
interface FeaturesContextType extends FeaturesState {
  // Verificações
  isEnabled: (feature: keyof Features) => boolean;
  canAccess: (feature: keyof Features) => boolean;
  hasAnyFeature: (features: (keyof Features)[]) => boolean;
  hasAllFeatures: (features: (keyof Features)[]) => boolean;

  // Ações
  refresh: () => Promise<void>;
  invalidate: () => void;

  // Metadata
  getFeatureMetadata: (feature: keyof Features) => FeatureMetadata | undefined;
  getFeaturesByCategory: (category: FeatureMetadata['category']) => FeatureMetadata[];
}

// ============================================================================
// DEFAULTS E CONSTANTES
// ============================================================================

/**
 * Features padrão (tudo desabilitado por segurança)
 */
const DEFAULT_FEATURES: Features = {
  // Core
  calendar_enabled: false,
  templates_enabled: false,
  notes_enabled: false,
  attachments_enabled: false,

  // Communication
  sse_enabled: false,
  search_enabled: false,

  // Analytics
  metrics_enabled: false,
  archive_enabled: false,
  voice_response_enabled: false,

  // AI
  ai_auto_handoff_enabled: false,
  ai_sentiment_alerts_enabled: false,
  copilot_enabled: false,

  // Security
  security_ghost_mode_enabled: false,
  security_export_lock_enabled: false,
  distrib_auto_assign_enabled: false,

  // Enterprise
  ai_guard_enabled: false,
  reengagement_enabled: false,
  knowledge_base_enabled: false,

  // Extras
  simulator_enabled: false,
  reports_enabled: false,
  api_access_enabled: false,
};

/**
 * Metadata de todas as features para UI
 */
export const FEATURES_METADATA: FeatureMetadata[] = [
  // Core Business
  { key: 'calendar_enabled', name: 'Calendário', description: 'Agendar compromissos e eventos', category: 'core', minPlan: 'starter' },
  { key: 'templates_enabled', name: 'Templates', description: 'Mensagens pré-definidas', category: 'core', minPlan: 'starter' },
  { key: 'notes_enabled', name: 'Notas', description: 'Anotações nos leads', category: 'core', minPlan: 'starter' },
  { key: 'attachments_enabled', name: 'Anexos', description: 'Enviar arquivos', category: 'core', minPlan: 'starter' },

  // Communication
  { key: 'sse_enabled', name: 'Real-time', description: 'Atualizações em tempo real', category: 'communication', minPlan: 'starter' },
  { key: 'search_enabled', name: 'Busca', description: 'Busca avançada de leads', category: 'communication', minPlan: 'starter' },

  // Analytics & Intelligence
  { key: 'metrics_enabled', name: 'Métricas', description: 'Dashboard de métricas', category: 'analytics', minPlan: 'premium' },
  { key: 'archive_enabled', name: 'Arquivo', description: 'Arquivar conversas', category: 'analytics', minPlan: 'premium' },
  { key: 'voice_response_enabled', name: 'Voz', description: 'Respostas por áudio', category: 'analytics', minPlan: 'premium' },
  { key: 'reports_enabled', name: 'Relatórios', description: 'Relatórios detalhados', category: 'analytics', minPlan: 'premium' },

  // AI Features
  { key: 'ai_auto_handoff_enabled', name: 'Handoff Auto', description: 'Transferência automática para humano', category: 'ai', minPlan: 'premium' },
  { key: 'ai_sentiment_alerts_enabled', name: 'Alertas de Sentimento', description: 'Detectar leads frustrados', category: 'ai', minPlan: 'premium' },
  { key: 'copilot_enabled', name: 'Copilot IA', description: 'Assistente inteligente para gestores', category: 'ai', minPlan: 'premium' },
  { key: 'simulator_enabled', name: 'Simulador IA', description: 'Testar conversas com a IA', category: 'ai', minPlan: 'premium' },

  // Security & Governance
  { key: 'security_ghost_mode_enabled', name: 'Modo Fantasma', description: 'Ocultar presença online', category: 'security', minPlan: 'premium' },
  { key: 'security_export_lock_enabled', name: 'Bloqueio de Export', description: 'Impedir exportação de dados', category: 'security', minPlan: 'starter' },
  { key: 'distrib_auto_assign_enabled', name: 'Distribuição Auto', description: 'Atribuir leads automaticamente', category: 'security', minPlan: 'premium' },

  // Enterprise
  { key: 'ai_guard_enabled', name: 'AI Guard', description: 'Proteção avançada de IA', category: 'enterprise', minPlan: 'enterprise' },
  { key: 'reengagement_enabled', name: 'Reengajamento', description: 'Follow-up automático', category: 'enterprise', minPlan: 'enterprise' },
  { key: 'knowledge_base_enabled', name: 'Base de Conhecimento', description: 'Documentos para a IA', category: 'enterprise', minPlan: 'enterprise' },
  { key: 'api_access_enabled', name: 'Acesso API', description: 'Integração via API', category: 'enterprise', minPlan: 'enterprise' },
];

// ============================================================================
// CONTEXT
// ============================================================================

const FeaturesContext = createContext<FeaturesContextType | undefined>(undefined);

// ============================================================================
// API
// ============================================================================

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

async function fetchFeatures(): Promise<{ features: Features; plan: string }> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

  if (!token) {
    throw new Error('Não autenticado');
  }

  const response = await fetch(`${API_URL}/v1/settings/features`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Sessão expirada');
    }
    throw new Error('Erro ao carregar features');
  }

  const data = await response.json();

  // O backend retorna { plan_features, overrides, final_features }
  // Vamos usar final_features que já é o merge
  return {
    features: data.final_features || data.features || data,
    plan: data.plan || 'starter',
  };
}

// ============================================================================
// PROVIDER
// ============================================================================

interface FeaturesProviderProps {
  children: ReactNode;
  /**
   * Se true, carrega features automaticamente no mount
   * @default true
   */
  autoLoad?: boolean;
  /**
   * Intervalo em ms para refresh automático (0 = desabilitado)
   * @default 300000 (5 minutos)
   */
  refreshInterval?: number;
}

export function FeaturesProvider({
  children,
  autoLoad = true,
  refreshInterval = 300000 // 5 minutos
}: FeaturesProviderProps) {
  const [state, setState] = useState<FeaturesState>({
    features: null,
    isLoading: true,
    error: null,
    lastUpdated: null,
    plan: null,
  });

  /**
   * Carrega features do backend
   */
  const refresh = useCallback(async () => {
    // Verifica se tem token antes de tentar
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (!token) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        features: DEFAULT_FEATURES,
        error: null
      }));
      return;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const { features, plan } = await fetchFeatures();
      setState({
        features: { ...DEFAULT_FEATURES, ...features },
        isLoading: false,
        error: null,
        lastUpdated: new Date(),
        plan,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro desconhecido';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
        // Manter features anteriores em caso de erro de rede
        features: prev.features || DEFAULT_FEATURES,
      }));
    }
  }, []);

  /**
   * Invalida cache e força reload na próxima verificação
   */
  const invalidate = useCallback(() => {
    setState(prev => ({ ...prev, lastUpdated: null }));
  }, []);

  /**
   * Verifica se feature está habilitada
   */
  const isEnabled = useCallback((feature: keyof Features): boolean => {
    if (!state.features) return false;
    return state.features[feature] === true;
  }, [state.features]);

  /**
   * Alias para isEnabled (para compatibilidade)
   */
  const canAccess = useCallback((feature: keyof Features): boolean => {
    return isEnabled(feature);
  }, [isEnabled]);

  /**
   * Verifica se tem QUALQUER uma das features
   */
  const hasAnyFeature = useCallback((features: (keyof Features)[]): boolean => {
    return features.some(f => isEnabled(f));
  }, [isEnabled]);

  /**
   * Verifica se tem TODAS as features
   */
  const hasAllFeatures = useCallback((features: (keyof Features)[]): boolean => {
    return features.every(f => isEnabled(f));
  }, [isEnabled]);

  /**
   * Retorna metadata de uma feature
   */
  const getFeatureMetadata = useCallback((feature: keyof Features): FeatureMetadata | undefined => {
    return FEATURES_METADATA.find(f => f.key === feature);
  }, []);

  /**
   * Retorna features de uma categoria
   */
  const getFeaturesByCategory = useCallback((category: FeatureMetadata['category']): FeatureMetadata[] => {
    return FEATURES_METADATA.filter(f => f.category === category);
  }, []);

  // Auto-load no mount
  useEffect(() => {
    if (autoLoad) {
      refresh();
    }
  }, [autoLoad, refresh]);

  // Refresh automático
  useEffect(() => {
    if (refreshInterval <= 0) return;

    const interval = setInterval(() => {
      refresh();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval, refresh]);

  // Refresh quando a janela ganha foco (volta de outra aba)
  useEffect(() => {
    const handleFocus = () => {
      // Só faz refresh se o último foi há mais de 1 minuto
      if (state.lastUpdated) {
        const diff = Date.now() - state.lastUpdated.getTime();
        if (diff > 60000) {
          refresh();
        }
      }
    };

    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [state.lastUpdated, refresh]);

  const value: FeaturesContextType = {
    ...state,
    isEnabled,
    canAccess,
    hasAnyFeature,
    hasAllFeatures,
    refresh,
    invalidate,
    getFeatureMetadata,
    getFeaturesByCategory,
  };

  return (
    <FeaturesContext.Provider value={value}>
      {children}
    </FeaturesContext.Provider>
  );
}

// ============================================================================
// HOOK
// ============================================================================

/**
 * Hook para acessar o contexto de features.
 *
 * @example
 * ```tsx
 * const { isEnabled, canAccess } = useFeatures();
 *
 * if (isEnabled('calendar_enabled')) {
 *   // Mostrar calendário
 * }
 * ```
 */
export function useFeatures(): FeaturesContextType {
  const context = useContext(FeaturesContext);

  if (context === undefined) {
    throw new Error('useFeatures must be used within a FeaturesProvider');
  }

  return context;
}

// ============================================================================
// EXPORTS
// ============================================================================

export { FeaturesContext };
export type { FeaturesContextType, FeaturesState };
