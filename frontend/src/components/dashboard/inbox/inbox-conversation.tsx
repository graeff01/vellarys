/**
 * Conversa do Inbox - WhatsApp Web Style
 * Interface inspirada no WhatsApp Web para melhor familiaridade dos corretores
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { InboxLead, InboxMessage, getLeadMessages, sendMessage, takeOverLead, returnToAI } from '@/lib/inbox';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { useSSE } from '@/hooks/use-sse';
import { cn } from '@/lib/utils';
import {
  Send,
  ArrowLeft,
  MoreVertical,
  Search,
  MessageSquare,
  Paperclip,
  Check,
  CheckCheck,
  StickyNote,
  Archive,
} from 'lucide-react';
import { TemplatesPopover } from './templates-popover';
import { LeadNotesPanel } from './lead-notes-panel';
import { AttachmentUpload } from './attachment-upload';
import { TypingIndicator } from './typing-indicator';

interface InboxConversationProps {
  lead: InboxLead | null;
  onBack?: () => void;
  onLeadUpdated?: () => void;
}

export function InboxConversation({ lead, onBack, onLeadUpdated }: InboxConversationProps) {
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [takingOver, setTakingOver] = useState(false);
  const [message, setMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showAttachmentUpload, setShowAttachmentUpload] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { toast } = useToast();

  // SSE para atualizações em tempo real
  useSSE(lead?.id || null, {
    enabled: !!lead,
    onMessage: (event) => {
      switch (event.type) {
        case 'new_message':
          // Adiciona nova mensagem à lista
          loadMessages();
          break;

        case 'message_status':
          // Atualiza status de mensagem (✓✓)
          setMessages(prev =>
            prev.map(msg =>
              msg.id === event.data.message_id
                ? { ...msg, status: event.data.status }
                : msg
            )
          );
          break;

        case 'typing':
          // Mostra indicador de digitação
          setIsTyping(event.data.is_typing);
          break;

        case 'lead_updated':
          // Recarrega dados do lead
          onLeadUpdated?.();
          break;

        case 'handoff':
          // Transferência de atendimento
          toast({
            title: 'Lead transferido',
            description: event.data.to_user_name
              ? `Lead transferido para ${event.data.to_user_name}`
              : 'Lead transferido'
          });
          onLeadUpdated?.();
          break;
      }
    }
  });

  // Carrega mensagens quando lead muda
  useEffect(() => {
    if (lead) {
      loadMessages();
    } else {
      setMessages([]);
    }
  }, [lead?.id]);

  // Auto-scroll para última mensagem
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadMessages = async () => {
    if (!lead) return;

    setLoading(true);
    try {
      const data = await getLeadMessages(lead.id);
      setMessages(data);
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Erro ao carregar mensagens',
        description: error.response?.data?.detail || 'Tente novamente',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTakeOver = async () => {
    if (!lead) return;

    setTakingOver(true);
    try {
      await takeOverLead(lead.id);
      toast({
        title: 'Conversa assumida!',
        description: 'Agora você pode responder o lead diretamente. A IA não responderá mais.',
      });
      onLeadUpdated?.();
      loadMessages();
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Erro ao assumir conversa',
        description: error.response?.data?.detail || 'Tente novamente',
      });
    } finally {
      setTakingOver(false);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!lead || !message.trim()) return;

    // Verifica se já assumiu a conversa
    if (!lead.is_taken_over) {
      toast({
        variant: 'destructive',
        title: 'Você precisa assumir a conversa primeiro',
        description: 'Clique em "Assumir Conversa" para poder enviar mensagens.',
      });
      return;
    }

    setSending(true);
    try {
      await sendMessage(lead.id, message);

      // Adiciona mensagem otimisticamente
      const newMessage: InboxMessage = {
        id: Date.now(),
        role: 'assistant',
        content: message,
        created_at: new Date().toISOString(),
        sender_type: 'seller',
        sender_user_id: null,
        sender_name: 'Você',
      };
      setMessages((prev) => [...prev, newMessage]);
      setMessage('');

      toast({
        title: 'Mensagem enviada!',
        description: 'O lead receberá sua mensagem via WhatsApp.',
      });

      // Recarrega mensagens após 1s para pegar a versão real
      setTimeout(loadMessages, 1000);
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Erro ao enviar mensagem',
        description: error.response?.data?.detail || 'Tente novamente',
      });
    } finally {
      setSending(false);
    }
  };

  const handleReturnToAI = async () => {
    if (!lead) return;

    try {
      await returnToAI(lead.id);
      toast({
        title: 'Lead devolvido para a IA',
        description: 'A IA voltará a atender automaticamente.',
      });
      onLeadUpdated?.();
      loadMessages();
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Erro ao devolver lead',
        description: error.response?.data?.detail || 'Tente novamente',
      });
    }
  };

  if (!lead) {
    return (
      <div className="flex items-center justify-center h-full bg-[#f0f2f5]">
        <div className="text-center space-y-4">
          <div className="w-64 h-64 mx-auto opacity-20">
            <svg viewBox="0 0 303 172" fill="none">
              <circle cx="151.5" cy="86" r="86" fill="#e5e7eb" />
            </svg>
          </div>
          <div className="space-y-2">
            <h3 className="text-2xl font-light text-gray-700" style={{ fontFamily: 'Segoe UI, Helvetica Neue, Arial, sans-serif' }}>
              CRM Inbox Vellarys
            </h3>
            <p className="text-sm text-gray-500">
              Selecione uma conversa para começar a atender
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full" style={{ fontFamily: 'Segoe UI, Helvetica Neue, Arial, sans-serif' }}>
      {/* Header estilo WhatsApp */}
      <div className="bg-[#075e54] text-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {onBack && (
            <button
              onClick={onBack}
              className="lg:hidden p-2 hover:bg-white/10 rounded-full transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
          )}

          {/* Avatar */}
          <div className="w-10 h-10 rounded-full bg-[#dfe5e7] flex items-center justify-center flex-shrink-0 overflow-hidden">
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
                    span.className = "text-lg font-medium text-gray-700";
                    span.textContent = lead.name ? lead.name.charAt(0).toUpperCase() : '?';
                    parent.appendChild(span);
                  }
                }}
              />
            ) : (
              <span className="text-lg font-medium text-gray-700">
                {lead.name ? lead.name.charAt(0).toUpperCase() : '?'}
              </span>
            )}
          </div>

          {/* Nome e info */}
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-base truncate">
              {lead.name || 'Lead sem nome'}
            </h3>
            <div className="flex items-center gap-2 text-xs">
              <span className="truncate">{lead.phone}</span>
              {lead.city && (
                <>
                  <span>•</span>
                  <span className="truncate">{lead.city}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Ações do header */}
        <div className="flex items-center gap-2">
          {/* Anotações */}
          <LeadNotesPanel leadId={lead.id}>
            <button className="p-2 hover:bg-white/10 rounded-full transition-colors">
              <StickyNote className="h-5 w-5" />
            </button>
          </LeadNotesPanel>

          <button className="p-2 hover:bg-white/10 rounded-full transition-colors">
            <Search className="h-5 w-5" />
          </button>
          <button className="p-2 hover:bg-white/10 rounded-full transition-colors">
            <MoreVertical className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Sub-header com status e ações */}
      {(!lead.is_taken_over || (lead.interest || lead.budget)) && (
        <div className="bg-[#f0f2f5] border-b border-gray-300 px-4 py-2">
          <div className="flex items-center justify-between gap-3">
            {/* Informações do lead */}
            <div className="flex items-center gap-3 text-xs text-gray-600 flex-1">
              {lead.interest && (
                <span className="bg-white px-2 py-1 rounded">
                  🏠 {lead.interest}
                </span>
              )}
              {lead.budget && (
                <span className="bg-white px-2 py-1 rounded">
                  💰 {lead.budget}
                </span>
              )}
              {lead.qualification && (
                <span className={cn(
                  "px-2 py-1 rounded font-medium",
                  lead.qualification.toLowerCase() === 'quente' && "bg-red-100 text-red-700",
                  lead.qualification.toLowerCase() === 'morno' && "bg-orange-100 text-orange-700",
                  lead.qualification.toLowerCase() === 'frio' && "bg-blue-100 text-blue-700"
                )}>
                  {lead.qualification}
                </span>
              )}
            </div>

            {/* Botões de ação */}
            <div className="flex items-center gap-2">
              {lead.is_taken_over ? (
                <>
                  <Badge className="bg-green-600 text-white text-xs">
                    ✓ Você está atendendo
                  </Badge>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleReturnToAI}
                    className="text-xs h-7"
                  >
                    Devolver para IA
                  </Button>
                </>
              ) : (
                <Button
                  onClick={handleTakeOver}
                  disabled={takingOver}
                  size="sm"
                  className="bg-[#075e54] hover:bg-[#064e46] text-white text-xs h-7"
                >
                  {takingOver ? 'Assumindo...' : 'Assumir Conversa'}
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Área de mensagens com fundo WhatsApp */}
      <div className="flex-1 overflow-hidden bg-[#e5ddd5] relative">
        {/* Padrão de fundo sutil do WhatsApp */}
        <div
          className="absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />

        <ScrollArea className="h-full">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#075e54]"></div>
            </div>
          ) : (
            <div className="px-[9%] py-3 space-y-2 relative">
              {messages.map((msg, index) => {
                const isUser = msg.role === 'user';
                const isAI = msg.sender_type === 'ai' || (msg.role === 'assistant' && !msg.sender_type);
                const isSeller = msg.sender_type === 'seller';
                const isSystem = msg.sender_type === 'system' || msg.role === 'system';

                // Formatação do horário
                const messageTime = new Date(msg.created_at).toLocaleTimeString('pt-BR', {
                  hour: '2-digit',
                  minute: '2-digit',
                });

                if (isSystem) {
                  return (
                    <div key={msg.id} className="flex justify-center my-3">
                      <div className="bg-[#ffffffcc] backdrop-blur-sm px-3 py-1.5 rounded-lg shadow-sm">
                        <p className="text-xs text-gray-700">{msg.content}</p>
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={msg.id}
                    className={cn(
                      'flex',
                      (isSeller || isAI) ? 'justify-end' : 'justify-start'
                    )}
                  >
                    <div
                      className={cn(
                        'relative max-w-[65%] rounded-lg shadow-sm px-3 py-2',
                        (isSeller || isAI)
                          ? 'bg-[#d9fdd3] rounded-tr-none'
                          : 'bg-white rounded-tl-none'
                      )}
                      style={{
                        wordWrap: 'break-word',
                      }}
                    >
                      {/* Nome do remetente (se não for o lead) */}
                      {!isUser && msg.sender_name && (
                        <p className={cn(
                          "text-xs font-medium mb-1",
                          isAI ? "text-blue-700" : "text-green-700"
                        )}>
                          {msg.sender_name}
                        </p>
                      )}

                      {/* Conteúdo da mensagem */}
                      <p className="text-sm text-gray-900 whitespace-pre-wrap break-words">
                        {msg.content}
                      </p>

                      {/* Timestamp e status */}
                      <div className="flex items-center justify-end gap-1 mt-1">
                        <span className="text-[11px] text-gray-500">
                          {messageTime}
                        </span>
                        {(isSeller || isAI) && (
                          <span className={cn(
                            "transition-colors",
                            (msg as any).status === 'read' ? "text-blue-500" : "text-gray-500"
                          )}>
                            {(msg as any).status === 'sent' ? (
                              <Check className="h-3.5 w-3.5" />
                            ) : (
                              <CheckCheck className="h-3.5 w-3.5" />
                            )}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Indicador de digitação */}
              {isTyping && (
                <div className="flex justify-start">
                  <div className="bg-white rounded-lg rounded-tl-none shadow-sm px-3 py-2">
                    <TypingIndicator isTyping={isTyping} userName={lead.name || 'Cliente'} />
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Aviso se não assumiu ainda */}
      {!lead.is_taken_over && (
        <div className="bg-[#fff4cc] border-t border-[#ffe066] px-4 py-2 flex items-center gap-2 text-sm">
          <span className="text-[#6c5c00]">⚠️</span>
          <p className="text-[#6c5c00] flex-1">
            <strong>IA atendendo.</strong> Clique em "Assumir Conversa" para poder enviar mensagens.
          </p>
        </div>
      )}

      {/* Input de mensagem - estilo WhatsApp */}
      <div className="bg-[#f0f2f5] px-4 py-2 border-t border-gray-300 space-y-2">
        {/* Upload de anexo */}
        {showAttachmentUpload && lead.is_taken_over && (
          <AttachmentUpload
            leadId={lead.id}
            onUploadComplete={(attachment) => {
              toast({
                title: 'Anexo enviado!',
                description: `${attachment.filename} foi enviado com sucesso.`
              });
              setShowAttachmentUpload(false);
              loadMessages();
            }}
            onUploadError={(error) => {
              toast({
                variant: 'destructive',
                title: 'Erro no upload',
                description: error
              });
            }}
          />
        )}

        <form onSubmit={handleSendMessage} className="flex items-end gap-2">
          {/* Botão Template */}
          <TemplatesPopover
            leadId={lead.id}
            onSelectTemplate={(content) => {
              setMessage(content);
              textareaRef.current?.focus();
            }}
          >
            <button
              type="button"
              disabled={!lead.is_taken_over}
              className={cn(
                "p-2 rounded-full transition-colors flex-shrink-0",
                lead.is_taken_over
                  ? "text-gray-600 hover:bg-gray-300/50"
                  : "text-gray-400 cursor-not-allowed"
              )}
              title="Templates de Respostas"
            >
              <MessageSquare className="h-6 w-6" />
            </button>
          </TemplatesPopover>

          {/* Botão Anexo */}
          <button
            type="button"
            disabled={!lead.is_taken_over}
            onClick={() => setShowAttachmentUpload(!showAttachmentUpload)}
            className={cn(
              "p-2 rounded-full transition-colors flex-shrink-0",
              lead.is_taken_over
                ? "text-gray-600 hover:bg-gray-300/50"
                : "text-gray-400 cursor-not-allowed"
            )}
          >
            <Paperclip className="h-6 w-6" />
          </button>

          {/* Input */}
          <div className="flex-1 bg-white rounded-lg shadow-sm">
            <Textarea
              ref={textareaRef}
              placeholder={
                lead.is_taken_over
                  ? 'Digite uma mensagem'
                  : 'Assuma a conversa para enviar mensagens'
              }
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              disabled={!lead.is_taken_over || sending}
              className="border-0 focus-visible:ring-0 focus-visible:ring-offset-0 min-h-[42px] max-h-[120px] resize-none py-2.5 px-3 text-sm"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              rows={1}
            />
          </div>

          {/* Botão Enviar */}
          <button
            type="submit"
            disabled={!lead.is_taken_over || !message.trim() || sending}
            className={cn(
              "p-3 rounded-full transition-colors flex-shrink-0",
              (!lead.is_taken_over || !message.trim() || sending)
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-[#075e54] hover:bg-[#064e46] text-white"
            )}
          >
            {sending ? (
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
