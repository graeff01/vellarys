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
    <div className="h-screen flex flex-col bg-[#F8FAFC] overflow-hidden font-sans selection:bg-indigo-100 selection:text-indigo-900">
      {/* Background Gradients */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-20%] right-[-10%] w-[800px] h-[800px] bg-indigo-300/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-20%] left-[-10%] w-[600px] h-[600px] bg-blue-300/10 rounded-full blur-[100px]" />
      </div>

      {/* Toast de Sucesso */}
      {mensagemSucesso && (
        <div className="fixed top-6 right-6 z-50 animate-in fade-in slide-in-from-top-4 duration-300">
          <div className="bg-emerald-500 text-white rounded-2xl px-6 py-4 shadow-[0_8px_30px_rgb(0,0,0,0.12)] flex items-center gap-3 border border-emerald-400/50 backdrop-blur-md">
            <div className="p-1 bg-white/20 rounded-full">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <span className="font-semibold tracking-wide">{mensagemSucesso}</span>
          </div>
        </div>
      )}

      {/* Header Principal */}
      <header className="relative z-10 bg-white/70 backdrop-blur-xl border-b border-slate-200/60 shadow-sm flex-shrink-0">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between gap-6">

            {/* Esquerda: Identificação */}
            <div className="flex items-center gap-5 flex-1 min-w-0">
              <button
                onClick={() => router.back()}
                className="group p-2.5 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 hover:border-slate-300 transition-all shadow-sm hover:shadow-md"
              >
                <ArrowLeft className="w-5 h-5 text-slate-500 group-hover:text-slate-800 transition-colors" />
              </button>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1.5">
                  <div className="min-w-0">
                    {editandoNome ? (
                      <input
                        type="text"
                        value={nomeTemp}
                        onChange={(e) => setNomeTemp(e.target.value)}
                        onBlur={salvarNome}
                        onKeyDown={(e) => e.key === 'Enter' && salvarNome()}
                        className="text-2xl font-bold text-slate-900 bg-transparent border-b-2 border-indigo-500 outline-none w-full"
                        autoFocus
                      />
                    ) : (
                      <div
                        className="flex items-center gap-3 group cursor-pointer"
                        onClick={() => { setNomeTemp(lead.name || ''); setEditandoNome(true); }}
                      >
                        <h1 className="text-2xl font-bold text-slate-900 truncate tracking-tight">
                          {lead.name || 'Sem Nome'}
                        </h1>
                        <div className="p-1.5 rounded-lg bg-slate-100 text-slate-400 opacity-0 group-hover:opacity-100 transition-all">
                          <Edit2 className="w-3.5 h-3.5" />
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {(lead.custom_data?.tags || []).map((tag: string) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-200 transition-colors"
                    >
                      {tag}
                      <button onClick={(e) => { e.stopPropagation(); removerTag(tag); }} className="hover:text-red-600">
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}

                  {adicionandoTag ? (
                    <input
                      type="text"
                      value={novaTag}
                      onChange={(e) => setNovaTag(e.target.value)}
                      onBlur={adicionarTag}
                      onKeyDown={(e) => e.key === 'Enter' && adicionarTag()}
                      placeholder="Nova tag..."
                      className="px-3 py-0.5 rounded-lg border border-indigo-300 text-xs w-32 outline-none focus:ring-2 focus:ring-indigo-100"
                      autoFocus
                    />
                  ) : (
                    <button
                      onClick={() => setAdicionandoTag(true)}
                      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg border border-dashed border-slate-300 text-xs font-medium text-slate-500 hover:text-indigo-600 hover:border-indigo-300 hover:bg-indigo-50 transition-all"
                    >
                      <Sparkles className="w-3 h-3" />
                      Add Tag
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Direita: Ações Principais */}
            <div className="flex items-center gap-4">
              {/* Seletor de Status */}
              <div className="relative group">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl blur opacity-20 group-hover:opacity-30 transition-opacity" />
                <div className="relative bg-white border border-slate-200 rounded-xl shadow-sm p-1 flex items-center">
                  <span className="pl-3 text-xs font-bold text-slate-400 uppercase tracking-wider mr-2">Status</span>
                  <select
                    value={lead.status}
                    onChange={(e) => atualizarStatus(e.target.value)}
                    className="bg-slate-50 text-slate-900 text-sm font-semibold rounded-lg py-1.5 pl-3 pr-8 outline-none border-transparent focus:bg-white focus:ring-2 focus:ring-indigo-100 cursor-pointer appearance-none hover:bg-slate-100 transition-colors"
                  >
                    <option value="new">Novo</option>
                    <option value="in_progress">Em Atendimento</option>
                    <option value="qualified">Qualificado</option>
                    <option value="lost">Perdido</option>
                  </select>
                  <ChevronDown className="w-4 h-4 text-slate-500 absolute right-3 pointer-events-none" />
                </div>
              </div>

              {/* Seletor de Qualificação */}
              <div className="relative group">
                <div className={`absolute inset-0 rounded-xl blur opacity-20 group-hover:opacity-30 transition-opacity ${lead.qualification === 'hot' ? 'bg-red-500' :
                  lead.qualification === 'warm' ? 'bg-orange-500' :
                    'bg-blue-500'
                  }`} />
                <div className="relative bg-white border border-slate-200 rounded-xl shadow-sm p-1 flex items-center">
                  <span className="pl-3 text-xs font-bold text-slate-400 uppercase tracking-wider mr-2">Qualif.</span>
                  <select
                    value={lead.qualification}
                    onChange={(e) => atualizarQualificacao(e.target.value)}
                    className={`
                      text-sm font-bold rounded-lg py-1.5 pl-3 pr-8 outline-none border-transparent cursor-pointer appearance-none transition-colors
                      ${lead.qualification === 'hot' ? 'bg-red-50 text-red-700' :
                        lead.qualification === 'warm' ? 'bg-orange-50 text-orange-700' :
                          'bg-blue-50 text-blue-700'
                      }
                    `}
                  >
                    <option value="cold">❄️ Frio</option>
                    <option value="warm">🔥 Morno</option>
                    <option value="hot">🚀 Quente</option>
                  </select>
                  <ChevronDown className={`w-4 h-4 absolute right-3 pointer-events-none ${lead.qualification === 'hot' ? 'text-red-500' :
                    lead.qualification === 'warm' ? 'text-orange-500' :
                      'text-blue-500'
                    }`} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Grid Principal */}
      <main className="relative z-0 flex-1 overflow-hidden p-6 max-w-[1920px] mx-auto w-full">
        <div className="grid grid-cols-12 gap-6 h-full">

          {/* COLUNA 1: DETALHES (3 cols) */}
          <div className="col-span-3 flex flex-col gap-5 overflow-hidden">

            {/* Card Contato */}
            <div className="bg-white rounded-2xl border border-slate-200/60 shadow-[0_2px_20px_rgb(0,0,0,0.04)] overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <User className="w-4 h-4 text-indigo-500" />
                  Dados de Contato
                </h3>
              </div>
              <div className="p-5 space-y-4">
                <div className="group">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block group-hover:text-indigo-500 transition-colors">Telefone</label>
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600 group-hover:scale-110 transition-transform">
                      <Phone className="w-4 h-4" />
                    </div>
                    <span className="font-mono text-slate-700 font-medium select-all">{lead.phone || '-'}</span>
                  </div>
                </div>

                <div className="group">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block group-hover:text-indigo-500 transition-colors">Email</label>
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600 group-hover:scale-110 transition-transform">
                      <Mail className="w-4 h-4" />
                    </div>
                    <span className="text-slate-700 font-medium truncate select-all">{lead.email || '-'}</span>
                  </div>
                </div>

                <div className="group">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block group-hover:text-indigo-500 transition-colors">Localização</label>
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600 group-hover:scale-110 transition-transform">
                      <MapPin className="w-4 h-4" />
                    </div>
                    <span className="text-slate-700 font-medium">{lead.city || '-'}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Card Vendedor */}
            <div className="bg-white rounded-2xl border border-slate-200/60 shadow-[0_2px_20px_rgb(0,0,0,0.04)] overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-emerald-500" />
                  Vendedor Responsável
                </h3>
              </div>
              <div className="p-5">
                {lead.assigned_seller ? (
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-slate-100 to-slate-200 border border-slate-300 flex items-center justify-center text-xl font-bold text-slate-600 shadow-inner">
                      {lead.assigned_seller.name.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-bold text-slate-900 truncate">{lead.assigned_seller.name}</p>
                      <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                        <Phone className="w-3 h-3" />
                        {lead.assigned_seller.whatsapp}
                      </p>
                    </div>
                    <button
                      onClick={removerAtribuicao}
                      className="p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all opacity-50 hover:opacity-100"
                      title="Remover vendedor"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="p-4 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-center">
                      <UserPlus className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                      <p className="text-xs text-slate-500">Nenhum vendedor atribuído</p>
                    </div>
                    <select
                      onChange={(e) => atribuirVendedor(parseInt(e.target.value))}
                      disabled={atribuindoVendedor}
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-medium outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 transition-all"
                    >
                      <option value="">+ Atribuir Vendedor</option>
                      {sellers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                    </select>
                  </div>
                )}
              </div>
            </div>

            {/* AI Insights - Special Card */}
            {lead.summary && (
              <div className="relative overflow-hidden rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] group">
                <div className="absolute inset-0 bg-gradient-to-br from-violet-600 to-indigo-600" />
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                  <Bot className="w-24 h-24 rotate-12" />
                </div>
                <div className="relative p-5">
                  <div className="flex items-center gap-2 mb-3 text-white/90">
                    <Sparkles className="w-4 h-4" />
                    <h3 className="text-xs font-bold uppercase tracking-wider">IA Summary</h3>
                  </div>
                  <p className="text-white/95 text-sm leading-relaxed font-medium">
                    "{lead.summary}"
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* COLUNA 2: TIMELINE & NOTAS (3 cols) */}
          <div className="col-span-3 flex flex-col gap-5 overflow-hidden">

            {/* Timeline */}
            <div className="flex-[0.4] bg-white rounded-2xl border border-slate-200/60 shadow-[0_2px_20px_rgb(0,0,0,0.04)] overflow-hidden flex flex-col">
              <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <History className="w-4 h-4 text-amber-500" />
                  Atividades Recentes
                </h3>
              </div>
              <div className="flex-1 overflow-y-auto p-5 custom-scrollbar">
                <div className="space-y-6 relative ml-3">
                  {/* Vertical Line */}
                  <div className="absolute top-2 bottom-2 left-[5px] w-[2px] bg-slate-100" />

                  {events.length === 0 ? (
                    <p className="text-xs text-slate-400 text-center py-4">Nenhuma atividade recente.</p>
                  ) : (
                    events.slice(0, 10).map((event) => (
                      <div key={event.id} className="relative pl-6 sm:pl-8">
                        {/* Dot */}
                        <div className="absolute left-0 top-1.5 w-3 h-3 rounded-full bg-white border-2 border-slate-200 shadow-sm z-10" />
                        <div className="flex flex-col gap-1">
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider bg-slate-50 self-start px-2 py-0.5 rounded-full border border-slate-100">
                            {new Date(event.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })} • {new Date(event.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                          <p className="text-sm font-medium text-slate-700 leading-snug">
                            {event.description}
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Notas */}
            <div className="flex-1 bg-white rounded-2xl border border-slate-200/60 shadow-[0_2px_20px_rgb(0,0,0,0.04)] overflow-hidden flex flex-col">
              <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <FileText className="w-4 h-4 text-blue-500" />
                  Notas Internas
                </h3>
                {!editandoNota && (
                  <button onClick={() => setEditandoNota(true)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-600 transition-colors">
                    <span className="text-xs font-bold">+ Adicionar</span>
                  </button>
                )}
              </div>

              <div className="flex-1 overflow-y-auto p-5 custom-scrollbar bg-slate-50/30">
                {editandoNota && (
                  <div className="mb-4 bg-white p-3 rounded-xl border border-blue-200 shadow-sm animate-in fade-in slide-in-from-top-2">
                    <textarea
                      value={novaNota}
                      onChange={(e) => setNovaNota(e.target.value)}
                      placeholder="Escreva sua nota..."
                      className="w-full text-sm outline-none resize-none placeholder:text-slate-400 min-h-[80px]"
                      autoFocus
                    />
                    <div className="flex justify-end gap-2 mt-2 pt-2 border-t border-slate-100">
                      <button onClick={() => setEditandoNota(false)} className="text-xs font-medium text-slate-500 hover:text-slate-800 px-3 py-1.5 transition-colors">Cancelar</button>
                      <button onClick={salvarNota} className="text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 px-4 py-1.5 rounded-lg transition-colors shadow-sm">Salvar Nota</button>
                    </div>
                  </div>
                )}

                <div className="space-y-3">
                  {(lead.custom_data?.notas || []).length === 0 && !editandoNota && (
                    <div className="text-center py-10 opacity-50">
                      <FileText className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                      <p className="text-xs text-slate-400 font-medium">Nenhuma nota registrada</p>
                    </div>
                  )}

                  {[...(lead.custom_data?.notas || [])].reverse().map((nota: Note) => (
                    <div key={nota.id} className="group relative bg-[#FFFBEB] border border-amber-200/60 p-4 rounded-t-xl rounded-br-xl rounded-bl-[2px] shadow-sm hover:shadow-md transition-all">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <div className="w-5 h-5 rounded-full bg-amber-200 flex items-center justify-center text-[10px] font-bold text-amber-800">
                            {nota.created_by.charAt(0)}
                          </div>
                          <span className="text-[10px] font-bold text-amber-800/60 uppercase">{new Date(nota.created_at).toLocaleDateString('pt-BR')}</span>
                        </div>
                        <button onClick={() => deletarNota(nota.id)} className="text-amber-400 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      <p className="text-sm text-slate-700 font-medium leading-relaxed whitespace-pre-wrap">{nota.content}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* COLUNA 3: CHAT (6 cols) */}
          <div className="col-span-6 flex flex-col h-full overflow-hidden">
            <div className="flex-1 bg-white rounded-2xl border border-slate-200/60 shadow-[0_4px_30px_rgb(0,0,0,0.05)] flex flex-col overflow-hidden relative">

              {/* Header Chat */}
              <div className="px-6 py-4 border-b border-slate-100 bg-white/50 backdrop-blur-md flex items-center justify-between z-10">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-green-500/20 text-white">
                    <MessageSquare className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 border-inherit">WhatsApp Business</h3>
                    <p className="text-xs text-green-600 font-medium flex items-center gap-1">
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                      </span>
                      {messages.length} mensagens sincronizadas
                    </p>
                  </div>
                </div>
              </div>

              {/* Chat Area */}
              <div
                ref={chatContainerRef}
                onScroll={handleScroll}
                className="flex-1 overflow-y-auto p-6 space-y-6 bg-[#F0F2F5]"
                style={{
                  backgroundImage: `radial-gradient(#CBD5E1 1px, transparent 1px)`,
                  backgroundSize: '20px 20px'
                }}
              >
                {messages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center opacity-40">
                    <div className="w-20 h-20 bg-slate-200 rounded-full flex items-center justify-center mb-4">
                      <MessageSquare className="w-10 h-10 text-slate-400" />
                    </div>
                    <p className="font-medium text-slate-500">Nenhuma troca de mensagens</p>
                  </div>
                ) : (
                  Array.from(messageGroups.entries()).map(([date, dateMessages]) => (
                    <div key={date}>
                      <div className="sticky top-0 flex justify-center z-10 mb-6">
                        <span className="px-4 py-1.5 bg-slate-200/80 backdrop-blur-sm rounded-full text-[10px] font-bold text-slate-600 uppercase tracking-widest shadow-sm">
                          {formatDateLabel(date, dateMessages[0].created_at)}
                        </span>
                      </div>

                      <div className="space-y-1">
                        {dateMessages.map((msg, idx) => {
                          const isAssistant = msg.role === 'assistant';
                          const isLastFromUser = !isAssistant && (idx === dateMessages.length - 1 || dateMessages[idx + 1]?.role !== 'user');
                          const isFirstFromUser = !isAssistant && (idx === 0 || dateMessages[idx - 1]?.role !== 'user');

                          return (
                            <div
                              key={msg.id}
                              className={`flex w-full group ${isAssistant ? 'justify-start' : 'justify-end'}`}
                            >
                              <div className={`flex max-w-[80%] ${isAssistant ? 'flex-row' : 'flex-row-reverse'} items-end gap-2`}>

                                {/* Avatar */}
                                <div className={`w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-full text-xs font-bold shadow-sm mb-1 ${isAssistant ? 'bg-white text-slate-600' : 'bg-indigo-600 text-white'
                                  }`}>
                                  {isAssistant ? <Bot className="w-5 h-5" /> : <User className="w-4 h-4" />}
                                </div>

                                {/* Bubble */}
                                <div className={`
                                  relative px-5 py-3 shadow-sm text-[15px] leading-relaxed
                                  ${isAssistant
                                    ? 'bg-white text-slate-800 rounded-2xl rounded-bl-none border border-slate-100'
                                    : 'bg-indigo-600 text-white rounded-2xl rounded-br-none bg-gradient-to-br from-indigo-500 to-indigo-600'
                                  }
                                `}>
                                  <div className="whitespace-pre-wrap">{msg.content}</div>
                                  <div className={`text-[10px] font-medium mt-1 text-right flex items-center justify-end gap-1 ${isAssistant ? 'text-slate-400' : 'text-indigo-200'
                                    }`}>
                                    {isAssistant ? null : <CheckCircle2 className="w-3 h-3" />}
                                    {new Date(msg.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))
                )}

                <div ref={chatEndRef} />
              </div>

              {/* Scroll Button */}
              {showScrollButton && (
                <button
                  onClick={scrollToBottom}
                  className="absolute bottom-6 right-6 p-3 bg-slate-800 text-white rounded-full shadow-lg hover:bg-slate-700 transition-all hover:scale-110 active:scale-95 z-20"
                >
                  <ChevronDown className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
