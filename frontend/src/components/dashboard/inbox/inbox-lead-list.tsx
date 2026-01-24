/**
 * Lista de Leads no Inbox
 * Mostra todos os leads atribuídos ao corretor
 */

'use client';

import { InboxLead, getQualificationColor, getQualificationEmoji, formatRelativeTime } from '@/lib/inbox';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { MessageCircle, User, Phone, MapPin } from 'lucide-react';

interface InboxLeadListProps {
  leads: InboxLead[];
  selectedLeadId: number | null;
  onSelectLead: (lead: InboxLead) => void;
  loading?: boolean;
}

export function InboxLeadList({
  leads,
  selectedLeadId,
  onSelectLead,
  loading = false,
}: InboxLeadListProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-2">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
          <p className="text-sm text-gray-500">Carregando leads...</p>
        </div>
      </div>
    );
  }

  if (leads.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-6">
        <div className="text-center space-y-3">
          <MessageCircle className="h-12 w-12 text-gray-400 mx-auto" />
          <p className="text-sm text-gray-500">Nenhum lead atribuído ainda</p>
          <p className="text-xs text-gray-400">
            Os leads qualificados aparecerão aqui automaticamente
          </p>
        </div>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="divide-y">
        {leads.map((lead) => (
          <button
            key={lead.id}
            onClick={() => onSelectLead(lead)}
            className={cn(
              'w-full p-4 hover:bg-gray-50 transition-colors text-left relative',
              selectedLeadId === lead.id && 'bg-blue-50 hover:bg-blue-50 border-l-4 border-blue-600'
            )}
          >
            {/* Badge de mensagens não lidas */}
            {lead.unread_messages > 0 && (
              <div className="absolute top-4 right-4">
                <Badge className="bg-blue-600 text-white rounded-full h-5 w-5 p-0 flex items-center justify-center text-xs">
                  {lead.unread_messages}
                </Badge>
              </div>
            )}

            {/* Nome e qualificação */}
            <div className="flex items-center gap-2 mb-2">
              <div className="flex-shrink-0">
                <div className="h-10 w-10 rounded-full bg-gray-100 flex items-center justify-center">
                  <User className="h-5 w-5 text-gray-600" />
                </div>
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-900 truncate">
                    {lead.name || 'Lead sem nome'}
                  </p>
                  {lead.qualification && (
                    <span className="text-sm">
                      {getQualificationEmoji(lead.qualification)}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1 text-xs text-gray-500">
                  <Phone className="h-3 w-3" />
                  <span>{lead.phone}</span>
                </div>
              </div>
            </div>

            {/* Preview da última mensagem */}
            {lead.last_message_preview && (
              <p className="text-sm text-gray-600 truncate mb-2">
                {lead.last_message_preview}
              </p>
            )}

            {/* Informações adicionais */}
            <div className="flex items-center justify-between text-xs text-gray-500">
              <div className="flex items-center gap-3">
                {lead.city && (
                  <div className="flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    <span>{lead.city}</span>
                  </div>
                )}
                {lead.qualification && (
                  <Badge
                    variant="outline"
                    className={cn(
                      'text-xs py-0 px-2',
                      getQualificationColor(lead.qualification)
                    )}
                  >
                    {lead.qualification}
                  </Badge>
                )}
              </div>

              <span className="text-gray-400">
                {formatRelativeTime(lead.last_message_at)}
              </span>
            </div>

            {/* Indicador de quem está atendendo */}
            <div className="mt-2 flex items-center gap-2">
              {lead.is_taken_over ? (
                <Badge className="bg-green-100 text-green-800 text-xs">
                  Você está atendendo
                </Badge>
              ) : (
                <Badge variant="outline" className="text-xs">
                  IA atendendo
                </Badge>
              )}
            </div>
          </button>
        ))}
      </div>
    </ScrollArea>
  );
}
