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
  Calendar,
  Tag as TagIcon,
  FileText,
  Building2,
  Hash
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
  const iconClass = "w-3.5 h-3.5";
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
      mostrarSucesso('Vendedor atribuído com sucesso');
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
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
          <span className="text-slate-600 font-semibold">Carregando informações...</span>
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-6 bg-slate-50">
        <div className="text-center">
          <h3 className="text-2xl font-bold text-slate-900 mb-2">Lead não encontrado</h3>
          <p className="text-slate-500">O lead que você procura não existe ou foi removido.</p>
        </div>
        <button
          onClick={() => router.back()}
          className="px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors shadow-lg shadow-blue-100"
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100/50">
      {/* Toast de Sucesso */}
      {mensagemSucesso && (
        <div className="fixed top-6 right-6 z-50 animate-in fade-in slide-in-from-top-4 duration-300">
          <div className="bg-white rounded-2xl px-6 py-4 shadow-2xl border border-slate-200 flex items-center gap-4 min-w-[300px]">
            <div className="w-10 h-10 bg-green-500 rounded-xl flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-slate-900 font-semibold">Sucesso</p>
              <p className="text-slate-600 text-sm">{mensagemSucesso}</p>
            </div>
          </div>
        </div>
      )}

      {/* Header com breadcrumb e ações */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-[1800px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-6 flex-wrap">
            {/* Lado esquerdo - Breadcrumb */}
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.back()}
                className="p-2 hover:bg-slate-100 rounded-xl transition-all group"
              >
                <ArrowLeft className="w-5 h-5 text-slate-600 group-hover:text-blue-600 transition-colors" />
              </button>

              <div className="flex items-center gap-2 text-sm">
                <span className="text-slate-400">Leads</span>
                <span className="text-slate-300">/</span>
                <span className="text-slate-900 font-semibold">{lead.name || 'Lead'}</span>
              </div>
            </div>

            {/* Lado direito - Badges de status */}
            <div className="flex items-center gap-3">
              <div className="relative group">
                <select
                  value={lead.status}
                  onChange={(e) => atualizarStatus(e.target.value)}
                  className={`${statusBadge.bg} ${statusBadge.text} px-4 py-2 rounded-xl font-semibold text-sm cursor-pointer border-0 appearance-none pr-8 hover:opacity-90 transition-opacity`}
                >
                  <option value="new">Novo</option>
                  <option value="in_progress">Atendimento</option>
                  <option value="qualified">Qualificado</option>
                  <option value="lost">Perdido</option>
                </select>
                <ChevronDown className="w-4 h-4 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              <div className="relative group">
                <select
                  value={lead.qualification}
                  onChange={(e) => atualizarQualificacao(e.target.value)}
                  className={`${qualBadge.bg} ${qualBadge.text} px-4 py-2 rounded-xl font-semibold text-sm cursor-pointer border-0 appearance-none pr-8 hover:opacity-90 transition-opacity`}
                >
                  <option value="cold">{qualBadge.icon} Frio</option>
                  <option value="warm">⚡ Morno</option>
                  <option value="hot">🔥 Quente</option>
                </select>
                <ChevronDown className="w-4 h-4 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-white" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Conteúdo Principal */}
      <div className="max-w-[1800px] mx-auto p-6">
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Sidebar Esquerda - Informações */}
          <div className="xl:col-span-1 space-y-6">
            {/* Card: Nome e Tags */}
            <Card className="bg-white border-slate-200 shadow-sm">
              <div className="p-6">
                {/* Nome editável */}
                <div className="mb-4">
                  {editandoNome ? (
                    <input
                      type="text"
                      value={nomeTemp}
                      onChange={(e) => setNomeTemp(e.target.value)}
                      onBlur={salvarNome}
                      onKeyDown={(e) => e.key === 'Enter' && salvarNome()}
                      className="text-2xl font-bold text-slate-900 w-full border-b-2 border-blue-600 outline-none bg-transparent"
                      autoFocus
                    />
                  ) : (
                    <div className="flex items-center gap-2 group cursor-pointer" onClick={() => { setNomeTemp(lead.name || ''); setEditandoNome(true); }}>
                      <h2 className="text-2xl font-bold text-slate-900">{lead.name || 'Lead sem nome'}</h2>
                      <Edit2 className="w-4 h-4 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  )}
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {(lead.custom_data?.tags || []).map((tag: string) => (
                    <Badge
                      key={tag}
                      className="flex items-center gap-1.5 bg-blue-50 text-blue-700 border border-blue-200 px-3 py-1 font-medium rounded-lg hover:bg-blue-100 transition-colors group"
                    >
                      <TagIcon className="w-3 h-3" />
                      {tag}
                      <button onClick={() => removerTag(tag)} className="hover:text-red-600 transition-colors ml-1">
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
                      placeholder="Nova tag..."
                      className="border border-blue-400 rounded-lg px-2 py-1 text-sm w-32 outline-none"
                      autoFocus
                    />
                  ) : (
                    <button
                      onClick={() => setAdicionandoTag(true)}
                      className="text-sm font-semibold text-blue-600 hover:text-blue-700 px-3 py-1 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                      + Tag
                    </button>
                  )}
                </div>

                {/* Data de criação */}
                <div className="flex items-center gap-2 text-sm text-slate-500 pt-4 border-t border-slate-100">
                  <Calendar className="w-4 h-4" />
                  <span>Criado em {new Date(lead.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' })}</span>
                </div>
              </div>
            </Card>

            {/* Card: Informações de Contato */}
            <Card className="bg-white border-slate-200 shadow-sm">
              <div className="p-6">
                <h3 className="font-bold text-sm text-slate-900 mb-4 flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-blue-600" />
                  Informações de Contato
                </h3>

                <div className="space-y-3">
                  {lead.phone && (
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors group">
                      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center border border-slate-200 group-hover:border-blue-300 transition-colors">
                        <Phone className="w-4 h-4 text-slate-600 group-hover:text-blue-600 transition-colors" />
                      </div>
                      <div>
                        <p className="text-xs text-slate-500 font-medium">Telefone</p>
                        <p className="text-slate-900 font-semibold">{lead.phone}</p>
                      </div>
                    </div>
                  )}

                  {lead.email && (
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors group">
                      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center border border-slate-200 group-hover:border-blue-300 transition-colors">
                        <Mail className="w-4 h-4 text-slate-600 group-hover:text-blue-600 transition-colors" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs text-slate-500 font-medium">E-mail</p>
                        <p className="text-slate-900 font-semibold truncate">{lead.email}</p>
                      </div>
                    </div>
                  )}

                  {lead.city && (
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors group">
                      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center border border-slate-200 group-hover:border-blue-300 transition-colors">
                        <MapPin className="w-4 h-4 text-slate-600 group-hover:text-blue-600 transition-colors" />
                      </div>
                      <div>
                        <p className="text-xs text-slate-500 font-medium">Cidade</p>
                        <p className="text-slate-900 font-semibold">{lead.city}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </Card>

            {/* Card: Resumo da IA */}
            {lead.summary && (
              <Card className="bg-gradient-to-br from-violet-50 to-purple-50 border-violet-200 shadow-sm">
                <div className="p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-8 h-8 bg-violet-600 rounded-lg flex items-center justify-center">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <h3 className="font-bold text-sm text-violet-900">Resumo Inteligente</h3>
                  </div>
                  <p className="text-violet-900 text-sm leading-relaxed italic">&quot;{lead.summary}&quot;</p>
                </div>
              </Card>
            )}

            {/* Card: Atribuição de Vendedor */}
            <Card className="bg-white border-slate-200 shadow-sm">
              <div className="p-6">
                <h3 className="font-bold text-sm text-slate-900 mb-4 flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-green-600" />
                  Vendedor Responsável
                </h3>

                {lead.assigned_seller ? (
                  <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center text-white font-bold">
                          {lead.assigned_seller.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-900">{lead.assigned_seller.name}</p>
                          <p className="text-sm text-green-700">{lead.assigned_seller.whatsapp}</p>
                        </div>
                      </div>
                      <button
                        onClick={removerAtribuicao}
                        className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <select
                      onChange={(e) => atribuirVendedor(parseInt(e.target.value))}
                      disabled={atribuindoVendedor}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-medium text-slate-700 outline-none hover:border-blue-300 transition-colors cursor-pointer disabled:opacity-50"
                    >
                      <option value="">Selecionar vendedor...</option>
                      {sellers.map(s => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>

                    <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
                      <Zap className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-blue-700">Vendedor será notificado via WhatsApp</p>
                    </div>
                  </div>
                )}
              </div>
            </Card>

            {/* Card: Timeline de Eventos */}
            {events.length > 0 && (
              <Card className="bg-white border-slate-200 shadow-sm">
                <div className="p-6">
                  <h3 className="font-bold text-sm text-slate-900 mb-4 flex items-center gap-2">
                    <History className="w-4 h-4 text-slate-600" />
                    Histórico de Atividades
                  </h3>

                  <div className="relative space-y-4 before:absolute before:left-[15px] before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                    {events.slice(0, 5).map((event) => (
                      <div key={event.id} className="relative pl-10 pb-4 last:pb-0">
                        <div className="absolute left-0 top-0 w-8 h-8 bg-white border-2 border-slate-200 rounded-full flex items-center justify-center">
                          {getEventIcon(event.event_type)}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-900">{event.description}</p>
                          <p className="text-xs text-slate-500 mt-1">
                            {new Date(event.created_at).toLocaleDateString('pt-BR', {
                              day: '2-digit',
                              month: 'short',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}

            {/* Card: Notas Internas */}
            <Card className="bg-white border-slate-200 shadow-sm">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-amber-600" />
                    Notas Internas
                  </h3>
                  <button
                    onClick={() => setEditandoNota(true)}
                    className="text-sm font-semibold text-blue-600 hover:text-blue-700"
                  >
                    + Adicionar
                  </button>
                </div>

                {editandoNota && (
                  <div className="mb-4 space-y-3">
                    <textarea
                      value={novaNota}
                      onChange={(e) => setNovaNota(e.target.value)}
                      placeholder="Digite sua nota..."
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm outline-none focus:border-blue-400 resize-none"
                      rows={3}
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={salvarNota}
                        className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"
                      >
                        Salvar
                      </button>
                      <button
                        onClick={() => { setEditandoNota(false); setNovaNota(''); }}
                        className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                )}

                <div className="space-y-3">
                  {(lead.custom_data?.notas || []).length === 0 && !editandoNota && (
                    <p className="text-sm text-slate-400 text-center py-4">Nenhuma nota adicionada</p>
                  )}

                  {(lead.custom_data?.notas || []).map((nota: Note) => (
                    <div
                      key={nota.id}
                      className="group p-3 bg-slate-50 rounded-xl border border-slate-200 hover:border-slate-300 transition-colors"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-xs text-slate-500 font-medium">{nota.created_by}</span>
                        <button
                          onClick={() => deletarNota(nota.id)}
                          className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-600 transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      <p className="text-sm text-slate-700 leading-relaxed">{nota.content}</p>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </div>

          {/* Área Principal - Chat de Mensagens */}
          <div className="xl:col-span-2">
            <Card className="bg-white border-slate-200 shadow-sm h-[calc(100vh-180px)] flex flex-col">
              {/* Header do Chat */}
              <div className="p-6 border-b border-slate-200 flex-shrink-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center">
                      <MessageSquare className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h3 className="font-bold text-lg text-slate-900">Histórico de Mensagens</h3>
                      <p className="text-sm text-slate-500">Sincronizado via WhatsApp</p>
                    </div>
                  </div>
                  <Badge className="bg-slate-100 text-slate-700 px-4 py-2 font-semibold">
                    <Hash className="w-3 h-3 mr-1" />
                    {messages.length} mensagens
                  </Badge>
                </div>
              </div>

              {/* Container de Mensagens */}
              <div
                ref={chatContainerRef}
                onScroll={handleScroll}
                className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/30"
              >
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-slate-400">
                    <MessageSquare className="w-16 h-16 mb-4 opacity-20" />
                    <p className="text-lg font-semibold text-slate-500">Nenhuma mensagem ainda</p>
                    <p className="text-sm text-slate-400">As conversas aparecerão aqui</p>
                  </div>
                ) : (
                  <>
                    {Array.from(messageGroups.entries()).map(([date, dateMessages]) => (
                      <div key={date} className="space-y-4">
                        {/* Separador de data */}
                        <div className="flex items-center justify-center my-8">
                          <div className="flex-1 h-px bg-slate-200" />
                          <span className="px-4 py-2 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-full mx-4">
                            {formatDateLabel(date, dateMessages[0].created_at)}
                          </span>
                          <div className="flex-1 h-px bg-slate-200" />
                        </div>

                        {/* Mensagens do dia */}
                        <div className="space-y-4">
                          {dateMessages.map((msg, idx) => {
                            const isAssistant = msg.role === 'assistant';
                            const showAvatar = idx === 0 || dateMessages[idx - 1]?.role !== msg.role;

                            return (
                              <div
                                key={msg.id}
                                className={`flex ${isAssistant ? 'justify-start' : 'justify-end'} animate-in fade-in slide-in-from-bottom-3 duration-300`}
                              >
                                {/* Avatar do bot */}
                                {isAssistant && (
                                  <div className={`flex-shrink-0 mr-3 ${showAvatar ? 'visible' : 'invisible'}`}>
                                    <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center shadow-lg">
                                      <Bot className="w-5 h-5 text-white" />
                                    </div>
                                  </div>
                                )}

                                {/* Bolha de mensagem */}
                                <div className={`
                                  max-w-[75%] px-5 py-3 rounded-2xl text-sm leading-relaxed
                                  ${isAssistant
                                    ? 'bg-white text-slate-700 shadow-sm border border-slate-200 rounded-tl-sm'
                                    : 'bg-blue-600 text-white shadow-lg rounded-tr-sm'
                                  }
                                `}>
                                  <p>{msg.content}</p>
                                  <div className={`flex items-center gap-1.5 mt-2 text-xs ${isAssistant ? 'text-slate-400' : 'text-blue-100'}`}>
                                    <Clock className="w-3 h-3" />
                                    <span>
                                      {new Date(msg.created_at).toLocaleTimeString('pt-BR', {
                                        hour: '2-digit',
                                        minute: '2-digit'
                                      })}
                                    </span>
                                  </div>
                                </div>

                                {/* Avatar do usuário */}
                                {!isAssistant && (
                                  <div className={`flex-shrink-0 ml-3 ${showAvatar ? 'visible' : 'invisible'}`}>
                                    <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center border-2 border-blue-200">
                                      <User className="w-5 h-5 text-blue-600" />
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
              </div>

              {/* Footer do Chat */}
              <div className="p-4 border-t border-slate-200 bg-slate-50/50 flex items-center justify-center flex-shrink-0">
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <Sparkles className="w-4 h-4 text-blue-600" />
                  <span className="font-medium">Conversas sincronizadas automaticamente</span>
                </div>
              </div>

              {/* Botão scroll to bottom */}
              {showScrollButton && (
                <button
                  onClick={scrollToBottom}
                  className="absolute bottom-24 right-8 p-3 bg-white border border-slate-300 rounded-full shadow-xl text-blue-600 hover:bg-blue-50 transition-all hover:scale-110"
                >
                  <ChevronDown className="w-5 h-5" />
                </button>
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
