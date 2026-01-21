/**
 * EMPTY STATE - Estados vazios bonitos
 * =====================================
 * 
 * Componente para quando não há dados.
 * Muito melhor que "Nenhum item encontrado"
 */

import { ReactNode } from 'react';

interface EmptyStateProps {
    icon?: ReactNode | string;
    title: string;
    description?: string;
    action?: {
        label: string;
        onClick: () => void;
    };
    className?: string;
}

export function EmptyState({
    icon = '📭',
    title,
    description,
    action,
    className = '',
}: EmptyStateProps) {
    return (
        <div className={`text-center py-12 px-4 ${className}`}>
            {/* Icon */}
            <div className="mb-4">
                {typeof icon === 'string' ? (
                    <div className="text-6xl">{icon}</div>
                ) : (
                    <div className="flex justify-center">{icon}</div>
                )}
            </div>

            {/* Title */}
            <h3 className="text-xl font-bold text-gray-900 mb-2">
                {title}
            </h3>

            {/* Description */}
            {description && (
                <p className="text-gray-600 mb-6 max-w-md mx-auto">
                    {description}
                </p>
            )}

            {/* Action */}
            {action && (
                <button
                    onClick={action.onClick}
                    className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-all hover:scale-105 hover:shadow-lg"
                >
                    {action.label}
                </button>
            )}
        </div>
    );
}

/**
 * EMPTY STATE PRESETS - Casos comuns
 */

export function EmptyLeads({ onCreateLead }: { onCreateLead?: () => void }) {
    return (
        <EmptyState
            icon="🎯"
            title="Nenhum lead ainda"
            description="Seus leads aparecerão aqui quando começarem a chegar pelo WhatsApp. Que tal testar com o simulador?"
            action={onCreateLead ? {
                label: '🧪 Testar com Simulador',
                onClick: onCreateLead,
            } : undefined}
        />
    );
}

export function EmptySellers({ onCreateSeller }: { onCreateSeller?: () => void }) {
    return (
        <EmptyState
            icon="👥"
            title="Nenhum vendedor cadastrado"
            description="Adicione vendedores para distribuir leads automaticamente e aumentar suas conversões."
            action={onCreateSeller ? {
                label: '+ Adicionar Vendedor',
                onClick: onCreateSeller,
            } : undefined}
        />
    );
}

export function EmptyMessages() {
    return (
        <EmptyState
            icon="💬"
            title="Nenhuma mensagem ainda"
            description="As conversas com este lead aparecerão aqui."
        />
    );
}

export function EmptySearch({ query }: { query: string }) {
    return (
        <EmptyState
            icon="🔍"
            title="Nenhum resultado encontrado"
            description={`Não encontramos nada para "${query}". Tente buscar com outros termos.`}
        />
    );
}

export function EmptyNotifications() {
    return (
        <EmptyState
            icon="🔔"
            title="Você está em dia!"
            description="Nenhuma notificação pendente no momento."
        />
    );
}

export function ErrorState({
    onRetry
}: {
    onRetry?: () => void
}) {
    return (
        <EmptyState
            icon="⚠️"
            title="Ops! Algo deu errado"
            description="Não conseguimos carregar os dados. Tente novamente."
            action={onRetry ? {
                label: '🔄 Tentar Novamente',
                onClick: onRetry,
            } : undefined}
        />
    );
}
