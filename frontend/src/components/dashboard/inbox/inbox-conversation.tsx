/**
 * Conversa do Inbox
 * Mostra histórico de mensagens e permite ao corretor responder
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { InboxLead, InboxMessage, getLeadMessages, sendMessage, takeOverLead, returnToAI } from '@/lib/inbox';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import {
  Send,
  Bot,
  User,
  CheckCircle,
  AlertCircle,
  Phone,
  MapPin,
  DollarSign,
  Home,
  ArrowLeft,
} from 'lucide-react';

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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

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

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
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
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-3">
          <User className="h-16 w-16 text-gray-400 mx-auto" />
          <p className="text-gray-500">Selecione um lead para ver a conversa</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header do Lead */}
      <div className="border-b p-4 bg-white">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            {onBack && (
              <Button variant="ghost" size="sm" onClick={onBack} className="lg:hidden">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            )}
            <div>
              <h3 className="font-semibold text-lg">{lead.name || 'Lead sem nome'}</h3>
              <div className="flex items-center gap-3 text-sm text-gray-600">
                <div className="flex items-center gap-1">
                  <Phone className="h-3 w-3" />
                  <span>{lead.phone}</span>
                </div>
                {lead.city && (
                  <div className="flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    <span>{lead.city}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Status e ações */}
          <div className="flex items-center gap-2">
            {lead.is_taken_over ? (
              <>
                <Badge className="bg-green-100 text-green-800">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Você está atendendo
                </Badge>
                <Button variant="outline" size="sm" onClick={handleReturnToAI}>
                  Devolver para IA
                </Button>
              </>
            ) : (
              <Button onClick={handleTakeOver} disabled={takingOver} size="sm">
                {takingOver ? 'Assumindo...' : 'Assumir Conversa'}
              </Button>
            )}
          </div>
        </div>

        {/* Informações do lead */}
        {(lead.interest || lead.budget) && (
          <div className="flex gap-4 text-sm">
            {lead.interest && (
              <div className="flex items-center gap-1 text-gray-600">
                <Home className="h-3 w-3" />
                <span>{lead.interest}</span>
              </div>
            )}
            {lead.budget && (
              <div className="flex items-center gap-1 text-gray-600">
                <DollarSign className="h-3 w-3" />
                <span>{lead.budget}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Área de mensagens */}
      <ScrollArea className="flex-1 p-4">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg) => {
              const isUser = msg.role === 'user';
              const isAI = msg.sender_type === 'ai' || (msg.role === 'assistant' && !msg.sender_type);
              const isSeller = msg.sender_type === 'seller';
              const isSystem = msg.sender_type === 'system' || msg.role === 'system';

              return (
                <div
                  key={msg.id}
                  className={cn(
                    'flex gap-3',
                    isUser && 'justify-end',
                    isSystem && 'justify-center'
                  )}
                >
                  {isSystem ? (
                    <Card className="px-4 py-2 bg-gray-50 text-center max-w-md">
                      <p className="text-xs text-gray-600">{msg.content}</p>
                    </Card>
                  ) : (
                    <>
                      {/* Ícone do remetente (esquerda) */}
                      {!isUser && (
                        <div
                          className={cn(
                            'flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center',
                            isAI && 'bg-blue-100',
                            isSeller && 'bg-green-100'
                          )}
                        >
                          {isAI ? (
                            <Bot className="h-4 w-4 text-blue-600" />
                          ) : (
                            <User className="h-4 w-4 text-green-600" />
                          )}
                        </div>
                      )}

                      {/* Mensagem */}
                      <div className={cn('flex flex-col', isUser && 'items-end')}>
                        <div
                          className={cn(
                            'rounded-lg px-4 py-2 max-w-md',
                            isUser && 'bg-blue-600 text-white',
                            isAI && 'bg-gray-100 text-gray-900',
                            isSeller && 'bg-green-100 text-gray-900'
                          )}
                        >
                          {!isUser && msg.sender_name && (
                            <p className="text-xs font-medium mb-1">
                              {msg.sender_name}
                            </p>
                          )}
                          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        </div>
                        <span className="text-xs text-gray-400 mt-1">
                          {new Date(msg.created_at).toLocaleTimeString('pt-BR', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>

                      {/* Ícone do usuário (direita) */}
                      {isUser && (
                        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
                          <User className="h-4 w-4 text-blue-600" />
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </ScrollArea>

      {/* Input de mensagem */}
      <div className="border-t p-4 bg-white">
        {!lead.is_taken_over && (
          <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5" />
            <p className="text-sm text-yellow-800">
              Você precisa assumir a conversa antes de enviar mensagens.
              A IA está atendendo automaticamente.
            </p>
          </div>
        )}

        <form onSubmit={handleSendMessage} className="flex gap-2">
          <Textarea
            placeholder={
              lead.is_taken_over
                ? 'Digite sua mensagem...'
                : 'Assuma a conversa para enviar mensagens'
            }
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={!lead.is_taken_over || sending}
            className="min-h-[60px] max-h-[120px]"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage(e);
              }
            }}
          />
          <Button
            type="submit"
            disabled={!lead.is_taken_over || !message.trim() || sending}
            className="flex-shrink-0"
          >
            {sending ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
        <p className="text-xs text-gray-500 mt-2">
          {lead.is_taken_over
            ? 'Pressione Enter para enviar • Shift+Enter para nova linha'
            : 'IA atendendo automaticamente'}
        </p>
      </div>
    </div>
  );
}
