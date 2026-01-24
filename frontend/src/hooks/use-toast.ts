import { useState, useCallback } from 'react';

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: 'default' | 'destructive';
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback(({ title, description, variant = 'default' }: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substring(7);
    const newToast = { id, title, description, variant };

    setToasts((prev) => [...prev, newToast]);

    // Auto-remove após 5 segundos
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);

    // Mostra alerta nativo por enquanto (pode melhorar depois)
    if (variant === 'destructive') {
      alert(`❌ ${title}\n${description || ''}`);
    } else {
      console.log(`✅ ${title}`, description);
    }
  }, []);

  return { toast, toasts };
}
