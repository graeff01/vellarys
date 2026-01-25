/**
 * TypingIndicator - Indicador de Digitação
 * =========================================
 *
 * Mostra animação de "digitando..." quando o lead está digitando.
 * Acionado por evento SSE do backend.
 */

'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

interface TypingIndicatorProps {
  isTyping: boolean;
  userName?: string;
  className?: string;
}

export function TypingIndicator({ isTyping, userName = 'Cliente', className }: TypingIndicatorProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isTyping) {
      setVisible(true);
    } else {
      // Fade out suave
      const timer = setTimeout(() => setVisible(false), 300);
      return () => clearTimeout(timer);
    }
  }, [isTyping]);

  if (!visible) return null;

  return (
    <div
      className={cn(
        "flex items-center gap-2 text-sm text-muted-foreground",
        "transition-opacity duration-300",
        isTyping ? "opacity-100" : "opacity-0",
        className
      )}
    >
      <span className="font-medium">{userName}</span>
      <span>está digitando</span>

      {/* Animação de 3 pontos */}
      <div className="flex gap-1">
        <Dot delay="0ms" />
        <Dot delay="150ms" />
        <Dot delay="300ms" />
      </div>
    </div>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <div
      className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce"
      style={{
        animationDelay: delay,
        animationDuration: '1s'
      }}
    />
  );
}
