'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getLead, getLeadMessages } from '@/lib/api';
import { 
  ArrowLeft, 
  Phone, 
  Mail, 
  MapPin, 
  ChevronDown,
  Bot,
  User,
  Calendar,
  Clock,
  MessageSquare,
  Sparkles
} from 'lucide-react';

interface Lead {
  id: number;
  name: string | null;
  phone: string | null;
  email: string | null;
  city: string | null;
  qualification: string;
  status: string;
  summary: string | null;
  custom_data: Record<string, unknown>;
  created_at: string;
}

interface Message {
  id: number;
  role: string;
  content: string;
  created_at: string;
}

// Helper para agrupar mensagens por data
function groupMessagesByDate(messages: Message[]): Map<string, Message[]> {
  const groups = new Map<string, Message[]>();
  
  messages.forEach(msg => {
    const date = new Date(msg.created_at).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric'
    });
    
    if (!groups.has(date)) {
      groups.set(date, []);
    }
    groups.get(date)!.push(msg);
  });
  
  return groups;
}

// Helper para verificar se é hoje
function isToday(dateString: string): boolean {
  const date = new Date(dateString);
  const today = new Date();
  return date.toDateString() === today.toDateString();
}

// Helper para verificar se é ontem
function isYesterday(dateString: string): boolean {
  const date = new Date(dateString);
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return date.toDateString() === yesterday.toDateString();
}

// Helper para formatar data amigável
function formatDateLabel(dateString: string, originalDate: string): string {
  if (isToday(originalDate)) return 'Hoje';
  if (isYesterday(originalDate)) return 'Ontem';
  return dateString;
}

export default function LeadDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [lead, setLead] = useState<Lead | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [hoveredMessage, setHoveredMessage] = useState<number | null>(null);
  
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [leadData, messagesData] = await Promise.all([
          getLead(Number(params.id)),
          getLeadMessages(Number(params.id))
        ]);
        setLead(leadData as Lead);
        setMessages(messagesData as Message[]);
      } catch (error) {
        console.error('Erro ao carregar lead:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [params.id]);

  // Auto-scroll para última mensagem quando carrega
  useEffect(() => {
    if (!loading && chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [loading, messages]);

  // Detecta scroll para mostrar/esconder botão
  const handleScroll = () => {
    if (chatContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      setShowScrollButton(!isNearBottom);
    }
  };

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="text-gray-500 text-sm">Carregando conversa...</span>
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-4">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
          <User className="w-8 h-8 text-gray-400" />
        </div>
        <p className="text-gray-500">Lead não encontrado</p>
        <button
          onClick={() => router.back()}
          className="text-blue-600 hover:underline text-sm"
        >
          Voltar
        </button>
      </div>
    );
  }

  const qualificationVariant = { hot: 'hot', warm: 'warm', cold: 'cold' } as const;
  const qualificationLabels: Record<string, string> = {
    hot: 'QUENTE',
    warm: 'MORNO', 
    cold: 'FRIO',
    quente: 'QUENTE',
    morno: 'MORNO',
    frio: 'FRIO'
  };

  const statusLabels: Record<string, string> = {
    novo: 'Novo',
    new: 'Novo',
    em_atendimento: 'Em Atendimento',
    in_progress: 'Em Atendimento',
    qualificado: 'Qualificado',
    qualified: 'Qualificado',
    transferido: 'Transferido',
    handed_off: 'Transferido',
    convertido: 'Convertido',
    converted: 'Convertido',
    perdido: 'Perdido',
    lost: 'Perdido'
  };

  const messageGroups = groupMessagesByDate(messages);

  return (
    <div className="space-y-4 md:space-y-6 pb-4">
      {/* Header */}
      <div className="flex items-center gap-3 md:gap-4">
        <button
          onClick={() => router.back()}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl md:text-2xl font-bold text-gray-900 truncate">
            {lead.name || 'Lead sem nome'}
          </h1>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <Badge variant={qualificationVariant[lead.qualification as keyof typeof qualificationVariant] || 'default'}>
              {qualificationLabels[lead.qualification] || lead.qualification.toUpperCase()}
            </Badge>
            <span className="text-gray-400 hidden sm:inline">•</span>
            <span className="text-gray-500 text-sm">
              {statusLabels[lead.status] || lead.status}
            </span>
          </div>
        </div>
      </div>

      {/* Layout Principal */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        
        {/* Coluna Esquerda - Info + Resumo (empilhados no mobile) */}
        <div className="lg:col-span-1 space-y-4 order-2 lg:order-1">
          
          {/* Card de Informações */}
          <Card>
            <CardHeader title="Informações" />
            <div className="space-y-3 p-4 pt-0">
              {lead.phone && (
                <a 
                  href={`tel:${lead.phone}`}
                  className="flex items-center gap-3 p-2 -mx-2 rounded-lg hover:bg-gray-50 transition-colors group"
                >
                  <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <Phone className="w-4 h-4 text-green-600" />
                  </div>
                  <span className="text-gray-700 group-hover:text-green-600 transition-colors truncate">
                    {lead.phone}
                  </span>
                </a>
              )}
              
              {lead.email && (
                <a 
                  href={`mailto:${lead.email}`}
                  className="flex items-center gap-3 p-2 -mx-2 rounded-lg hover:bg-gray-50 transition-colors group"
                >
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <Mail className="w-4 h-4 text-blue-600" />
                  </div>
                  <span className="text-gray-700 group-hover:text-blue-600 transition-colors truncate">
                    {lead.email}
                  </span>
                </a>
              )}
              
              {lead.city && (
                <div className="flex items-center gap-3 p-2 -mx-2">
                  <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <MapPin className="w-4 h-4 text-purple-600" />
                  </div>
                  <span className="text-gray-700 truncate">{lead.city}</span>
                </div>
              )}

              <div className="flex items-center gap-3 p-2 -mx-2">
                <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <Calendar className="w-4 h-4 text-gray-500" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-gray-400">Criado em</p>
                  <p className="text-gray-700 text-sm">
                    {new Date(lead.created_at).toLocaleDateString('pt-BR', {
                      day: '2-digit',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
              </div>

              {/* Dados Adicionais */}
              {lead.custom_data && Object.keys(lead.custom_data).length > 0 && (
                <div className="pt-3 mt-3 border-t border-gray-100">
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
                    Dados adicionais
                  </p>
                  <div className="space-y-2">
                    {Object.entries(lead.custom_data)
                      .filter(([, value]) => value)
                      .map(([key, value]) => (
                        <div 
                          key={key} 
                          className="flex justify-between items-start gap-2 text-sm py-1"
                        >
                          <span className="text-gray-500 flex-shrink-0">{key}:</span>
                          <span className="text-gray-900 text-right truncate">
                            {String(value)}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Card de Resumo IA */}
          {lead.summary && (
            <Card>
              <CardHeader title={
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-500" />
                  <span>Resumo da IA</span>
                </div>
              } />
              <div className="p-4 pt-0">
                <p className="text-gray-600 text-sm leading-relaxed">
                  {lead.summary}
                </p>
              </div>
            </Card>
          )}
        </div>

        {/* Coluna Direita - Chat (aparece primeiro no mobile) */}
        <div className="lg:col-span-2 order-1 lg:order-2">
          <Card className="flex flex-col h-[60vh] md:h-[70vh] lg:h-[calc(100vh-220px)] min-h-[400px]">
            {/* Header do Chat */}
            <div className="flex items-center justify-between p-4 border-b border-gray-100 flex-shrink-0">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-gray-400" />
                <h3 className="font-semibold text-gray-900">Histórico da Conversa</h3>
              </div>
              <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
                {messages.length} {messages.length === 1 ? 'mensagem' : 'mensagens'}
              </span>
            </div>

            {/* Área de Mensagens */}
            <div
              ref={chatContainerRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth"
              style={{
                scrollbarWidth: 'thin',
                scrollbarColor: '#E5E7EB transparent'
              }}
            >
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
                  <MessageSquare className="w-12 h-12 opacity-50" />
                  <p>Nenhuma mensagem ainda</p>
                </div>
              ) : (
                <>
                  {Array.from(messageGroups.entries()).map(([date, dateMessages]) => (
                    <div key={date}>
                      {/* Separador de Data */}
                      <div className="flex items-center justify-center my-4">
                        <div className="flex-1 h-px bg-gray-200"></div>
                        <span className="px-3 text-xs text-gray-400 bg-white">
                          {formatDateLabel(date, dateMessages[0].created_at)}
                        </span>
                        <div className="flex-1 h-px bg-gray-200"></div>
                      </div>

                      {/* Mensagens do Dia */}
                      <div className="space-y-3">
                        {dateMessages.map((msg, idx) => {
                          const isAssistant = msg.role === 'assistant';
                          const showAvatar = idx === 0 || dateMessages[idx - 1]?.role !== msg.role;
                          
                          return (
                            <div
                              key={msg.id}
                              className={`flex ${isAssistant ? 'justify-start' : 'justify-end'}`}
                              onMouseEnter={() => setHoveredMessage(msg.id)}
                              onMouseLeave={() => setHoveredMessage(null)}
                            >
                              {/* Avatar IA */}
                              {isAssistant && (
                                <div className={`flex-shrink-0 mr-2 ${showAvatar ? 'visible' : 'invisible'}`}>
                                  <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center shadow-sm">
                                    <Bot className="w-4 h-4 text-white" />
                                  </div>
                                </div>
                              )}

                              {/* Balão da Mensagem */}
                              <div
                                className={`
                                  relative max-w-[85%] sm:max-w-[75%] px-4 py-2.5 rounded-2xl
                                  ${isAssistant 
                                    ? 'bg-gray-100 text-gray-800 rounded-tl-md' 
                                    : 'bg-blue-600 text-white rounded-tr-md'
                                  }
                                `}
                              >
                                <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                                  {msg.content}
                                </p>
                                
                                {/* Hora */}
                                <div className={`
                                  flex items-center gap-1 mt-1
                                  ${isAssistant ? 'text-gray-400' : 'text-blue-200'}
                                `}>
                                  <Clock className="w-3 h-3" />
                                  <span className="text-xs">
                                    {new Date(msg.created_at).toLocaleTimeString('pt-BR', {
                                      hour: '2-digit',
                                      minute: '2-digit'
                                    })}
                                  </span>
                                </div>

                                {/* Tooltip com data/hora completa */}
                                {hoveredMessage === msg.id && (
                                  <div className={`
                                    absolute -top-8 px-2 py-1 text-xs bg-gray-900 text-white rounded
                                    whitespace-nowrap z-10 shadow-lg
                                    ${isAssistant ? 'left-0' : 'right-0'}
                                  `}>
                                    {new Date(msg.created_at).toLocaleString('pt-BR')}
                                  </div>
                                )}
                              </div>

                              {/* Avatar Usuário */}
                              {!isAssistant && (
                                <div className={`flex-shrink-0 ml-2 ${showAvatar ? 'visible' : 'invisible'}`}>
                                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center shadow-sm">
                                    <User className="w-4 h-4 text-white" />
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </>
              )}
              
              {/* Ref para scroll */}
              <div ref={chatEndRef} />
            </div>

            {/* Botão Scroll to Bottom */}
            {showScrollButton && (
              <div className="absolute bottom-20 right-6">
                <button
                  onClick={scrollToBottom}
                  className="p-2 bg-white border border-gray-200 rounded-full shadow-lg hover:bg-gray-50 transition-all hover:scale-105"
                >
                  <ChevronDown className="w-5 h-5 text-gray-600" />
                </button>
              </div>
            )}

            {/* Footer do Chat */}
            <div className="p-3 border-t border-gray-100 bg-gray-50/50 flex-shrink-0 rounded-b-xl">
              <p className="text-xs text-gray-400 text-center">
                Conversa gerenciada pela IA do Velaris
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}