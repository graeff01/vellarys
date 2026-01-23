'use client';

import { useEffect, useState, useRef } from 'react';
import {
  X,
  Phone,
  Calendar,
  MessageSquare,
  Bot,
  User,
  Clock,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  MoreHorizontal,
  Send,
  History,
  Info,
  UserPlus
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { getLeadMessages, getLeadEvents } from '@/lib/api';

// =============================================
// TYPES
// =============================================

interface AssignedSeller {
  id: number;
  name: string;
  whatsapp: string;
}

interface Lead {
  id: number;
  name: string | null;
  phone: string | null;
  qualification: string;
  status: string;
  created_at: string;
  assigned_seller?: AssignedSeller | null;
  // Campos potenciais para o futuro
  email?: string;
  location?: string;
  summary?: string;
}

interface Message {
  id: number;
  content: string;
  direction: 'inbound' | 'outbound';
  channel: string;
  created_at: string;
}

interface LeadEvent {
  id: number;
  title: string;
  description?: string;
  created_at: string;
  type?: 'system' | 'user' | 'ai';
}

interface LeadsQuickviewProps {
  lead: Lead | null;
  onClose: () => void;
  onOpenAssignModal: (leadId: number) => void;
}

// =============================================
// CONFIG
// =============================================

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  novo: { label: 'Novo', color: 'text-blue-700', bg: 'bg-blue-50' },
  new: { label: 'Novo', color: 'text-blue-700', bg: 'bg-blue-50' },
  em_atendimento: { label: 'Em Atendimento', color: 'text-amber-700', bg: 'bg-amber-50' },
  in_progress: { label: 'Em Atendimento', color: 'text-amber-700', bg: 'bg-amber-50' },
  qualificado: { label: 'Qualificado', color: 'text-emerald-700', bg: 'bg-emerald-50' },
  qualified: { label: 'Qualificado', color: 'text-emerald-700', bg: 'bg-emerald-50' },
  contacted: { label: 'Em Contato', color: 'text-indigo-700', bg: 'bg-indigo-50' },
  transferido: { label: 'Transferido', color: 'text-purple-700', bg: 'bg-purple-50' },
  handed_off: { label: 'Transferido', color: 'text-purple-700', bg: 'bg-purple-50' },
  convertido: { label: 'Convertido', color: 'text-green-700', bg: 'bg-green-50' },
  converted: { label: 'Convertido', color: 'text-green-700', bg: 'bg-green-50' },
  perdido: { label: 'Perdido', color: 'text-rose-700', bg: 'bg-rose-50' },
  lost: { label: 'Perdido', color: 'text-rose-700', bg: 'bg-rose-50' },
  closed: { label: 'Fechado', color: 'text-slate-700', bg: 'bg-slate-50' },
};

// =============================================
// COMPONENT
// =============================================

export function LeadsQuickview({
  lead,
  onClose,
  onOpenAssignModal,
}: LeadsQuickviewProps) {
  const [activeTab, setActiveTab] = useState<'chat' | 'timeline' | 'info'>('chat');
  const [messages, setMessages] = useState<Message[]>([]);
  const [events, setEvents] = useState<LeadEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const leadId = lead?.id;

  // Carrega dados
  useEffect(() => {
    if (!leadId) {
      setMessages([]);
      setEvents([]);
      return;
    }

    async function loadData() {
      setLoading(true);
      try {
        const [msgsData, eventsData] = await Promise.all([
          getLeadMessages(leadId as number),
          getLeadEvents(leadId as number).catch(() => []), // Falha silenciosa para eventos por enquanto
        ]);

        const msgs = Array.isArray(msgsData) ? msgsData : ((msgsData as any)?.messages || []);
        setMessages(msgs);
        setEvents(eventsData as any[]);
      } catch (err) {
        console.error('Erro ao carregar dados:', err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [leadId]);

  // Auto-scroll chat
  useEffect(() => {
    if (activeTab === 'chat' && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, activeTab]);

  if (!lead) return null;

  const status = STATUS_CONFIG[lead.status] || { label: lead.status, color: 'text-gray-700', bg: 'bg-gray-100' };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Slide-over Panel */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-white shadow-2xl flex flex-col transform transition-transform duration-300 ease-out border-l border-slate-100">

        {/* HEADER PREMIUM */}
        <div className="relative overflow-hidden bg-slate-900 text-white shrink-0">
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-600 to-purple-700 opacity-90" />

          {/* Decorative circles */}
          <div className="absolute top-0 right-0 -mt-10 -mr-10 w-40 h-40 bg-white/10 rounded-full blur-2xl" />
          <div className="absolute bottom-0 left-0 -mb-10 -ml-10 w-40 h-40 bg-indigo-500/20 rounded-full blur-2xl" />

          <div className="relative p-6">
            <div className="flex items-start justify-between mb-6">
              <button
                onClick={onClose}
                className="p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-all backdrop-blur-md"
              >
                <X className="w-5 h-5" />
              </button>
              <div className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-white/20 backdrop-blur-md ${status.color.replace('text-', 'text-white ')} border border-white/20`}>
                {status.label}
              </div>
            </div>

            <div className="flex items-center gap-5">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-white/20 to-white/5 backdrop-blur-md border border-white/20 flex items-center justify-center text-2xl font-bold shadow-xl">
                {lead.name?.charAt(0) || <User className="w-8 h-8" />}
              </div>

              <div>
                <h2 className="text-2xl font-bold tracking-tight text-white mb-1">
                  {lead.name || 'Lead sem nome'}
                </h2>
                <div className="flex items-center gap-3 text-indigo-100 text-sm">
                  {lead.phone && (
                    <div className="flex items-center gap-1.5 bg-white/10 px-2 py-0.5 rounded-md">
                      <Phone className="w-3.5 h-3.5" />
                      <span className="font-mono opacity-90">{lead.phone}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1.5 opacity-75">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>
                      {new Date(lead.created_at).toLocaleDateString('pt-BR')}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* TABS HEADER */}
          <div className="flex items-center px-2 bg-black/20 backdrop-blur-sm">
            {[
              { id: 'chat', label: 'Conversa', icon: MessageSquare },
              { id: 'timeline', label: 'Linha do Tempo', icon: History },
              { id: 'info', label: 'Informações', icon: Info },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`
                  flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-all relative
                  ${activeTab === tab.id ? 'text-white' : 'text-slate-400 hover:text-slate-200'}
                `}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
                {activeTab === tab.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-white rounded-t-full" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* CONTENT AREA */}
        <div className="flex-1 bg-slate-50 overflow-hidden flex flex-col relative">

          {/* === ABA CHAT === */}
          {activeTab === 'chat' && (
            <div className="flex flex-col h-full absolute inset-0">
              {/* Messages Area */}
              <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-4 space-y-4"
              >
                {loading ? (
                  <div className="flex flex-col items-center justify-center h-full space-y-3">
                    <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-sm text-slate-500 font-medium">Carregando histórico...</p>
                  </div>
                ) : messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center p-8 bg-white m-4 rounded-3xl border border-dashed border-slate-200">
                    <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4">
                      <MessageSquare className="w-8 h-8 text-slate-300" />
                    </div>
                    <h3 className="text-slate-900 font-bold mb-1">Nenhuma mensagem</h3>
                    <p className="text-slate-500 text-sm">Este lead ainda não iniciou uma conversa.</p>
                  </div>
                ) : (
                  <>
                    <div className="text-center py-4">
                      <span className="px-3 py-1 bg-slate-200 text-slate-600 text-[10px] uppercase font-bold rounded-full tracking-wider">
                        Início da Conversa
                      </span>
                    </div>
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex gap-3 ${msg.direction === 'outbound' ? 'flex-row' : 'flex-row-reverse'}`}
                      >
                        {/* Avatar */}
                        <div className={`
                          w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-sm
                          ${msg.direction === 'outbound'
                            ? 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white'
                            : 'bg-white border border-slate-200 text-slate-600'}
                        `}>
                          {msg.direction === 'outbound' ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                        </div>

                        {/* Bubble */}
                        <div className={`
                          max-w-[75%] space-y-1
                          ${msg.direction === 'outbound' ? 'items-start' : 'items-end flex flex-col'}
                        `}>
                          <div className={`
                            px-4 py-3 text-sm shadow-sm
                            ${msg.direction === 'outbound'
                              ? 'bg-white rounded-2xl rounded-tl-sm border border-slate-100 text-slate-700'
                              : 'bg-indigo-600 text-white rounded-2xl rounded-tr-sm'}
                          `}>
                            <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                          </div>
                          <span className="text-[10px] font-medium text-slate-400 px-1">
                            {new Date(msg.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>

              {/* Chat Input (Visual only for now) */}
              <div className="p-4 bg-white border-t border-slate-100">
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Escrever observação interna..."
                    className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                  />
                  <button className="p-2 bg-slate-900 text-white rounded-xl hover:bg-slate-800 transition-colors">
                    <Send className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* === ABA TIMELINE === */}
          {activeTab === 'timeline' && (
            <div className="p-6 overflow-y-auto absolute inset-0">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-full space-y-3">
                  <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : events.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <History className="w-12 h-12 text-slate-200 mb-3" />
                  <p className="text-slate-500 font-medium">Nenhum evento registrado</p>
                </div>
              ) : (
                <div className="relative border-l-2 border-slate-200 ml-3 space-y-8 py-2">
                  {events.map((event, idx) => (
                    <div key={idx} className="relative pl-8">
                      {/* Dot */}
                      <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-white border-4 border-indigo-500 shadow-sm" />

                      <div className="flex flex-col gap-1">
                        <span className="text-xs font-bold text-indigo-600 uppercase tracking-widest">
                          {new Date(event.created_at).toLocaleDateString('pt-BR')} • {new Date(event.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <h4 className="font-bold text-slate-800">{event.title}</h4>
                        {event.description && (
                          <p className="text-sm text-slate-500 bg-white p-3 rounded-xl border border-slate-100 shadow-sm mt-1">
                            {event.description}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* === ABA INFO === */}
          {activeTab === 'info' && (
            <div className="p-6 overflow-y-auto absolute inset-0 space-y-6">

              {/* Smart Summary Card */}
              <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-2xl p-5 border border-indigo-100/50 shadow-sm">
                <div className="flex items-center gap-2 mb-3">
                  <div className="p-1.5 bg-indigo-100 rounded-lg">
                    <Bot className="w-4 h-4 text-indigo-600" />
                  </div>
                  <h3 className="font-bold text-indigo-900 text-sm uppercase tracking-wide">Analise da IA</h3>
                </div>

                <div className="space-y-3">
                  <div className="flex gap-3 items-start">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-semibold text-slate-800">Interesse Alto</p>
                      <p className="text-xs text-slate-500 leading-relaxed">O lead demonstrou alto engajamento e respondeu rapidamente às mensagens sobre valores.</p>
                    </div>
                  </div>
                  <div className="flex gap-3 items-start">
                    <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-semibold text-slate-800">Atenção Necessária</p>
                      <p className="text-xs text-slate-500 leading-relaxed">Cliente perguntou sobre financiamento e a IA não tinha info completa. Vendedor humano deve intervir.</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Seller Assignment */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
                  <h3 className="font-bold text-slate-700 text-xs uppercase tracking-wide">Vendedor Responsável</h3>
                  <button
                    onClick={() => onOpenAssignModal(lead.id)}
                    className="text-xs font-bold text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 px-2 py-1 rounded transition-colors"
                  >
                    Alterar
                  </button>
                </div>

                <div className="p-5">
                  {lead.assigned_seller ? (
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 font-bold text-lg">
                        {lead.assigned_seller.name.charAt(0)}
                      </div>
                      <div>
                        <p className="font-bold text-slate-900">{lead.assigned_seller.name}</p>
                        <div className="flex items-center gap-1.5 text-slate-500 text-sm mt-0.5">
                          <Phone className="w-3 h-3" />
                          {lead.assigned_seller.whatsapp}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-3 text-slate-300">
                        <UserPlus className="w-6 h-6" />
                      </div>
                      <p className="text-sm text-slate-500 mb-3">Este lead ainda não tem dono.</p>
                      <button
                        onClick={() => onOpenAssignModal(lead.id)}
                        className="px-4 py-2 bg-slate-900 text-white text-sm font-bold rounded-xl hover:bg-slate-800 transition-all shadow-lg shadow-slate-200"
                      >
                        Atribuir Agora
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Technical Details */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
                <h3 className="font-bold text-slate-700 text-xs uppercase tracking-wide mb-4">Detalhes Técnicos</h3>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <p className="text-xs text-slate-400 font-bold uppercase mb-1">ID do Lead</p>
                    <p className="text-sm font-mono font-semibold text-slate-700">#{lead.id}</p>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <p className="text-xs text-slate-400 font-bold uppercase mb-1">Canal</p>
                    <div className="flex items-center gap-1.5">
                      <MessageSquare className="w-3 h-3 text-emerald-500" />
                      <p className="text-sm font-semibold text-slate-700">WhatsApp</p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-100 rounded-xl text-amber-800 text-xs font-medium">
                  <Clock className="w-4 h-4 shrink-0" />
                  <span>Última interação há 2 horas</span>
                </div>
              </div>

            </div>
          )}
        </div>
      </div>
    </>
  );
}
