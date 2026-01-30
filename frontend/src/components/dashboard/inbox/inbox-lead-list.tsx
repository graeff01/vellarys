/**
 * Lista de Leads no Inbox - WhatsApp Web Style
 * Interface inspirada no WhatsApp Web para melhor familiaridade dos corretores
 */

'use client';

import { InboxLead, formatRelativeTime } from '@/lib/inbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import { MessageCircle, CheckCheck } from 'lucide-react';

interface InboxLeadListProps {
  leads: InboxLead[];
  selectedLeadId: number | null;
  onSelectLead: (lead: InboxLead) => void;
  loading?: boolean;
  bulkMode?: boolean;
  selectedLeadIds?: number[];
}

export function InboxLeadList({
  leads,
  selectedLeadId,
  onSelectLead,
  loading = false,
  bulkMode = false,
  selectedLeadIds = [],
}: InboxLeadListProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-white">
        <div className="text-center space-y-2">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#075e54] mx-auto"></div>
          <p className="text-sm text-gray-500" style={{ fontFamily: 'Segoe UI, Helvetica Neue, Arial, sans-serif' }}>
            Carregando conversas...
          </p>
        </div>
      </div>
    );
  }

  if (leads.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-6 bg-white">
        <div className="text-center space-y-3">
          <div className="w-32 h-32 mx-auto rounded-full bg-[#f0f2f5] flex items-center justify-center">
            <MessageCircle className="h-16 w-16 text-gray-400" />
          </div>
          <div style={{ fontFamily: 'Segoe UI, Helvetica Neue, Arial, sans-serif' }}>
            <p className="text-base text-gray-700 font-medium">Nenhuma conversa ainda</p>
            <p className="text-sm text-gray-500 mt-1">
              Os leads qualificados aparecerão aqui
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full bg-white">
      <div style={{ fontFamily: 'Segoe UI, Helvetica Neue, Arial, sans-serif' }}>
        {leads.map((lead) => {
          const isSelected = selectedLeadId === lead.id;
          const hasUnread = lead.unread_messages > 0;
          const isBulkSelected = selectedLeadIds.includes(lead.id);

          return (
            <button
              key={lead.id}
              onClick={() => onSelectLead(lead)}
              className={cn(
                'w-full px-4 py-3 transition-colors text-left relative border-b border-gray-100',
                'hover:bg-[#f5f6f6]',
                isSelected && !bulkMode && 'bg-[#f0f2f5]',
                isBulkSelected && bulkMode && 'bg-blue-50 border-blue-200'
              )}
            >
              <div className="flex items-start gap-3">
                {/* Checkbox para bulk mode */}
                {bulkMode && (
                  <div className="flex-shrink-0 pt-3" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={isBulkSelected}
                      onCheckedChange={() => onSelectLead(lead)}
                      className="h-5 w-5"
                    />
                  </div>
                )}

                {/* Avatar */}
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-[#dfe5e7] flex items-center justify-center overflow-hidden">
                  {lead.profile_picture_url ? (
                    <img
                      src={lead.profile_picture_url}
                      alt={lead.name || 'Lead'}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        // Fallback para inicial se imagem falhar
                        e.currentTarget.style.display = 'none';
                        const parent = e.currentTarget.parentElement;
                        if (parent) {
                          const span = document.createElement('span');
                          span.className = "text-xl font-medium text-gray-700";
                          span.textContent = lead.name ? lead.name.charAt(0).toUpperCase() : '?';
                          parent.appendChild(span);
                        }
                      }}
                    />
                  ) : (
                    <span className="text-xl font-medium text-gray-700">
                      {lead.name ? lead.name.charAt(0).toUpperCase() : '?'}
                    </span>
                  )}
                </div>

                {/* Conteúdo */}
                <div className="flex-1 min-w-0">
                  {/* Linha superior: Nome e Timestamp */}
                  <div className="flex items-baseline justify-between mb-1 gap-2">
                    <h4 className={cn(
                      "text-base truncate",
                      hasUnread ? "font-semibold text-gray-900" : "font-normal text-gray-900"
                    )}>
                      {lead.name || 'Lead sem nome'}
                    </h4>
                    <span className={cn(
                      "text-xs flex-shrink-0",
                      hasUnread ? "text-[#00a884] font-medium" : "text-gray-500"
                    )}>
                      {formatRelativeTime(lead.last_message_at)}
                    </span>
                  </div>

                  {/* Linha inferior: Preview e Badge */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1 min-w-0 flex-1">
                      {/* Indicador de quem enviou a última mensagem */}
                      {lead.is_taken_over && (
                        <CheckCheck className={cn(
                          "h-4 w-4 flex-shrink-0",
                          hasUnread ? "text-gray-500" : "text-blue-600"
                        )} />
                      )}

                      {/* Preview da última mensagem */}
                      <p className={cn(
                        "text-sm truncate",
                        hasUnread ? "font-medium text-gray-900" : "text-gray-600"
                      )}>
                        {lead.last_message_preview || 'Sem mensagens'}
                      </p>
                    </div>

                    {/* Badge de não lidas */}
                    {hasUnread && (
                      <div className="flex-shrink-0 bg-[#25d366] text-white rounded-full min-w-[20px] h-5 px-1.5 flex items-center justify-center">
                        <span className="text-xs font-medium">
                          {lead.unread_messages > 99 ? '99+' : lead.unread_messages}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Linha de informações extras - mais sutil */}
                  <div className="flex items-center gap-2 mt-1">
                    {/* Indicadores sutis */}
                    {lead.qualification && (
                      <span className="text-xs text-gray-500">
                        {lead.qualification === 'quente' || lead.qualification === 'Quente' ? '🔥' :
                          lead.qualification === 'morno' || lead.qualification === 'Morno' ? '☀️' :
                            lead.qualification === 'frio' || lead.qualification === 'Frio' ? '❄️' : '📋'}
                      </span>
                    )}

                    {lead.city && (
                      <span className="text-xs text-gray-500 truncate">
                        {lead.city}
                      </span>
                    )}

                    {lead.is_taken_over && (
                      <span className="text-xs text-green-600 font-medium ml-auto flex-shrink-0">
                        Você
                      </span>
                    )}
                    {!lead.is_taken_over && (
                      <span className="text-xs text-blue-600 font-medium ml-auto flex-shrink-0">
                        IA
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </ScrollArea>
  );
}
