'use client';

/**
 * LEAD DETAIL PAGE (v3) - REDESIGN MODERNO
 * =========================================
 * Layout limpo e organizado com tabs para melhor UX
 */

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  getLead,
  getLeadMessages,
  updateLead,
  getLeadEvents,
  getSellers,
  getLeadOpportunities,
  Opportunity,
} from '@/lib/api';
import {
  ArrowLeft,
  MessageCircle,
  Calendar,
  TrendingUp,
  StickyNote,
  Phone,
  Mail,
  MapPin,
  Clock,
  User,
  CheckCircle2,
  Loader2,
  Edit2,
  X,
  Plus,
} from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

// =============================================
// TIPOS
// =============================================

interface Lead {
  id: number;
  name: string | null;
  phone: string | null;
  email: string | null;
  city: string | null;
  qualification: string;
  status: string;
  summary: string | null;
  custom_data: Record<string, any>;
  created_at: string;
  assigned_seller?: {
    id: number;
    name: string;
    whatsapp: string;
  } | null;
}

interface Message {
  id: number;
  role: string;
  content: string;
  created_at: string;
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

export default function LeadDetailPageV3() {
  const params = useParams();
  const router = useRouter();

  const [lead, setLead] = useState<Lead | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [events, setEvents] = useState<LeadEvent[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'opportunities' | 'notes'>('overview');
  const [mensagemSucesso, setMensagemSucesso] = useState('');

  useEffect(() => {
    loadData();
  }, [params.id]);

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

  const mostrarSucesso = (mensagem: string) => {
    setMensagemSucesso(mensagem);
    setTimeout(() => setMensagemSucesso(''), 3000);
  };

  const atualizarQualificacao = async (novaQualificacao: string) => {
    if (!lead) return;
    try {
      await updateLead(lead.id, { qualification: novaQualificacao });
      setLead({ ...lead, qualification: novaQualificacao });
      mostrarSucesso('Qualificação atualizada');
    } catch {
      alert('Erro ao atualizar qualificação');
    }
  };

  const atualizarStatus = async (novoStatus: string) => {
    if (!lead) return;
    try {
      await updateLead(lead.id, { status: novoStatus });
      setLead({ ...lead, status: novoStatus });
      mostrarSucesso('Status atualizado');
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

  const tabs = [
    { id: 'overview', label: 'Visão Geral', icon: User },
    { id: 'history', label: 'Histórico', icon: MessageCircle },
    { id: 'opportunities', label: 'Oportunidades', icon: TrendingUp },
    { id: 'notes', label: 'Notas', icon: StickyNote },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Toast de Sucesso */}
      {mensagemSucesso && (
        <div className="fixed top-4 right-4 z-50 animate-in fade-in">
          <div className="bg-green-500 rounded-lg px-6 py-3 shadow-lg flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-white" />
            <span className="text-sm font-semibold text-white">{mensagemSucesso}</span>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Esquerda */}
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.back()}
                className="flex items-center gap-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Voltar
              </Button>

              <div>
                <h1 className="text-2xl font-bold text-gray-900">{lead.name || 'Lead sem nome'}</h1>
                <div className="flex items-center gap-2 mt-1">
                  {lead.phone && (
                    <span className="text-sm text-gray-600 flex items-center gap-1">
                      <Phone className="w-3 h-3" />
                      {lead.phone}
                    </span>
                  )}
                  {lead.email && (
                    <span className="text-sm text-gray-600 flex items-center gap-1">
                      <Mail className="w-3 h-3" />
                      {lead.email}
                    </span>
                  )}
                  {lead.city && (
                    <span className="text-sm text-gray-600 flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {lead.city}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Direita - Status e Qualificação */}
            <div className="flex items-center gap-3">
              <select
                value={lead.status}
                onChange={(e) => atualizarStatus(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg font-medium text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="new">Novo</option>
                <option value="in_progress">Em Andamento</option>
                <option value="qualified">Qualificado</option>
                <option value="lost">Perdido</option>
              </select>

              <select
                value={lead.qualification}
                onChange={(e) => atualizarQualificacao(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg font-medium text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="cold">🧊 Frio</option>
                <option value="warm">🌤️ Morno</option>
                <option value="hot">🔥 Quente</option>
              </select>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-1 mt-6 border-b border-gray-200">
            {tabs.map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`
                    flex items-center gap-2 px-4 py-3 font-medium text-sm transition-all
                    ${isActive
                      ? 'text-blue-600 border-b-2 border-blue-600'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                  {tab.id === 'history' && messages.length > 0 && (
                    <Badge className="bg-blue-100 text-blue-700 text-xs">{messages.length}</Badge>
                  )}
                  {tab.id === 'opportunities' && opportunities.length > 0 && (
                    <Badge className="bg-green-100 text-green-700 text-xs">{opportunities.length}</Badge>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Conteúdo */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {activeTab === 'overview' && <OverviewTab lead={lead} />}
        {activeTab === 'history' && <HistoryTab messages={messages} events={events} />}
        {activeTab === 'opportunities' && <OpportunitiesTab opportunities={opportunities} leadId={lead.id} onReload={loadData} />}
        {activeTab === 'notes' && <NotesTab lead={lead} onUpdate={setLead} />}
      </div>
    </div>
  );
}

// =============================================
// TABS COMPONENTS
// =============================================

function OverviewTab({ lead }: { lead: Lead }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Informações Principais */}
      <Card className="lg:col-span-2 p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Informações do Lead</h3>
        <div className="space-y-4">
          {lead.summary && (
            <div>
              <label className="text-sm font-medium text-gray-700">Resumo</label>
              <p className="text-gray-900 mt-1">{lead.summary}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Status</label>
              <p className="text-gray-900 mt-1 capitalize">{lead.status.replace('_', ' ')}</p>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">Qualificação</label>
              <p className="text-gray-900 mt-1 capitalize">{lead.qualification}</p>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">Criado em</label>
              <p className="text-gray-900 mt-1">
                {format(new Date(lead.created_at), "dd 'de' MMMM, yyyy", { locale: ptBR })}
              </p>
            </div>

            {lead.assigned_seller && (
              <div>
                <label className="text-sm font-medium text-gray-700">Vendedor</label>
                <p className="text-gray-900 mt-1">{lead.assigned_seller.name}</p>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Tags */}
      <Card className="p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Tags</h3>
        <div className="flex flex-wrap gap-2">
          {(lead.custom_data?.tags || []).map((tag: string) => (
            <Badge key={tag} className="bg-blue-100 text-blue-700">
              {tag}
            </Badge>
          ))}
          {(!lead.custom_data?.tags || lead.custom_data.tags.length === 0) && (
            <p className="text-sm text-gray-500">Nenhuma tag adicionada</p>
          )}
        </div>
      </Card>
    </div>
  );
}

function HistoryTab({ messages, events }: { messages: Message[]; events: LeadEvent[] }) {
  // Combinar mensagens e eventos em uma timeline
  const timeline = [
    ...messages.map(m => ({ type: 'message', data: m, date: new Date(m.created_at) })),
    ...events.map(e => ({ type: 'event', data: e, date: new Date(e.created_at) })),
  ].sort((a, b) => a.date.getTime() - b.date.getTime());

  return (
    <Card className="p-6">
      <h3 className="text-lg font-bold text-gray-900 mb-6">Histórico Completo</h3>

      {timeline.length === 0 ? (
        <div className="text-center py-12">
          <MessageCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Nenhuma interação registrada</p>
        </div>
      ) : (
        <div className="space-y-4">
          {timeline.map((item, idx) => (
            <div key={idx} className="flex gap-4">
              <div className="flex-shrink-0">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  item.type === 'message'
                    ? ((item.data as Message).role === 'user' ? 'bg-green-100' : 'bg-blue-100')
                    : 'bg-gray-100'
                }`}>
                  {item.type === 'message' ? (
                    <MessageCircle className={`w-5 h-5 ${
                      (item.data as Message).role === 'user' ? 'text-green-600' : 'text-blue-600'
                    }`} />
                  ) : (
                    <Clock className="w-5 h-5 text-gray-600" />
                  )}
                </div>
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-gray-900">
                    {item.type === 'message'
                      ? ((item.data as Message).role === 'user' ? 'Lead' : 'Assistente')
                      : 'Sistema'
                    }
                  </span>
                  <span className="text-xs text-gray-500">
                    {format(item.date, "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
                  </span>
                </div>

                {item.type === 'message' ? (
                  <p className="text-gray-700 whitespace-pre-wrap">{(item.data as Message).content}</p>
                ) : (
                  <p className="text-gray-600 text-sm">{(item.data as LeadEvent).description}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function OpportunitiesTab({ opportunities, leadId, onReload }: { opportunities: Opportunity[]; leadId: number; onReload: () => void }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-gray-900">Oportunidades Abertas</h3>
        <Button className="flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Nova Oportunidade
        </Button>
      </div>

      {opportunities.length === 0 ? (
        <Card className="p-12 text-center">
          <TrendingUp className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Nenhuma oportunidade criada</p>
        </Card>
      ) : (
        <div className="grid gap-4">
          {opportunities.map(opp => (
            <Card key={opp.id} className="p-6">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-bold text-gray-900">{opp.title}</h4>
                  {opp.description && (
                    <p className="text-sm text-gray-600 mt-1">{opp.description}</p>
                  )}
                  <div className="flex items-center gap-4 mt-3">
                    <Badge className="bg-green-100 text-green-700">
                      R$ {opp.value?.toLocaleString('pt-BR')}
                    </Badge>
                    <span className="text-sm text-gray-500">{opp.stage}</span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function NotesTab({ lead, onUpdate }: { lead: Lead; onUpdate: (lead: Lead) => void }) {
  const [novaNotaContent, setNovaNotaContent] = useState('');
  const [adicionando, setAdicionando] = useState(false);

  const notas = lead.custom_data?.notas || [];

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold text-gray-900">Anotações Internas</h3>

      {/* Form para adicionar nota */}
      <Card className="p-4">
        <textarea
          value={novaNotaContent}
          onChange={(e) => setNovaNotaContent(e.target.value)}
          placeholder="Adicione uma nota sobre este lead..."
          className="w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-h-[100px]"
        />
        <div className="flex justify-end mt-3">
          <Button
            onClick={() => {
              if (novaNotaContent.trim()) {
                // TODO: Salvar nota
                setNovaNotaContent('');
              }
            }}
            disabled={!novaNotaContent.trim() || adicionando}
          >
            {adicionando ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                Salvando...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4 mr-2" />
                Adicionar Nota
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* Lista de notas */}
      {notas.length === 0 ? (
        <Card className="p-12 text-center">
          <StickyNote className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Nenhuma nota adicionada</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {notas.map((nota: any) => (
            <Card key={nota.id} className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="text-gray-900">{nota.content}</p>
                  <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                    <span>{nota.created_by}</span>
                    <span>•</span>
                    <span>{format(new Date(nota.created_at), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}</span>
                  </div>
                </div>
                <button className="text-gray-400 hover:text-red-600">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
