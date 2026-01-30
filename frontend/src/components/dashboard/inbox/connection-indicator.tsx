/**
 * ConnectionIndicator - Indicador de Conexão SSE
 * ===============================================
 *
 * Indicador visual do status da conexão em tempo real (SSE).
 */

'use client';

import { Wifi, WifiOff, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

type ConnectionStatus = 'connected' | 'connecting' | 'disconnected';

interface ConnectionIndicatorProps {
  status: ConnectionStatus;
  className?: string;
}

export function ConnectionIndicator({ status, className }: ConnectionIndicatorProps) {
  const icons = {
    connected: Wifi,
    connecting: Loader2,
    disconnected: WifiOff,
  };

  const colors = {
    connected: 'text-green-500',
    connecting: 'text-yellow-500',
    disconnected: 'text-red-500',
  };

  const labels = {
    connected: 'Conectado em tempo real',
    connecting: 'Conectando...',
    disconnected: 'Desconectado',
  };

  const Icon = icons[status];

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={cn('flex items-center gap-1.5', className)}>
            <Icon
              className={cn(
                'h-4 w-4',
                colors[status],
                status === 'connecting' && 'animate-spin'
              )}
            />
            <span className="text-xs font-medium text-muted-foreground hidden sm:inline">
              {labels[status]}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p className="text-xs">
            {status === 'connected' && 'Mensagens atualizadas em tempo real via SSE'}
            {status === 'connecting' && 'Estabelecendo conexão...'}
            {status === 'disconnected' && 'Sem conexão em tempo real. Recarregue a página.'}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
