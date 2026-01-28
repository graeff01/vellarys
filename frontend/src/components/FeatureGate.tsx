'use client';

/**
 * FeatureGate - Componente de Controle de Acesso por Feature
 * ==========================================================
 *
 * Inspirado em:
 * - HubSpot: Feature gates com upgrade prompts
 * - Intercom: Graceful degradation
 * - Stripe: Entitlements-based access
 *
 * Uso:
 * ```tsx
 * <FeatureGate feature="calendar_enabled">
 *   <CalendarComponent />
 * </FeatureGate>
 *
 * // Com fallback customizado
 * <FeatureGate feature="metrics_enabled" fallback={<UpgradePrompt />}>
 *   <MetricsDashboard />
 * </FeatureGate>
 *
 * // Múltiplas features (AND)
 * <FeatureGate features={['calendar_enabled', 'templates_enabled']}>
 *   <AdvancedScheduler />
 * </FeatureGate>
 *
 * // Múltiplas features (OR)
 * <FeatureGate features={['calendar_enabled', 'templates_enabled']} requireAll={false}>
 *   <BasicScheduler />
 * </FeatureGate>
 * ```
 */

import React, { ReactNode } from 'react';
import { useFeatures, Features, FEATURES_METADATA } from '@/contexts/FeaturesContext';
import { Lock, Sparkles, ArrowUpRight, Crown } from 'lucide-react';
import Link from 'next/link';

// ============================================================================
// TIPOS
// ============================================================================

interface FeatureGateProps {
  /**
   * Feature única para verificar
   */
  feature?: keyof Features;

  /**
   * Múltiplas features para verificar
   */
  features?: (keyof Features)[];

  /**
   * Se true (default), requer TODAS as features.
   * Se false, requer QUALQUER uma das features.
   */
  requireAll?: boolean;

  /**
   * Conteúdo a exibir quando feature está habilitada
   */
  children: ReactNode;

  /**
   * Conteúdo a exibir quando feature está desabilitada
   * @default FeatureBlockedCard
   */
  fallback?: ReactNode;

  /**
   * Se true, não renderiza nada quando feature está desabilitada
   * @default false
   */
  hidden?: boolean;

  /**
   * Se true, mostra versão "blurred" do conteúdo ao invés do fallback
   * @default false
   */
  blur?: boolean;

  /**
   * Classe CSS adicional para o wrapper
   */
  className?: string;
}

// ============================================================================
// COMPONENTES AUXILIARES
// ============================================================================

/**
 * Card padrão exibido quando feature está bloqueada
 */
function FeatureBlockedCard({ feature, features }: { feature?: keyof Features; features?: (keyof Features)[] }) {
  const featureKey = feature || features?.[0];
  const metadata = featureKey ? FEATURES_METADATA.find(f => f.key === featureKey) : null;

  const planLabels = {
    starter: 'Starter',
    premium: 'Premium',
    enterprise: 'Enterprise',
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 text-center min-h-[200px]">
      <div className="w-16 h-16 bg-gradient-to-br from-violet-500 to-purple-600 rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-violet-500/25">
        <Lock className="w-8 h-8 text-white" />
      </div>

      <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
        {metadata?.name || 'Recurso'} não disponível
      </h3>

      <p className="text-sm text-slate-500 dark:text-slate-400 mb-4 max-w-md">
        {metadata?.description || 'Este recurso não está disponível no seu plano atual.'}
      </p>

      {metadata?.minPlan && metadata.minPlan !== 'starter' && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-violet-100 dark:bg-violet-900/30 rounded-full mb-4">
          <Crown className="w-4 h-4 text-violet-600 dark:text-violet-400" />
          <span className="text-xs font-semibold text-violet-600 dark:text-violet-400">
            Disponível no plano {planLabels[metadata.minPlan]}
          </span>
        </div>
      )}

      <Link
        href="/dashboard/settings?tab=subscription"
        className="inline-flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white text-sm font-semibold rounded-lg transition-colors"
      >
        <Sparkles className="w-4 h-4" />
        Fazer Upgrade
        <ArrowUpRight className="w-4 h-4" />
      </Link>
    </div>
  );
}

/**
 * Versão compacta do bloqueio (para usar em botões, links, etc)
 */
function FeatureBlockedInline({ feature }: { feature?: keyof Features }) {
  const metadata = feature ? FEATURES_METADATA.find(f => f.key === feature) : null;

  return (
    <div className="inline-flex items-center gap-1.5 px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-md text-xs text-slate-500 dark:text-slate-400">
      <Lock className="w-3 h-3" />
      <span>{metadata?.name || 'Recurso'} bloqueado</span>
    </div>
  );
}

/**
 * Badge de "Pro" ou "Enterprise" para mostrar em features bloqueadas
 */
export function FeatureBadge({ plan }: { plan: 'premium' | 'enterprise' }) {
  const colors = {
    premium: 'bg-gradient-to-r from-violet-500 to-purple-600',
    enterprise: 'bg-gradient-to-r from-amber-500 to-orange-600',
  };

  const labels = {
    premium: 'PRO',
    enterprise: 'ENTERPRISE',
  };

  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 ${colors[plan]} text-white text-[10px] font-bold rounded uppercase tracking-wider`}>
      <Crown className="w-2.5 h-2.5" />
      {labels[plan]}
    </span>
  );
}

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

export function FeatureGate({
  feature,
  features,
  requireAll = true,
  children,
  fallback,
  hidden = false,
  blur = false,
  className,
}: FeatureGateProps) {
  const { isEnabled, hasAnyFeature, hasAllFeatures, isLoading, isSuperAdmin } = useFeatures();

  // SuperAdmin SEMPRE tem acesso total - bypass completo
  if (isSuperAdmin) {
    return <>{children}</>;
  }

  // Determina quais features verificar
  const featuresToCheck = features || (feature ? [feature] : []);

  // Se não tem features para verificar, renderiza children
  if (featuresToCheck.length === 0) {
    return <>{children}</>;
  }

  // Verifica acesso
  const hasAccess = requireAll
    ? hasAllFeatures(featuresToCheck)
    : hasAnyFeature(featuresToCheck);

  // Loading state - mostra children com loading overlay
  if (isLoading) {
    return (
      <div className={`relative ${className || ''}`}>
        <div className="opacity-50 pointer-events-none">
          {children}
        </div>
        <div className="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm rounded-lg">
          <div className="w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  // Tem acesso - renderiza children
  if (hasAccess) {
    return <>{children}</>;
  }

  // Não tem acesso - hidden mode
  if (hidden) {
    return null;
  }

  // Não tem acesso - blur mode
  if (blur) {
    return (
      <div className={`relative ${className || ''}`}>
        <div className="blur-sm pointer-events-none select-none" aria-hidden="true">
          {children}
        </div>
        <div className="absolute inset-0 flex items-center justify-center">
          <FeatureBlockedInline feature={feature || features?.[0]} />
        </div>
      </div>
    );
  }

  // Não tem acesso - fallback ou card padrão
  if (fallback) {
    return <>{fallback}</>;
  }

  return <FeatureBlockedCard feature={feature} features={features} />;
}

// ============================================================================
// COMPONENTES UTILITÁRIOS
// ============================================================================

/**
 * HOC para proteger uma página inteira
 */
export function withFeatureGate<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  feature: keyof Features,
  options?: Omit<FeatureGateProps, 'feature' | 'children'>
) {
  return function FeatureGatedComponent(props: P) {
    return (
      <FeatureGate feature={feature} {...options}>
        <WrappedComponent {...props} />
      </FeatureGate>
    );
  };
}

/**
 * Wrapper para botões/links que devem ser desabilitados se feature bloqueada
 */
export function FeatureButton({
  feature,
  children,
  onClick,
  className = '',
  ...props
}: {
  feature: keyof Features;
  children: ReactNode;
  onClick?: () => void;
  className?: string;
  [key: string]: any;
}) {
  const { isEnabled } = useFeatures();
  const hasAccess = isEnabled(feature);
  const metadata = FEATURES_METADATA.find(f => f.key === feature);

  if (!hasAccess) {
    return (
      <button
        className={`relative cursor-not-allowed opacity-60 ${className}`}
        disabled
        title={`${metadata?.name || 'Recurso'} não disponível no seu plano`}
        {...props}
      >
        {children}
        <span className="absolute -top-1 -right-1">
          <Lock className="w-3 h-3 text-slate-400" />
        </span>
      </button>
    );
  }

  return (
    <button className={className} onClick={onClick} {...props}>
      {children}
    </button>
  );
}

/**
 * Link que só funciona se feature habilitada
 */
export function FeatureLink({
  feature,
  href,
  children,
  className = '',
  ...props
}: {
  feature: keyof Features;
  href: string;
  children: ReactNode;
  className?: string;
  [key: string]: any;
}) {
  const { isEnabled } = useFeatures();
  const hasAccess = isEnabled(feature);
  const metadata = FEATURES_METADATA.find(f => f.key === feature);

  if (!hasAccess) {
    return (
      <span
        className={`relative cursor-not-allowed opacity-60 ${className}`}
        title={`${metadata?.name || 'Recurso'} não disponível no seu plano`}
        {...props}
      >
        {children}
        <Lock className="inline-block w-3 h-3 ml-1 text-slate-400" />
      </span>
    );
  }

  return (
    <Link href={href} className={className} {...props}>
      {children}
    </Link>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export { FeatureBlockedCard, FeatureBlockedInline };
