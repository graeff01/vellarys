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
    connected: 'text-green-700',
    connecting: 'text-amber-700',
    disconnected: 'text-red-700',
  };

  const bgColors = {
    connected: 'bg-green-50 border-green-200',
    connecting: 'bg-amber-50 border-amber-200',
    disconnected: 'bg-red-50 border-red-200',
  };

  const labels = {
    connected: 'Online',
    connecting: 'Conectando',
    disconnected: 'Offline',
  };

  const Icon = icons[status];

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={cn(
            'inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] font-medium',
            bgColors[status],
            colors[status],
            className
          )}>
            <Icon
              className={cn(
                'h-2.5 w-2.5',
                status === 'connecting' && 'animate-spin'
              )}
            />
            <span>
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
