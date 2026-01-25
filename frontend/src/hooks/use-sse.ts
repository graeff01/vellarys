/**
 * useSSE - Hook para Server-Sent Events
 * =====================================
 *
 * Conecta ao endpoint SSE do backend para receber atualizações em tempo real.
 *
 * Eventos:
 * - new_message: Nova mensagem recebida/enviada
 * - message_status: Status de entrega atualizado (✓✓)
 * - typing: Indicador de digitação
 * - lead_updated: Dados do lead alterados
 * - handoff: Transferência de atendimento
 */

import { useEffect, useRef, useState } from 'react';

export interface SSEEvent {
  type: string;
  timestamp: string;
  data: any;
}

interface UseSSEOptions {
  onMessage?: (event: SSEEvent) => void;
  onError?: (error: Event) => void;
  enabled?: boolean;
}

export function useSSE(leadId: number | null, options: UseSSEOptions = {}) {
  const { onMessage, onError, enabled = true } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Não conecta se desabilitado ou sem leadId
    if (!enabled || !leadId) {
      return;
    }

    const connect = () => {
      try {
        // Obtém token do localStorage
        const token = localStorage.getItem('token');
        if (!token) {
          console.error('[SSE] Token não encontrado');
          return;
        }

        // URL do SSE (não podemos passar headers em EventSource, então token vai na URL)
        const url = `${process.env.NEXT_PUBLIC_API_URL}/seller/inbox/leads/${leadId}/stream?token=${token}`;

        // Cria conexão SSE
        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;

        // Evento: aberto
        eventSource.onopen = () => {
          console.log(`[SSE] Conectado ao lead ${leadId}`);
          setIsConnected(true);

          // Limpa timeout de reconexão
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
          }
        };

        // Evento: mensagem
        eventSource.onmessage = (event) => {
          try {
            // Ignora heartbeat
            if (!event.data || event.data.trim() === '') {
              return;
            }

            const parsed: SSEEvent = JSON.parse(event.data);

            // Ignora evento de conexão
            if (parsed.type === 'connected') {
              return;
            }

            console.log('[SSE] Evento recebido:', parsed.type, parsed.data);

            setLastEvent(parsed);

            if (onMessage) {
              onMessage(parsed);
            }
          } catch (error) {
            console.error('[SSE] Erro ao parsear evento:', error);
          }
        };

        // Evento: erro
        eventSource.onerror = (error) => {
          console.error('[SSE] Erro na conexão:', error);
          setIsConnected(false);

          if (onError) {
            onError(error);
          }

          // Fecha conexão atual
          eventSource.close();

          // Tenta reconectar após 5s
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('[SSE] Tentando reconectar...');
            connect();
          }, 5000);
        };

      } catch (error) {
        console.error('[SSE] Erro ao criar EventSource:', error);
      }
    };

    // Conecta
    connect();

    // Cleanup
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      setIsConnected(false);
    };
  }, [leadId, enabled, onMessage, onError]);

  return {
    isConnected,
    lastEvent
  };
}
