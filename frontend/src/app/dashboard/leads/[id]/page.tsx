'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  getLead,
  getLeadMessages,
  updateLead,
  getLeadEvents,
  assignSellerToLead,
  unassignSellerFromLead,
  updateLeadCustomData,
  getSellers
} from '@/lib/api';
import {
  ArrowLeft,
  Phone,
  Mail,
  MapPin,
  ChevronDown,
  Bot,
  User,
  Clock,
  MessageSquare,
  Sparkles,
  Edit2,
  X,
  Trash2,
  UserPlus,
  History,
  CheckCircle2,
  Loader2,
  Zap,
  TrendingUp,
  UserCheck,
  Tag as TagIcon,
  FileText,
  Info
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

interface Seller {
  id: number;
  name: string;
  whatsapp: string;
  available: boolean;
  active: boolean;
}

interface Note {
  id: number;
  content: string;
  created_by: string;
  created_at: string;
}

function groupMessagesByDate(messages: Message[]): Map<string, Message[]> {
  const groups = new Map<string, Message[]>();
  messages.forEach(msg => {
    const date = new Date(msg.created_at).toLocaleDateString('pt-BR', {
      day: '2-digit', month: 'long', year: 'numeric'
    });
    if (!groups.has(date)) groups.set(date, []);
    groups.get(date)!.push(msg);
  });
  return groups;
}

function isToday(dateString: string): boolean {
  return new Date(dateString).toDateString() === new Date().toDateString();
}

function isYesterday(dateString: string): boolean {
  const date = new Date(dateString);
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return date.toDateString() === yesterday.toDateString();
}

function formatDateLabel(dateString: string, originalDate: string): string {
  if (isToday(originalDate)) return 'Hoje';
  if (isYesterday(originalDate)) return 'Ontem';
  return dateString;
}

function getEventIcon(eventType: string) {
  const iconClass = "w-3 h-3";
  switch (eventType) {
    case 'status_change': return <TrendingUp className={`${iconClass} text-blue-600`} />;
    case 'qualification_change': return <Zap className={`${iconClass} text-purple-600`} />;
    case 'seller_assigned': return <UserPlus className={`${iconClass} text-green-600`} />;
    case 'seller_unassigned': return <X className={`${iconClass} text-red-600`} />;
    default: return <Clock className={`${iconClass} text-slate-400`} />;
  }
}

function getQualificationBadge(qual: string) {
  switch (qual?.toLowerCase()) {
    case 'hot':
    case 'quente':
      return { bg: 'bg-rose-500', text: 'text-white', icon: '🔥', label: 'Quente' };
    case 'warm':
    case 'morno':
      return { bg: 'bg-amber-500', text: 'text-white', icon: '⚡', label: 'Morno' };
    case 'cold':
    case 'frio':
      return { bg: 'bg-blue-500', text: 'text-white', icon: '❄️', label: 'Frio' };
    default:
      return { bg: 'bg-slate-500', text: 'text-white', icon: '•', label: 'Indefinido' };
  }
}

function getStatusBadge(status: string) {
  switch (status?.toLowerCase()) {
    case 'new':
      return { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Novo' };
    case 'in_progress':
      return { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Atendimento' };
    case 'qualified':
      return { bg: 'bg-green-100', text: 'text-green-700', label: 'Qualificado' };
    case 'lost':
      return { bg: 'bg-slate-100', text: 'text-slate-700', label: 'Perdido' };
    default:
      return { bg: 'bg-slate-100', text: 'text-slate-700', label: status };
  }
}

export default function LeadDetailPage() {
  const params = useParams();
  const router = useRouter();

  const [lead, setLead] = useState<Lead | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [events, setEvents] = useState<LeadEvent[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'messages' | 'info' | 'notes'>('messages');

  const [showScrollButton, setShowScrollButton] = useState(false);
  const [editandoNome, setEditandoNome] = useState(false);
  const [nomeTemp, setNomeTemp] = useState('');
  const [editandoNota, setEditandoNota] = useState(false);
  const [novaNota, setNovaNota] = useState('');
  const [adicionandoTag, setAdicionandoTag] = useState(false);
  const [novaTag, setNovaTag] = useState('');
  const [mensagemSucesso, setMensagemSucesso] = useState('');
  const [atribuindoVendedor, setAtribuindoVendedor] = useState(false);

  const chatContainerRef = useRef<HTMLDivElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [leadData, messagesData, eventsData, sellersData] = await Promise.all([
          getLead(Number(params.id)),
          getLeadMessages(Number(params.id)),
          getLeadEvents(Number(params.id)).catch(() => []),
          getSellers().catch(() => ({ sellers: [] })),
        ]);

        setLead(leadData as Lead);
        setMessages(messagesData as Message[]);
        setEvents(eventsData as LeadEvent[]);
        setSellers((sellersData as { sellers: Seller[] }).sellers || []);
      } catch (error) {
        console.error('Erro ao carregar lead:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [params.id]);

  useEffect(() => {
    if (!loading && chatEndRef.current && activeTab === 'messages') {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [loading, messages, activeTab]);

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

  const mostrarSucesso = (mensagem: string) => {
    setMensagemSucesso(mensagem);
    setTimeout(() => setMensagemSucesso(''), 3000);
  };

  const atualizarQualificacao = async (novaQualificacao: string) => {
    if (!lead) return;
    try {
      await updateLead(lead.id, { qualification: novaQualificacao });
      setLead({ ...lead, qualification: novaQualificacao });
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
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
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
      mostrarSucesso('Status atualizado');
    } catch {
      alert('Erro ao atualizar status');
    }
  };

  const salvarNome = async () => {
    if (!lead || !nomeTemp.trim()) {
      setEditandoNome(false);
      return;
    }
    try {
      await updateLead(lead.id, { name: nomeTemp.trim() });
      setLead({ ...lead, name: nomeTemp.trim() });
      setEditandoNome(false);
      mostrarSucesso('Nome atualizado');
    } catch {
      alert('Erro ao salvar nome');
    }
  };

  const salvarNota = async () => {
    if (!lead || !novaNota.trim()) return;
    try {
      const notasAtuais: Note[] = lead.custom_data?.notas || [];
      const novaNot: Note = {
        id: Date.now(),
        content: novaNota.trim(),
        created_by: 'Usuário',
        created_at: new Date().toISOString(),
      };
      const customDataAtualizado = { ...lead.custom_data, notas: [...notasAtuais, novaNot] };
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
      setNovaNota('');
      setEditandoNota(false);
      mostrarSucesso('Nota adicionada');
    } catch {
      alert('Erro ao salvar nota');
    }
  };

  const deletarNota = async (notaId: number) => {
    if (!lead || !confirm('Excluir nota?')) return;
    try {
      const notasAtuais: Note[] = lead.custom_data?.notas || [];
      const notasFiltradas = notasAtuais.filter((n: Note) => n.id !== notaId);
      const customDataAtualizado = { ...lead.custom_data, notas: notasFiltradas };
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
      mostrarSucesso('Nota excluída');
    } catch {
      alert('Erro ao deletar nota');
    }
  };

  const adicionarTag = async () => {
    if (!lead || !novaTag.trim()) {
      setAdicionandoTag(false);
      return;
    }
    try {
      const tagsAtuais: string[] = lead.custom_data?.tags || [];
      const tagFormatada = novaTag.trim().toLowerCase();
      if (tagsAtuais.includes(tagFormatada)) {
        alert('Tag já existe!');
        return;
      }
      const customDataAtualizado = { ...lead.custom_data, tags: [...tagsAtuais, tagFormatada] };
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
      setNovaTag('');
      setAdicionandoTag(false);
      mostrarSucesso('Tag adicionada');
    } catch {
      alert('Erro ao adicionar tag');
    }
  };

  const removerTag = async (tag: string) => {
    if (!lead) return;
    try {
      const tagsAtuais: string[] = lead.custom_data?.tags || [];
      const tagsFiltradas = tagsAtuais.filter((t: string) => t !== tag);
      const customDataAtualizado = { ...lead.custom_data, tags: tagsFiltradas };
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
      mostrarSucesso('Tag removida');
    } catch {
      alert('Erro ao remover tag');
    }
  };

  const atribuirVendedor = async (sellerId: number) => {
    if (!lead || !sellerId) return;
    try {
      setAtribuindoVendedor(true);
      await assignSellerToLead(lead.id, sellerId);
      const leadAtualizado = await getLead(lead.id);
      setLead(leadAtualizado as Lead);
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
      mostrarSucesso('Vendedor atribuído');
    } catch {
      alert('Erro ao atribuir vendedor');
    } finally {
      setAtribuindoVendedor(false);
    }
  };

  const removerAtribuicao = async () => {
    if (!lead || !confirm('Remover atribuição?')) return;
    try {
      await unassignSellerFromLead(lead.id);
      setLead({ ...lead, assigned_seller: null });
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
      mostrarSucesso('Atribuição removida');
    } catch {
      alert('Erro ao remover atribuição');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
          <span className="text-slate-600 font-semibold text-sm">Carregando...</span>
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4 bg-slate-50">
        <h3 className="text-xl font-bold text-slate-900">Lead não encontrado</h3>
        <button
          onClick={() => router.back()}
          className="px-6 py-2 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors"
        >
          Voltar
        </button>
      </div>
    );
  }

  const messageGroups = groupMessagesByDate(messages);
  const qualBadge = getQualificationBadge(lead.qualification);
  const statusBadge = getStatusBadge(lead.status);

  return (
    <div className="h-screen flex flex-col bg-slate-50 overflow-hidden">
      {/* Toast */}
      {mensagemSucesso && (
        <div className="fixed top-4 right-4 z-50 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="bg-white rounded-xl px-5 py-3 shadow-xl border border-slate-200 flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-green-500" />
            <span className="text-sm font-medium text-slate-900">{mensagemSucesso}</span>
          </div>
        </div>
      )}

      {/* Header Compacto */}
      <div className="bg-white border-b border-slate-200 flex-shrink-0">
        <div className="px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 min-w-0 flex-1">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-slate-600" />
            </button>

            <div className="min-w-0 flex-1">
              {editandoNome ? (
                <input
                  type="text"
                  value={nomeTemp}
                  onChange={(e) => setNomeTemp(e.target.value)}
                  onBlur={salvarNome}
                  onKeyDown={(e) => e.key === 'Enter' && salvarNome()}
                  className="text-lg font-bold text-slate-900 w-full border-b-2 border-blue-600 outline-none bg-transparent"
                  autoFocus
                />
              ) : (
                <div className="flex items-center gap-2 group cursor-pointer" onClick={() => { setNomeTemp(lead.name || ''); setEditandoNome(true); }}>
                  <h1 className="text-lg font-bold text-slate-900 truncate">{lead.name || 'Lead sem nome'}</h1>
                  <Edit2 className="w-3.5 h-3.5 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              )}

              {/* Tags inline */}
              <div className="flex flex-wrap gap-1.5 mt-1">
                {(lead.custom_data?.tags || []).map((tag: string) => (
                  <Badge key={tag} className="flex items-center gap-1 bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 text-xs font-medium rounded-md">
                    {tag}
                    <button onClick={() => removerTag(tag)} className="hover:text-red-600">
                      <X className="w-3 h-3" />
                    </button>
                  </Badge>
                ))}
                {adicionandoTag ? (
                  <input
                    type="text"
                    value={novaTag}
                    onChange={(e) => setNovaTag(e.target.value)}
                    onBlur={adicionarTag}
                    onKeyDown={(e) => e.key === 'Enter' && adicionarTag()}
                    placeholder="Tag..."
                    className="border border-blue-400 rounded-md px-2 py-0.5 text-xs w-20 outline-none"
                    autoFocus
                  />
                ) : (
                  <button onClick={() => setAdicionandoTag(true)} className="text-xs font-semibold text-blue-600 hover:text-blue-700 px-2 py-0.5 bg-blue-50 rounded-md">
                    + Tag
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Status badges compactos */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <select
                value={lead.status}
                onChange={(e) => atualizarStatus(e.target.value)}
                className={`${statusBadge.bg} ${statusBadge.text} px-3 py-1.5 rounded-lg font-semibold text-xs cursor-pointer border-0 appearance-none pr-7`}
              >
                <option value="new">Novo</option>
                <option value="in_progress">Atendimento</option>
                <option value="qualified">Qualificado</option>
                <option value="lost">Perdido</option>
              </select>
              <ChevronDown className="w-3 h-3 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>

            <div className="relative">
              <select
                value={lead.qualification}
                onChange={(e) => atualizarQualificacao(e.target.value)}
                className={`${qualBadge.bg} ${qualBadge.text} px-3 py-1.5 rounded-lg font-semibold text-xs cursor-pointer border-0 appearance-none pr-7`}
              >
                <option value="cold">❄️ Frio</option>
                <option value="warm">⚡ Morno</option>
                <option value="hot">🔥 Quente</option>
              </select>
              <ChevronDown className="w-3 h-3 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-white" />
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="px-6 flex gap-1 border-t border-slate-100">
          <button
            onClick={() => setActiveTab('messages')}
            className={`px-4 py-2.5 text-sm font-semibold transition-colors relative ${
              activeTab === 'messages'
                ? 'text-blue-600'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <MessageSquare className="w-4 h-4 inline mr-1.5" />
            Mensagens
            {activeTab === 'messages' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600" />}
          </button>
          <button
            onClick={() => setActiveTab('info')}
            className={`px-4 py-2.5 text-sm font-semibold transition-colors relative ${
              activeTab === 'info'
                ? 'text-blue-600'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Info className="w-4 h-4 inline mr-1.5" />
            Informações
            {activeTab === 'info' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600" />}
          </button>
          <button
            onClick={() => setActiveTab('notes')}
            className={`px-4 py-2.5 text-sm font-semibold transition-colors relative ${
              activeTab === 'notes'
                ? 'text-blue-600'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="w-4 h-4 inline mr-1.5" />
            Notas
            {activeTab === 'notes' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600" />}
          </button>
        </div>
      </div>

      {/* Conteúdo das Tabs */}
      <div className="flex-1 overflow-hidden">
        {/* Tab: Mensagens */}
        {activeTab === 'messages' && (
          <div
            ref={chatContainerRef}
            onScroll={handleScroll}
            className="h-full overflow-y-auto p-6 space-y-4 bg-slate-50"
          >
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-400">
                <MessageSquare className="w-12 h-12 mb-3 opacity-20" />
                <p className="text-sm font-semibold text-slate-500">Nenhuma mensagem</p>
              </div>
            ) : (
              <>
                {Array.from(messageGroups.entries()).map(([date, dateMessages]) => (
                  <div key={date}>
                    <div className="flex items-center justify-center my-6">
                      <span className="px-3 py-1 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-full">
                        {formatDateLabel(date, dateMessages[0].created_at)}
                      </span>
                    </div>

                    <div className="space-y-3">
                      {dateMessages.map((msg, idx) => {
                        const isAssistant = msg.role === 'assistant';
                        const showAvatar = idx === 0 || dateMessages[idx - 1]?.role !== msg.role;

                        return (
                          <div key={msg.id} className={`flex ${isAssistant ? 'justify-start' : 'justify-end'}`}>
                            {isAssistant && (
                              <div className={`flex-shrink-0 mr-2 ${showAvatar ? 'visible' : 'invisible'}`}>
                                <div className="w-8 h-8 bg-slate-900 rounded-lg flex items-center justify-center">
                                  <Bot className="w-4 h-4 text-white" />
                                </div>
                              </div>
                            )}

                            <div className={`
                              max-w-[70%] px-4 py-2.5 rounded-2xl text-sm
                              ${isAssistant
                                ? 'bg-white text-slate-700 border border-slate-200 rounded-tl-sm'
                                : 'bg-blue-600 text-white rounded-tr-sm'
                              }
                            `}>
                              <p className="leading-relaxed">{msg.content}</p>
                              <div className={`flex items-center gap-1 mt-1.5 text-xs ${isAssistant ? 'text-slate-400' : 'text-blue-100'}`}>
                                <Clock className="w-3 h-3" />
                                <span>{new Date(msg.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>
                              </div>
                            </div>

                            {!isAssistant && (
                              <div className={`flex-shrink-0 ml-2 ${showAvatar ? 'visible' : 'invisible'}`}>
                                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center border border-blue-200">
                                  <User className="w-4 h-4 text-blue-600" />
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
            <div ref={chatEndRef} />

            {showScrollButton && (
              <button
                onClick={scrollToBottom}
                className="fixed bottom-6 right-6 p-3 bg-white border border-slate-300 rounded-full shadow-xl text-blue-600 hover:bg-blue-50 transition-all"
              >
                <ChevronDown className="w-5 h-5" />
              </button>
            )}
          </div>
        )}

        {/* Tab: Informações */}
        {activeTab === 'info' && (
          <div className="h-full overflow-y-auto p-6 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Contato */}
              <Card className="bg-white border-slate-200 p-4">
                <h3 className="text-xs font-bold text-slate-900 mb-3 uppercase tracking-wider">Contato</h3>
                <div className="space-y-2">
                  {lead.phone && (
                    <div className="flex items-center gap-3">
                      <Phone className="w-4 h-4 text-slate-400" />
                      <span className="text-sm text-slate-900">{lead.phone}</span>
                    </div>
                  )}
                  {lead.email && (
                    <div className="flex items-center gap-3">
                      <Mail className="w-4 h-4 text-slate-400" />
                      <span className="text-sm text-slate-900 truncate">{lead.email}</span>
                    </div>
                  )}
                  {lead.city && (
                    <div className="flex items-center gap-3">
                      <MapPin className="w-4 h-4 text-slate-400" />
                      <span className="text-sm text-slate-900">{lead.city}</span>
                    </div>
                  )}
                </div>
              </Card>

              {/* Vendedor */}
              <Card className="bg-white border-slate-200 p-4">
                <h3 className="text-xs font-bold text-slate-900 mb-3 uppercase tracking-wider flex items-center gap-2">
                  <UserCheck className="w-3.5 h-3.5 text-green-600" />
                  Vendedor
                </h3>
                {lead.assigned_seller ? (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 bg-green-600 rounded-lg flex items-center justify-center text-white font-bold text-xs">
                        {lead.assigned_seller.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-semibold text-sm text-slate-900">{lead.assigned_seller.name}</p>
                        <p className="text-xs text-green-700">{lead.assigned_seller.whatsapp}</p>
                      </div>
                    </div>
                    <button onClick={removerAtribuicao} className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <select
                    onChange={(e) => atribuirVendedor(parseInt(e.target.value))}
                    disabled={atribuindoVendedor}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 outline-none"
                  >
                    <option value="">Selecionar...</option>
                    {sellers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                )}
              </Card>

              {/* Resumo IA */}
              {lead.summary && (
                <Card className="bg-gradient-to-br from-violet-50 to-purple-50 border-violet-200 p-4 md:col-span-2">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-violet-600" />
                    <h3 className="text-xs font-bold text-violet-900 uppercase tracking-wider">Resumo IA</h3>
                  </div>
                  <p className="text-violet-900 text-sm leading-relaxed italic">&quot;{lead.summary}&quot;</p>
                </Card>
              )}

              {/* Timeline */}
              {events.length > 0 && (
                <Card className="bg-white border-slate-200 p-4 md:col-span-2">
                  <h3 className="text-xs font-bold text-slate-900 mb-3 uppercase tracking-wider flex items-center gap-2">
                    <History className="w-3.5 h-3.5 text-slate-600" />
                    Atividades Recentes
                  </h3>
                  <div className="space-y-2">
                    {events.slice(0, 4).map((event) => (
                      <div key={event.id} className="flex items-start gap-3 text-sm">
                        <div className="mt-1">{getEventIcon(event.event_type)}</div>
                        <div className="flex-1 min-w-0">
                          <p className="text-slate-900 font-medium">{event.description}</p>
                          <p className="text-xs text-slate-500">
                            {new Date(event.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          </div>
        )}

        {/* Tab: Notas */}
        {activeTab === 'notes' && (
          <div className="h-full overflow-y-auto p-6">
            <div className="max-w-3xl mx-auto space-y-4">
              {editandoNota && (
                <Card className="bg-white border-slate-200 p-4">
                  <textarea
                    value={novaNota}
                    onChange={(e) => setNovaNota(e.target.value)}
                    placeholder="Digite sua nota..."
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm outline-none resize-none"
                    rows={4}
                  />
                  <div className="flex gap-2 mt-3">
                    <button onClick={salvarNota} className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700">
                      Salvar
                    </button>
                    <button onClick={() => { setEditandoNota(false); setNovaNota(''); }} className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-lg">
                      Cancelar
                    </button>
                  </div>
                </Card>
              )}

              {!editandoNota && (
                <button
                  onClick={() => setEditandoNota(true)}
                  className="w-full py-3 border-2 border-dashed border-slate-300 rounded-lg text-sm font-semibold text-slate-600 hover:border-blue-400 hover:text-blue-600 transition-colors"
                >
                  + Adicionar Nota
                </button>
              )}

              {(lead.custom_data?.notas || []).length === 0 && !editandoNota && (
                <p className="text-sm text-slate-400 text-center py-8">Nenhuma nota criada</p>
              )}

              {(lead.custom_data?.notas || []).map((nota: Note) => (
                <Card key={nota.id} className="bg-white border-slate-200 p-4 group hover:border-slate-300">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs text-slate-500 font-medium">{nota.created_by}</span>
                    <button onClick={() => deletarNota(nota.id)} className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-600">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed">{nota.content}</p>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
