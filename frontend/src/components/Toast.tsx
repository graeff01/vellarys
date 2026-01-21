/**
 * TOAST SYSTEM - Notificações bonitas
 * ====================================
 * 
 * Sistema de toast nativo (sem dependências externas).
 * Substitui alerts feios por notificações modernas.
 */

'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
    id: string;
    type: ToastType;
    message: string;
    icon?: string;
    duration?: number;
}

interface ToastContextType {
    toasts: Toast[];
    showToast: (message: string, type?: ToastType, icon?: string, duration?: number) => void;
    success: (message: string, icon?: string) => void;
    error: (message: string, icon?: string) => void;
    info: (message: string, icon?: string) => void;
    warning: (message: string, icon?: string) => void;
    removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, []);

    const showToast = useCallback((
        message: string,
        type: ToastType = 'info',
        icon?: string,
        duration: number = 3000
    ) => {
        const id = Math.random().toString(36).substr(2, 9);

        const defaultIcons = {
            success: '✅',
            error: '❌',
            info: 'ℹ️',
            warning: '⚠️',
        };

        const toast: Toast = {
            id,
            type,
            message,
            icon: icon || defaultIcons[type],
            duration,
        };

        setToasts((prev) => [...prev, toast]);

        if (duration > 0) {
            setTimeout(() => removeToast(id), duration);
        }
    }, [removeToast]);

    const success = useCallback((message: string, icon?: string) => {
        showToast(message, 'success', icon);
    }, [showToast]);

    const error = useCallback((message: string, icon?: string) => {
        showToast(message, 'error', icon);
    }, [showToast]);

    const info = useCallback((message: string, icon?: string) => {
        showToast(message, 'info', icon);
    }, [showToast]);

    const warning = useCallback((message: string, icon?: string) => {
        showToast(message, 'warning', icon);
    }, [showToast]);

    return (
        <ToastContext.Provider value={{ toasts, showToast, success, error, info, warning, removeToast }}>
            {children}
            <ToastContainer toasts={toasts} onRemove={removeToast} />
        </ToastContext.Provider>
    );
}

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within ToastProvider');
    }
    return context;
}

function ToastContainer({ toasts, onRemove }: { toasts: Toast[]; onRemove: (id: string) => void }) {
    return (
        <div className="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">
            {toasts.map((toast) => (
                <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
            ))}
        </div>
    );
}

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: (id: string) => void }) {
    const typeStyles = {
        success: 'bg-green-50 border-green-200 text-green-800',
        error: 'bg-red-50 border-red-200 text-red-800',
        info: 'bg-blue-50 border-blue-200 text-blue-800',
        warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    };

    return (
        <div
            className={`
        ${typeStyles[toast.type]}
        pointer-events-auto
        min-w-[300px] max-w-md
        px-4 py-3 rounded-lg border shadow-lg
        flex items-center gap-3
        animate-slide-in-right
        transition-all duration-300
      `}
        >
            {/* Icon */}
            {toast.icon && (
                <span className="text-2xl flex-shrink-0">
                    {toast.icon}
                </span>
            )}

            {/* Message */}
            <p className="flex-1 font-medium text-sm">
                {toast.message}
            </p>

            {/* Close button */}
            <button
                onClick={() => onRemove(toast.id)}
                className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>
    );
}

/**
 * HELPER GLOBAL - Para usar fora de componentes React
 */
let globalToast: ToastContextType | null = null;

export function setGlobalToast(toast: ToastContextType) {
    globalToast = toast;
}

export const toast = {
    success: (message: string, icon?: string) => globalToast?.success(message, icon),
    error: (message: string, icon?: string) => globalToast?.error(message, icon),
    info: (message: string, icon?: string) => globalToast?.info(message, icon),
    warning: (message: string, icon?: string) => globalToast?.warning(message, icon),
};
