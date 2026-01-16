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
  Building2,
  FileText
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
      return { bg: 'bg-red-600', text: 'text-white', label: 'Quente' };
    case 'warm':
    case 'morno':
      return { bg: 'bg-orange-600', text: 'text-white', label: 'Morno' };
    case 'cold':
    case 'frio':
      return { bg: 'bg-blue-600', text: 'text-white', label: 'Frio' };
    default:
      return { bg: 'bg-gray-600', text: 'text-white', label: 'Indefinido' };
  }
}

function getStatusBadge(status: string) {
  switch (status?.toLowerCase()) {
    case 'new':
      return { bg: 'bg-blue-600', text: 'text-white', label: 'Novo' };
    case 'in_progress':
      return { bg: 'bg-yellow-600', text: 'text-white', label: 'Em Andamento' };
    case 'qualified':
      return { bg: 'bg-green-600', text: 'text-white', label: 'Qualificado' };
    case 'lost':
      return { bg: 'bg-gray-600', text: 'text-white', label: 'Perdido' };
    default:
      return { bg: 'bg-gray-600', text: 'text-white', label: status };
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
    if (!loading && chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [loading, messages]);

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
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
          <span className="text-gray-600 font-medium">Carregando...</span>
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4 bg-gray-50">
        <h3 className="text-xl font-semibold text-gray-900">Lead não encontrado</h3>
        <button
          onClick={() => router.back()}
          className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
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
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Toast */}
      {mensagemSucesso && (
        <div className="fixed top-4 right-4 z-50 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="bg-white rounded-lg px-5 py-3 shadow-lg border border-gray-200 flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-green-600" />
            <span className="text-sm font-medium text-gray-900">{mensagemSucesso}</span>
          </div>
        </div>
      )}

      {/* Header Corporativo */}
      <div className="bg-white border-b border-gray-200 flex-shrink-0">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            {/* Esquerda - Voltar + Nome + Tags */}
            <div className="flex items-center gap-4 min-w-0 flex-1">
              <button
                onClick={() => router.back()}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
              >
                <ArrowLeft className="w-5 h-5 text-gray-600" />
              </button>

              <div className="min-w-0 flex-1">
                {editandoNome ? (
                  <input
                    type="text"
                    value={nomeTemp}
                    onChange={(e) => setNomeTemp(e.target.value)}
                    onBlur={salvarNome}
                    onKeyDown={(e) => e.key === 'Enter' && salvarNome()}
                    className="text-xl font-semibold text-gray-900 w-full border-b-2 border-blue-600 outline-none bg-transparent"
                    autoFocus
                  />
                ) : (
                  <div className="flex items-center gap-2 group cursor-pointer" onClick={() => { setNomeTemp(lead.name || ''); setEditandoNome(true); }}>
                    <h1 className="text-xl font-semibold text-gray-900 truncate">{lead.name || 'Lead sem nome'}</h1>
                    <Edit2 className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                  </div>
                )}

                <div className="flex flex-wrap gap-2 mt-2">
                  {(lead.custom_data?.tags || []).map((tag: string) => (
                    <Badge key={tag} className="bg-gray-100 text-gray-700 border border-gray-300 px-2 py-0.5 text-xs font-medium rounded hover:bg-gray-200 transition-colors">
                      {tag}
                      <button onClick={(e) => { e.stopPropagation(); removerTag(tag); }} className="ml-1.5 hover:text-red-600">
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
                      placeholder="Nova tag"
                      className="border border-gray-300 rounded px-2 py-0.5 text-xs w-24 outline-none focus:border-blue-500"
                      autoFocus
                    />
                  ) : (
                    <button onClick={() => setAdicionandoTag(true)} className="text-xs font-medium text-gray-600 hover:text-gray-900 px-2 py-0.5 border border-dashed border-gray-300 rounded hover:border-gray-400 transition-colors">
                      + Adicionar tag
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Direita - Status e Qualificação */}
            <div className="flex items-center gap-3 flex-shrink-0">
              <div className="relative">
                <select
                  value={lead.status}
                  onChange={(e) => atualizarStatus(e.target.value)}
                  className={`${statusBadge.bg} ${statusBadge.text} px-4 py-2 rounded-lg font-medium text-sm cursor-pointer border-0 appearance-none pr-9 shadow-sm`}
                >
                  <option value="new">Novo</option>
                  <option value="in_progress">Em Andamento</option>
                  <option value="qualified">Qualificado</option>
                  <option value="lost">Perdido</option>
                </select>
                <ChevronDown className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-white" />
              </div>

              <div className="relative">
                <select
                  value={lead.qualification}
                  onChange={(e) => atualizarQualificacao(e.target.value)}
                  className={`${qualBadge.bg} ${qualBadge.text} px-4 py-2 rounded-lg font-medium text-sm cursor-pointer border-0 appearance-none pr-9 shadow-sm`}
                >
                  <option value="cold">Frio</option>
                  <option value="warm">Morno</option>
                  <option value="hot">Quente</option>
                </select>
                <ChevronDown className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-white" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Conteúdo Principal - Layout em Grid */}
      <div className="flex-1 grid grid-cols-12 gap-0 overflow-hidden">
        {/* Sidebar - 4 colunas */}
        <div className="col-span-4 bg-white border-r border-gray-200 overflow-y-auto">
          <div className="p-6 space-y-6">
            {/* Informações de Contato */}
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                Informações de Contato
              </h3>
              <div className="space-y-3">
                {lead.phone && (
                  <div className="flex items-center gap-3 text-sm">
                    <Phone className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <span className="text-gray-900 font-medium">{lead.phone}</span>
                  </div>
                )}
                {lead.email && (
                  <div className="flex items-center gap-3 text-sm">
                    <Mail className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <span className="text-gray-900 font-medium truncate">{lead.email}</span>
                  </div>
                )}
                {lead.city && (
                  <div className="flex items-center gap-3 text-sm">
                    <MapPin className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <span className="text-gray-900 font-medium">{lead.city}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="border-t border-gray-200 pt-6">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                <UserCheck className="w-4 h-4" />
                Vendedor Responsável
              </h3>
              {lead.assigned_seller ? (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center text-white font-semibold">
                        {lead.assigned_seller.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900 text-sm">{lead.assigned_seller.name}</p>
                        <p className="text-xs text-green-700">{lead.assigned_seller.whatsapp}</p>
                      </div>
                    </div>
                    <button onClick={removerAtribuicao} className="p-1.5 text-red-600 hover:bg-red-50 rounded">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ) : (
                <select
                  onChange={(e) => atribuirVendedor(parseInt(e.target.value))}
                  disabled={atribuindoVendedor}
                  className="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-700 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">Selecionar vendedor</option>
                  {sellers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              )}
            </div>

            {lead.summary && (
              <div className="border-t border-gray-200 pt-6">
                <div className="bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-indigo-600" />
                    <h3 className="text-xs font-semibold text-indigo-900 uppercase tracking-wider">Resumo IA</h3>
                  </div>
                  <p className="text-sm text-indigo-900 leading-relaxed">&quot;{lead.summary}&quot;</p>
                </div>
              </div>
            )}

            {events.length > 0 && (
              <div className="border-t border-gray-200 pt-6">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <History className="w-4 h-4" />
                  Histórico
                </h3>
                <div className="space-y-3">
                  {events.slice(0, 3).map((event) => (
                    <div key={event.id} className="flex items-start gap-2 text-sm">
                      <div className="mt-0.5">{getEventIcon(event.event_type)}</div>
                      <div>
                        <p className="text-gray-900 font-medium text-xs">{event.description}</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {new Date(event.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="border-t border-gray-200 pt-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Notas
                </h3>
                {!editandoNota && (
                  <button onClick={() => setEditandoNota(true)} className="text-xs font-medium text-blue-600 hover:text-blue-700">
                    + Adicionar
                  </button>
                )}
              </div>

              {editandoNota && (
                <div className="mb-3 space-y-2">
                  <textarea
                    value={novaNota}
                    onChange={(e) => setNovaNota(e.target.value)}
                    placeholder="Digite sua nota..."
                    className="w-full bg-white border border-gray-300 rounded-lg p-3 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
                    rows={3}
                  />
                  <div className="flex gap-2">
                    <button onClick={salvarNota} className="flex-1 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700">
                      Salvar
                    </button>
                    <button onClick={() => { setEditandoNota(false); setNovaNota(''); }} className="px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-lg">
                      Cancelar
                    </button>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                {(lead.custom_data?.notas || []).length === 0 && !editandoNota && (
                  <p className="text-xs text-gray-400 text-center py-4">Nenhuma nota</p>
                )}
                {(lead.custom_data?.notas || []).map((nota: Note) => (
                  <div key={nota.id} className="group bg-gray-50 border border-gray-200 rounded-lg p-3 hover:border-gray-300 transition-colors">
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-xs text-gray-500 font-medium">{nota.created_by}</span>
                      <button onClick={() => deletarNota(nota.id)} className="opacity-0 group-hover:opacity-100 text-red-600 hover:text-red-700">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                    <p className="text-xs text-gray-700 leading-relaxed">{nota.content}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Área de Chat - 8 colunas */}
        <div className="col-span-8 flex flex-col bg-white">
          {/* Header do Chat */}
          <div className="px-6 py-4 border-b border-gray-200 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                  <MessageSquare className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Conversas</h3>
                  <p className="text-xs text-gray-500">Sincronizado via WhatsApp</p>
                </div>
              </div>
              <Badge className="bg-gray-100 text-gray-700 px-3 py-1 font-medium text-xs">
                {messages.length} mensagens
              </Badge>
            </div>
          </div>

          {/* Container de Mensagens */}
          <div
            ref={chatContainerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50"
          >
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <MessageSquare className="w-12 h-12 mb-2 opacity-20" />
                <p className="text-sm font-medium">Nenhuma mensagem</p>
              </div>
            ) : (
              <>
                {Array.from(messageGroups.entries()).map(([date, dateMessages]) => (
                  <div key={date}>
                    <div className="flex items-center justify-center my-6">
                      <span className="px-3 py-1 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded-full">
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
                                <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
                                  <Bot className="w-4 h-4 text-white" />
                                </div>
                              </div>
                            )}

                            <div className={`
                              max-w-[70%] px-4 py-2.5 rounded-lg text-sm
                              ${isAssistant
                                ? 'bg-white text-gray-800 border border-gray-200'
                                : 'bg-blue-600 text-white'
                              }
                            `}>
                              <p className="leading-relaxed">{msg.content}</p>
                              <div className={`flex items-center gap-1 mt-1.5 text-xs ${isAssistant ? 'text-gray-500' : 'text-blue-100'}`}>
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
                className="fixed bottom-6 right-6 p-3 bg-white border border-gray-300 rounded-full shadow-lg text-blue-600 hover:bg-gray-50 transition-all"
              >
                <ChevronDown className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
