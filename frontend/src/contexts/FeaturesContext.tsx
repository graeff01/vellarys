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
import { getUser } from '@/lib/auth';

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
  userRole: string | null;
  isSuperAdmin: boolean;
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
 * Features TODAS HABILITADAS (para SuperAdmin)
 * SuperAdmin tem acesso total ao sistema
 */
const ALL_FEATURES_ENABLED: Features = {
  // Core
  calendar_enabled: true,
  templates_enabled: true,
  notes_enabled: true,
  attachments_enabled: true,

  // Communication
  sse_enabled: true,
  search_enabled: true,

  // Analytics
  metrics_enabled: true,
  archive_enabled: true,
  voice_response_enabled: true,

  // AI
  ai_auto_handoff_enabled: true,
  ai_sentiment_alerts_enabled: true,
  copilot_enabled: true,

  // Security - Locks desabilitados para superadmin ter acesso
  security_ghost_mode_enabled: true,
  security_export_lock_enabled: false, // FALSE = export liberado
  distrib_auto_assign_enabled: true,

  // Enterprise
  ai_guard_enabled: true,
  reengagement_enabled: true,
  knowledge_base_enabled: true,

  // Extras
  simulator_enabled: true,
  reports_enabled: true,
  api_access_enabled: true,
};

/**
 * Metadata de todas as features para UI
 * Sincronizado com backend PLAN_FEATURES
 *
 * Planos:
 * 🟢 starter = Essencial (básico)
 * 🔵 premium = Profissional (intermediário)
 * 🟣 enterprise = Completo (máximo)
 */
export const FEATURES_METADATA: FeatureMetadata[] = [
  // ==========================================================================
  // 🟢 STARTER - Core Features (disponível em todos os planos)
  // ==========================================================================
  { key: 'calendar_enabled', name: 'Calendário', description: 'Agenda de compromissos e visitas', category: 'core', minPlan: 'starter' },
  { key: 'templates_enabled', name: 'Templates', description: 'Respostas rápidas personalizadas', category: 'core', minPlan: 'starter' },
  { key: 'notes_enabled', name: 'Notas', description: 'Anotações internas nos leads', category: 'core', minPlan: 'starter' },
  { key: 'attachments_enabled', name: 'Anexos', description: 'Envio de arquivos e imagens', category: 'core', minPlan: 'starter' },
  { key: 'sse_enabled', name: 'Tempo Real', description: 'Atualizações instantâneas', category: 'communication', minPlan: 'starter' },
  { key: 'search_enabled', name: 'Busca', description: 'Busca avançada de leads', category: 'communication', minPlan: 'starter' },

  // ==========================================================================
  // 🔵 PREMIUM - Analytics & IA (a partir do Premium)
  // ==========================================================================
  { key: 'metrics_enabled', name: 'Dashboard', description: 'Métricas e KPIs em tempo real', category: 'analytics', minPlan: 'premium' },
  { key: 'archive_enabled', name: 'Arquivo', description: 'Arquivamento de conversas antigas', category: 'analytics', minPlan: 'premium' },
  { key: 'voice_response_enabled', name: 'Áudio IA', description: 'Respostas em áudio da IA', category: 'analytics', minPlan: 'premium' },
  { key: 'reports_enabled', name: 'Relatórios', description: 'Relatórios detalhados e exportação', category: 'analytics', minPlan: 'premium' },
  { key: 'ai_auto_handoff_enabled', name: 'Handoff Inteligente', description: 'Transferência automática para humano', category: 'ai', minPlan: 'premium' },
  { key: 'ai_sentiment_alerts_enabled', name: 'Detector de Sentimento', description: 'Alertas de leads frustrados', category: 'ai', minPlan: 'premium' },
  { key: 'copilot_enabled', name: 'Vellarys Copilot', description: 'Assistente IA para gestores', category: 'ai', minPlan: 'premium' },
  { key: 'simulator_enabled', name: 'Simulador IA', description: 'Teste conversas antes de ativar', category: 'ai', minPlan: 'premium' },
  { key: 'security_ghost_mode_enabled', name: 'Modo Fantasma', description: 'Oculta presença online', category: 'security', minPlan: 'premium' },
  { key: 'distrib_auto_assign_enabled', name: 'Distribuição Auto', description: 'Atribuição automática de leads', category: 'security', minPlan: 'premium' },

  // ==========================================================================
  // 🟣 ENTERPRISE - Recursos Avançados (exclusivo Enterprise)
  // ==========================================================================
  { key: 'ai_guard_enabled', name: 'AI Guard', description: 'Guardrails avançados para IA', category: 'enterprise', minPlan: 'enterprise' },
  { key: 'reengagement_enabled', name: 'Reengajamento', description: 'Follow-up automático inteligente', category: 'enterprise', minPlan: 'enterprise' },
  { key: 'knowledge_base_enabled', name: 'Base de Conhecimento', description: 'RAG - IA aprende seus documentos', category: 'enterprise', minPlan: 'enterprise' },
  { key: 'api_access_enabled', name: 'API Access', description: 'Integração via API REST', category: 'enterprise', minPlan: 'enterprise' },

  // ==========================================================================
  // 🔒 LOCK FEATURES (lógica invertida)
  // ==========================================================================
  // Nota: security_export_lock_enabled = TRUE significa BLOQUEADO
  // Starter: bloqueado | Premium/Enterprise: liberado
  { key: 'security_export_lock_enabled', name: 'Exportação de Dados', description: 'Exportar leads e relatórios', category: 'security', minPlan: 'premium' },
];

// ============================================================================
// CONTEXT
// ============================================================================

const FeaturesContext = createContext<FeaturesContextType | undefined>(undefined);

// ============================================================================
// API
// ============================================================================

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

async function fetchFeatures(): Promise<{ features: Features; plan: string; userRole: string }> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('vellarys_token') : null;

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

  /**
   * 🔴 NOVA ESTRUTURA DO BACKEND:
   * ========================================
   * - plan_features: Features do plano contratado
   * - overrides: SuperAdmin overrides (feature_overrides)
   * - team_features: O que o gestor liberou para a equipe
   * - final_features: Merge final (plan + overrides + team)
   * - user_role: Role do usuário (superadmin/admin/gestor/vendedor)
   *
   * 🔴 LÓGICA POR ROLE:
   * ========================================
   * SuperAdmin: Bypass completo (ALL_FEATURES_ENABLED)
   * Gestor/Admin: Usa final_features (plano + overrides + team)
   * Vendedor: Usa APENAS team_features (o que gestor liberou)
   */

  const userRole = data.user_role || 'vendedor';
  let effectiveFeatures: Features;

  if (userRole === 'superadmin') {
    // SuperAdmin tem acesso total (já tratado no Provider)
    effectiveFeatures = ALL_FEATURES_ENABLED;
  } else {
    // Para qualquer role não-superadmin, preferimos final_features quando disponível
    // (plan + overrides + team). Isso garante que overrides do Admin Master sejam respeitados.
    // Fallbacks:
    // - vendedor/seller: team_features
    // - demais: objeto inteiro (compatibilidade)
    if (data?.final_features) {
      effectiveFeatures = data.final_features;
      console.log('🟡 [FEATURES] Usando final_features:', effectiveFeatures);
    } else if (userRole === 'vendedor' || userRole === 'seller') {
      effectiveFeatures = data.team_features || DEFAULT_FEATURES;
      console.log('🟢 [VENDEDOR] Usando team_features:', effectiveFeatures);
    } else {
      effectiveFeatures = data || DEFAULT_FEATURES;
      console.log('🟡 [GESTOR] Fallback usando payload:', effectiveFeatures);
    }
  }

  return {
    features: effectiveFeatures,
    plan: data.plan_name || 'starter',
    userRole,
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
  // Verifica role do usuário
  const user = typeof window !== 'undefined' ? getUser() : null;
  const isSuperAdmin = user?.role === 'superadmin';

  const [state, setState] = useState<FeaturesState>({
    features: isSuperAdmin ? ALL_FEATURES_ENABLED : null,
    isLoading: !isSuperAdmin, // SuperAdmin não precisa carregar
    error: null,
    lastUpdated: isSuperAdmin ? new Date() : null,
    plan: isSuperAdmin ? 'superadmin' : null,
    userRole: user?.role || null,
    isSuperAdmin,
  });

  /**
   * Carrega features do backend
   * SuperAdmin NUNCA precisa carregar - tem acesso total
   */
  const refresh = useCallback(async () => {
    // SuperAdmin tem acesso total - não precisa carregar features
    if (isSuperAdmin) {
      setState(prev => ({
        ...prev,
        features: ALL_FEATURES_ENABLED,
        isLoading: false,
        error: null,
        lastUpdated: new Date(),
        plan: 'superadmin',
        userRole: 'superadmin',
        isSuperAdmin: true,
      }));
      return;
    }

    // Verifica se tem token antes de tentar
    const token = typeof window !== 'undefined' ? localStorage.getItem('vellarys_token') : null;
    if (!token) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        features: DEFAULT_FEATURES,
        error: null,
        userRole: null,
        isSuperAdmin: false,
      }));
      return;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const { features, plan, userRole } = await fetchFeatures();
      const currentUser = getUser();
      setState({
        features: { ...DEFAULT_FEATURES, ...features },
        isLoading: false,
        error: null,
        lastUpdated: new Date(),
        plan,
        userRole: userRole || currentUser?.role || null,
        isSuperAdmin: userRole === 'superadmin',
      });
      console.log('✅ Features carregadas:', { plan, userRole, features });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro desconhecido';
      console.error('❌ Erro ao carregar features:', err);
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
        // Manter features anteriores em caso de erro de rede
        features: prev.features || DEFAULT_FEATURES,
      }));
    }
  }, [isSuperAdmin]);

  /**
   * Invalida cache e força reload na próxima verificação
   */
  const invalidate = useCallback(() => {
    setState(prev => ({ ...prev, lastUpdated: null }));
  }, []);

  /**
   * Verifica se feature está habilitada
   * SuperAdmin SEMPRE tem acesso a tudo
   */
  const isEnabled = useCallback((feature: keyof Features): boolean => {
    // SuperAdmin bypass - acesso total
    if (state.isSuperAdmin) {
      // Para lock features, SuperAdmin NÃO é bloqueado
      if (feature === 'security_export_lock_enabled') {
        return false; // Lock desativado = export liberado
      }
      return true;
    }
    if (!state.features) return false;
    return state.features[feature] === true;
  }, [state.features, state.isSuperAdmin]);

  /**
   * Alias para isEnabled (para compatibilidade)
   */
  const canAccess = useCallback((feature: keyof Features): boolean => {
    return isEnabled(feature);
  }, [isEnabled]);

  /**
   * Verifica se tem QUALQUER uma das features
   * SuperAdmin sempre retorna true
   */
  const hasAnyFeature = useCallback((features: (keyof Features)[]): boolean => {
    if (state.isSuperAdmin) return true;
    return features.some(f => isEnabled(f));
  }, [isEnabled, state.isSuperAdmin]);

  /**
   * Verifica se tem TODAS as features
   * SuperAdmin sempre retorna true
   */
  const hasAllFeatures = useCallback((features: (keyof Features)[]): boolean => {
    if (state.isSuperAdmin) return true;
    return features.every(f => isEnabled(f));
  }, [isEnabled, state.isSuperAdmin]);

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
