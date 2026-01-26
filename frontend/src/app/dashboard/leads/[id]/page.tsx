'use client';

/**
 * LEAD DETAIL PAGE (v4) - PREMIUM EDITION
 * ==========================================
 * Design inspirado em: HubSpot, Salesforce, Pipedrive
 * Histórico de conversas: Estilo WhatsApp Web (igual ao inbox)
 */

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  getLead,
  getLeadMessages,
  updateLead,
  getLeadEvents,
  getLeadOpportunities,
  Opportunity,
} from '@/lib/api';
import {
  ArrowLeft,
  MessageCircle,
  TrendingUp,
  Phone,
  Mail,
  MapPin,
  Clock,
  User,
  CheckCircle2,
  Loader2,
  Plus,
  Calendar,
  DollarSign,
  Tag,
  Building2,
  Star,
  Check,
  CheckCheck,
  ExternalLink,
  Edit2,
  MoreHorizontal,
} from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { cn } from '@/lib/utils';

// =============================================
// TIPOS
// =============================================

interface Lead {
  id: number;
  name: string | null;
  email: string | null;
  phone: string;
  city: string | null;
  status: string;
  qualification: string;
  summary: string | null;
  interest: string | null;
  budget: string | null;
  created_at: string;
  assigned_seller: { id: number; name: string } | null;
  custom_data?: {
    tags?: string[];
    company?: string;
    position?: string;
    notes?: string;
  };
}

interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  sender_type?: 'ai' | 'seller' | 'system';
  sender_name?: string | null;
  status?: 'sent' | 'delivered' | 'read';
}

interface LeadEvent {
  id: number;
  event_type: string;
  old_value: string | null;
  new_value: string | null;
  description: string;
  created_at: string;
}

// =============================================
// COMPONENTE PRINCIPAL
// =============================================

export default function LeadDetailPage() {
  const params = useParams();
  const router = useRouter();

  const [lead, setLead] = useState<Lead | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [events, setEvents] = useState<LeadEvent[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'activity' | 'opportunities'>('activity');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadData();
  }, [params.id]);

  useEffect(() => {
    if (activeTab === 'activity') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, activeTab]);

  async function loadData() {
    try {
      setLoading(true);
      const [leadData, messagesData, eventsData, oppsData] = await Promise.all([
        getLead(Number(params.id)),
        getLeadMessages(Number(params.id)),
        getLeadEvents(Number(params.id)).catch(() => []),
        getLeadOpportunities(Number(params.id)).catch(() => []),
      ]);

      setLead(leadData as Lead);
      setMessages(messagesData as Message[]);
      setEvents(eventsData as LeadEvent[]);
      setOpportunities(oppsData as Opportunity[]);
    } catch (error) {
      console.error('Erro ao carregar lead:', error);
    } finally {
      setLoading(false);
    }
  }

  const atualizarQualificacao = async (novaQualificacao: string) => {
    if (!lead) return;
    try {
      await updateLead(lead.id, { qualification: novaQualificacao });
      setLead({ ...lead, qualification: novaQualificacao });
    } catch {
      alert('Erro ao atualizar qualificação');
    }
  };

  const atualizarStatus = async (novoStatus: string) => {
    if (!lead) return;
    try {
      await updateLead(lead.id, { status: novoStatus });
      setLead({ ...lead, status: novoStatus });
    } catch {
      alert('Erro ao atualizar status');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4 bg-gray-50">
        <h3 className="text-xl font-semibold text-gray-900">Lead não encontrado</h3>
        <Button onClick={() => router.back()}>Voltar</Button>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 overflow-hidden">
      {/* Header fixo - estilo Salesforce/HubSpot */}
      <div className="bg-white border-b border-gray-200 shadow-sm flex-shrink-0">
        <div className="px-6 py-4">
          <div className="flex items-start justify-between">
            {/* Info do Lead */}
            <div className="flex items-start gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.back()}
                className="mt-1"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Voltar
              </Button>

              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold text-gray-900">
                    {lead.name || 'Lead sem nome'}
                  </h1>
                  <StatusBadge status={lead.status} />
                  <QualificationBadge qualification={lead.qualification} />
                </div>

                <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                  {lead.phone && (
                    <span className="flex items-center gap-1">
                      <Phone className="w-3.5 h-3.5" />
                      {lead.phone}
                    </span>
                  )}
                  {lead.email && (
                    <span className="flex items-center gap-1">
                      <Mail className="w-3.5 h-3.5" />
                      {lead.email}
                    </span>
                  )}
                  {lead.city && (
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5" />
                      {lead.city}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {format(new Date(lead.created_at), "dd/MM/yyyy", { locale: ptBR })}
                  </span>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="gap-2">
                <Phone className="w-4 h-4" />
                Ligar
              </Button>
              <Button variant="outline" size="sm" className="gap-2">
                <Mail className="w-4 h-4" />
                Email
              </Button>
              <Button variant="outline" size="sm" className="gap-2">
                <MessageCircle className="w-4 h-4" />
                WhatsApp
              </Button>
              <Button variant="outline" size="sm">
                <MoreHorizontal className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="px-6">
          <div className="flex gap-6 border-b border-gray-200">
            <button
              onClick={() => setActiveTab('activity')}
              className={cn(
                "px-1 py-3 font-medium text-sm border-b-2 transition-colors",
                activeTab === 'activity'
                  ? "text-blue-600 border-blue-600"
                  : "text-gray-600 border-transparent hover:text-gray-900"
              )}
            >
              Atividade
            </button>
            <button
              onClick={() => setActiveTab('opportunities')}
              className={cn(
                "px-1 py-3 font-medium text-sm border-b-2 transition-colors flex items-center gap-2",
                activeTab === 'opportunities'
                  ? "text-blue-600 border-blue-600"
                  : "text-gray-600 border-transparent hover:text-gray-900"
              )}
            >
              Oportunidades
              {opportunities.length > 0 && (
                <Badge className="bg-green-100 text-green-700 text-xs">
                  {opportunities.length}
                </Badge>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Layout 3 colunas - SEM SCROLL EXTERNO */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full max-w-[1600px] mx-auto grid grid-cols-12 gap-6 p-6">
          {/* Coluna principal (conversas/atividades) */}
          <div className="col-span-8 h-full">
            {activeTab === 'activity' && (
              <WhatsAppConversation messages={messages} events={events} messagesEndRef={messagesEndRef} />
            )}
            {activeTab === 'opportunities' && (
              <OpportunitiesPanel opportunities={opportunities} leadId={lead.id} onReload={loadData} />
            )}
          </div>

          {/* Sidebar direita - Info do Lead - COM SCROLL PRÓPRIO */}
          <div className="col-span-4 h-full overflow-y-auto space-y-4 pr-2">
            <LeadInfoSidebar lead={lead} onUpdate={setLead} onUpdateQualification={atualizarQualificacao} onUpdateStatus={atualizarStatus} />
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================
// COMPONENTE: WhatsApp Conversation
// =============================================

function WhatsAppConversation({
  messages,
  events,
  messagesEndRef
}: {
  messages: Message[];
  events: LeadEvent[];
  messagesEndRef: React.RefObject<HTMLDivElement>;
}) {
  // Combinar mensagens e eventos em timeline
  const timeline = [
    ...messages.map(m => ({ type: 'message' as const, data: m, date: new Date(m.created_at) })),
    ...events.map(e => ({ type: 'event' as const, data: e, date: new Date(e.created_at) })),
  ].sort((a, b) => a.date.getTime() - b.date.getTime());

  return (
    <Card className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4 bg-white flex-shrink-0">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-blue-600" />
          Histórico de Conversas
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          {messages.length} mensagens • {events.length} eventos
        </p>
      </div>

      {/* Área de mensagens - ESTILO WHATSAPP - SCROLL APENAS AQUI */}
      <div className="flex-1 overflow-y-auto bg-[#e5ddd5] relative">
        {/* Padrão de fundo WhatsApp */}
        <div
          className="absolute inset-0 opacity-[0.06] pointer-events-none"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />

        {timeline.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <MessageCircle className="w-16 h-16 text-gray-300 mb-4" />
            <p className="text-gray-500">Nenhuma interação registrada</p>
          </div>
        ) : (
          <div className="px-[8%] py-6 space-y-3 relative">
            {timeline.map((item, idx) => {
              if (item.type === 'event') {
                const event = item.data as LeadEvent;
                return (
                  <div key={`event-${idx}`} className="flex justify-center my-4">
                    <div className="bg-[#ffffffdd] backdrop-blur-sm px-4 py-2 rounded-lg shadow-sm max-w-md">
                      <p className="text-xs text-gray-700 text-center font-medium">
                        {event.description}
                      </p>
                      <p className="text-[10px] text-gray-500 text-center mt-1">
                        {format(new Date(event.created_at), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
                      </p>
                    </div>
                  </div>
                );
              }

              const msg = item.data as Message;
              const isUser = msg.role === 'user';
              const isAI = msg.sender_type === 'ai' || (msg.role === 'assistant' && !msg.sender_type);
              const isSeller = msg.sender_type === 'seller';
              const isSystem = msg.sender_type === 'system' || msg.role === 'system';

              const messageTime = new Date(msg.created_at).toLocaleTimeString('pt-BR', {
                hour: '2-digit',
                minute: '2-digit',
              });

              if (isSystem) {
                return (
                  <div key={`msg-${idx}`} className="flex justify-center my-4">
                    <div className="bg-[#ffffffdd] backdrop-blur-sm px-4 py-2 rounded-lg shadow-sm">
                      <p className="text-xs text-gray-700 font-medium">{msg.content}</p>
                    </div>
                  </div>
                );
              }

              return (
                <div
                  key={`msg-${idx}`}
                  className={cn(
                    'flex mb-2',
                    (isSeller || isAI) ? 'justify-end' : 'justify-start'
                  )}
                >
                  <div
                    className={cn(
                      'relative max-w-[70%] rounded-lg px-3 py-2',
                      (isSeller || isAI)
                        ? 'bg-[#d9fdd3] rounded-tr-none shadow-md'
                        : 'bg-white rounded-tl-none shadow-md'
                    )}
                    style={{ wordWrap: 'break-word' }}
                  >
                    {/* Nome do remetente */}
                    {!isUser && msg.sender_name && (
                      <p className={cn(
                        "text-xs font-semibold mb-1.5",
                        isAI ? "text-blue-700" : "text-green-700"
                      )}>
                        {msg.sender_name}
                      </p>
                    )}

                    {/* Conteúdo */}
                    <p className="text-[14.5px] text-gray-900 whitespace-pre-wrap break-words leading-relaxed">
                      {msg.content}
                    </p>

                    {/* Timestamp e checks */}
                    <div className="flex items-center justify-end gap-1.5 mt-2">
                      <span className="text-[11px] text-gray-500 font-medium">
                        {messageTime}
                      </span>
                      {(isSeller || isAI) && (
                        <span className={cn(
                          "transition-colors",
                          msg.status === 'read' ? "text-blue-500" : "text-gray-500"
                        )}>
                          {msg.status === 'sent' ? (
                            <Check className="h-4 w-4" />
                          ) : (
                            <CheckCheck className="h-4 w-4" />
                          )}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
    </Card>
  );
}

// =============================================
// COMPONENTE: Sidebar de Informações
// =============================================

function LeadInfoSidebar({
  lead,
  onUpdate,
  onUpdateQualification,
  onUpdateStatus
}: {
  lead: Lead;
  onUpdate: (lead: Lead) => void;
  onUpdateQualification: (qual: string) => void;
  onUpdateStatus: (status: string) => void;
}) {
  return (
    <>
      {/* Card: Resumo */}
      {lead.summary && (
        <Card className="p-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Resumo</h4>
          <p className="text-sm text-gray-700 leading-relaxed">{lead.summary}</p>
        </Card>
      )}

      {/* Card: Detalhes */}
      <Card className="p-4">
        <h4 className="text-sm font-semibold text-gray-900 mb-3">Detalhes do Lead</h4>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Status</label>
            <select
              value={lead.status}
              onChange={(e) => onUpdateStatus(e.target.value)}
              className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="new">Novo</option>
              <option value="in_progress">Em Andamento</option>
              <option value="qualified">Qualificado</option>
              <option value="lost">Perdido</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Qualificação</label>
            <select
              value={lead.qualification}
              onChange={(e) => onUpdateQualification(e.target.value)}
              className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="cold">🧊 Frio</option>
              <option value="warm">🌤️ Morno</option>
              <option value="hot">🔥 Quente</option>
            </select>
          </div>

          {lead.assigned_seller && (
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Vendedor</label>
              <p className="mt-1 text-sm text-gray-900">{lead.assigned_seller.name}</p>
            </div>
          )}

          {lead.interest && (
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Interesse</label>
              <p className="mt-1 text-sm text-gray-900">{lead.interest}</p>
            </div>
          )}

          {lead.budget && (
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Orçamento</label>
              <p className="mt-1 text-sm text-gray-900">{lead.budget}</p>
            </div>
          )}

          {lead.custom_data?.company && (
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Empresa</label>
              <p className="mt-1 text-sm text-gray-900">{lead.custom_data.company}</p>
            </div>
          )}

          {lead.custom_data?.position && (
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Cargo</label>
              <p className="mt-1 text-sm text-gray-900">{lead.custom_data.position}</p>
            </div>
          )}
        </div>
      </Card>

      {/* Card: Tags */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-gray-900">Tags</h4>
          <Button variant="ghost" size="sm" className="h-7 px-2">
            <Plus className="w-3.5 h-3.5" />
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {(lead.custom_data?.tags || []).map((tag: string) => (
            <Badge key={tag} variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
              {tag}
            </Badge>
          ))}
          {(!lead.custom_data?.tags || lead.custom_data.tags.length === 0) && (
            <p className="text-sm text-gray-500">Nenhuma tag</p>
          )}
        </div>
      </Card>

      {/* Card: Ações Rápidas */}
      <Card className="p-4">
        <h4 className="text-sm font-semibold text-gray-900 mb-3">Ações Rápidas</h4>
        <div className="space-y-2">
          <Button variant="outline" size="sm" className="w-full justify-start gap-2">
            <Calendar className="w-4 h-4" />
            Agendar Visita
          </Button>
          <Button variant="outline" size="sm" className="w-full justify-start gap-2">
            <TrendingUp className="w-4 h-4" />
            Criar Oportunidade
          </Button>
          <Button variant="outline" size="sm" className="w-full justify-start gap-2">
            <Edit2 className="w-4 h-4" />
            Adicionar Nota
          </Button>
        </div>
      </Card>
    </>
  );
}

// =============================================
// COMPONENTE: Oportunidades
// =============================================

function OpportunitiesPanel({
  opportunities,
  leadId,
  onReload
}: {
  opportunities: Opportunity[];
  leadId: number;
  onReload: () => void;
}) {
  return (
    <Card className="h-full flex flex-col overflow-hidden">
      <div className="border-b border-gray-200 px-6 py-4 bg-white flex items-center justify-between flex-shrink-0">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-600" />
            Oportunidades
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {opportunities.length} {opportunities.length === 1 ? 'oportunidade' : 'oportunidades'}
          </p>
        </div>
        <Button className="gap-2">
          <Plus className="w-4 h-4" />
          Nova Oportunidade
        </Button>
      </div>

      {/* SCROLL APENAS AQUI */}
      <div className="flex-1 overflow-y-auto">
        {opportunities.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <TrendingUp className="w-16 h-16 text-gray-300 mb-4" />
            <p className="text-gray-500 font-medium">Nenhuma oportunidade criada</p>
            <p className="text-sm text-gray-400 mt-1">
              Crie uma oportunidade para começar a rastrear vendas
            </p>
          </div>
        ) : (
          <div className="p-6 space-y-4">
            {opportunities.map(opp => (
              <Card key={opp.id} className="p-5 hover:shadow-lg transition-all border border-gray-200">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-semibold text-gray-900 text-base">{opp.title}</h4>
                    {opp.description && (
                      <p className="text-sm text-gray-600 mt-1 leading-relaxed">{opp.description}</p>
                    )}
                    <div className="flex items-center gap-3 mt-3">
                      <Badge className="bg-green-100 text-green-700 font-semibold">
                        R$ {opp.value?.toLocaleString('pt-BR')}
                      </Badge>
                      <span className="text-sm text-gray-500 capitalize">{opp.stage}</span>
                      {opp.expected_close_date && (
                        <span className="text-xs text-gray-400">
                          Fecha em {format(new Date(opp.expected_close_date), "dd/MM/yyyy", { locale: ptBR })}
                        </span>
                      )}
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">
                    <ExternalLink className="w-4 h-4" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

// =============================================
// COMPONENTES: Badges
// =============================================

function StatusBadge({ status }: { status: string }) {
  const config = {
    new: { label: 'Novo', className: 'bg-blue-100 text-blue-700' },
    in_progress: { label: 'Em Andamento', className: 'bg-yellow-100 text-yellow-700' },
    qualified: { label: 'Qualificado', className: 'bg-green-100 text-green-700' },
    lost: { label: 'Perdido', className: 'bg-red-100 text-red-700' },
  };

  const { label, className } = config[status as keyof typeof config] || config.new;

  return (
    <Badge className={cn('text-xs font-semibold', className)}>
      {label}
    </Badge>
  );
}

function QualificationBadge({ qualification }: { qualification: string }) {
  const config = {
    hot: { label: '🔥 Quente', className: 'bg-red-100 text-red-700' },
    warm: { label: '🌤️ Morno', className: 'bg-orange-100 text-orange-700' },
    cold: { label: '🧊 Frio', className: 'bg-blue-100 text-blue-700' },
  };

  const { label, className } = config[qualification as keyof typeof config] || config.cold;

  return (
    <Badge className={cn('text-xs font-semibold', className)}>
      {label}
    </Badge>
  );
}
