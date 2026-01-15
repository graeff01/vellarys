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
  UserCheck
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
      mostrarSucesso('✨ Qualificação atualizada!');
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
      mostrarSucesso('✅ Status atualizado!');
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
      mostrarSucesso('👤 Nome atualizado!');
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
      mostrarSucesso('📝 Nota adicionada!');
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
      mostrarSucesso('🗑️ Nota excluída!');
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
      mostrarSucesso('🏷️ Tag adicionada!');
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
      mostrarSucesso('🏷️ Tag removida!');
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
      mostrarSucesso('🎉 Vendedor atribuído e notificado!');
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
      mostrarSucesso('👋 Atribuição removida!');
    } catch {
      alert('Erro ao remover atribuição');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
          <span className="text-slate-500 text-sm font-bold uppercase tracking-widest">Carregando...</span>
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4">
        <h3 className="text-xl font-bold text-slate-900">Lead não encontrado</h3>
        <button onClick={() => router.back()} className="px-6 py-2 bg-blue-600 text-white rounded-xl font-bold transition-all hover:bg-blue-700">
          Voltar
        </button>
      </div>
    );
  }

  const messageGroups = groupMessagesByDate(messages);

  const qualificationConfig = {
    quente: { bg: 'bg-rose-50', border: 'border-rose-200', text: 'text-rose-700', label: 'Quente' },
    hot: { bg: 'bg-rose-50', border: 'border-rose-200', text: 'text-rose-700', label: 'Quente' },
    morno: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', label: 'Morno' },
    warm: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', label: 'Morno' },
    frio: { bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-700', label: 'Frio' },
    cold: { bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-700', label: 'Frio' },
  };

  const currentQual = qualificationConfig[lead.qualification as keyof typeof qualificationConfig] || qualificationConfig.frio;

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col bg-slate-50/50">
      {/* Toast Notificação */}
      {mensagemSucesso && (
        <div className="fixed top-6 right-6 z-50 animate-in fade-in slide-in-from-right-4 duration-500">
          <div className="bg-white/90 backdrop-blur-xl border border-emerald-200 rounded-2xl px-5 py-4 shadow-xl flex items-center gap-4">
            <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center shadow-lg shadow-emerald-100">
              <CheckCircle2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-slate-900 font-bold text-sm">Sucesso</p>
              <p className="text-slate-500 text-xs font-medium">{mensagemSucesso}</p>
            </div>
          </div>
        </div>
      )}

      {/* Header Premium */}
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between gap-6">
          <div className="flex items-center gap-4 min-w-0">
            <button
              onClick={() => router.back()}
              className="p-2.5 hover:bg-slate-100 rounded-xl transition-all active:scale-95 group border border-slate-100"
            >
              <ArrowLeft className="w-5 h-5 text-slate-500 group-hover:text-blue-600 transition-colors" />
            </button>

            <div className="min-w-0">
              {editandoNome ? (
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={nomeTemp}
                    onChange={(e) => setNomeTemp(e.target.value)}
                    className="text-2xl font-bold bg-slate-50 border-b-2 border-blue-600 px-2 outline-none"
                    onBlur={salvarNome}
                    autoFocus
                  />
                </div>
              ) : (
                <div className="flex items-center gap-2 group">
                  <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight truncate">
                    {lead.name || 'Lead sem nome'}
                  </h1>
                  <button
                    onClick={() => { setNomeTemp(lead.name || ''); setEditandoNome(true); }}
                    className="p-1.5 opacity-0 group-hover:opacity-100 hover:bg-slate-100 rounded-lg transition-all"
                  >
                    <Edit2 className="w-4 h-4 text-slate-400" />
                  </button>
                </div>
              )}

              <div className="flex items-center gap-3 mt-1.5 overflow-x-auto no-scrollbar py-0.5">
                {(lead.custom_data?.tags || []).map((tag: string) => (
                  <Badge
                    key={tag}
                    className="flex items-center gap-1.5 bg-white border border-slate-200 text-slate-600 px-3 py-1 font-semibold text-[10px] uppercase tracking-wider rounded-lg shadow-sm"
                  >
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                    {tag}
                    <button onClick={() => removerTag(tag)} className="hover:text-rose-500 transition-colors ml-1">
                      <X className="w-3 h-3" />
                    </button>
                  </Badge>
                ))}

                {adicionandoTag ? (
                  <input
                    type="text"
                    className="border border-blue-400 rounded-lg px-2 py-0.5 text-[10px] font-bold w-24 outline-none"
                    onBlur={(e) => { setNovaTag(e.target.value); adicionarTag(); }}
                    autoFocus
                  />
                ) : (
                  <button
                    onClick={() => setAdicionandoTag(true)}
                    className="text-[10px] uppercase font-extrabold tracking-widest text-blue-600 hover:text-blue-700 py-1 px-2 bg-blue-50 rounded-lg"
                  >
                    + Tag
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center bg-slate-100/50 p-1.5 rounded-2xl border border-slate-200 hidden md:flex">
              <select
                value={lead.status}
                onChange={(e) => atualizarStatus(e.target.value)}
                className="bg-transparent text-xs font-bold text-slate-700 px-3 border-r border-slate-200 outline-none"
              >
                <option value="new">Novo</option>
                <option value="in_progress">Atendimento</option>
                <option value="qualified">Qualificado</option>
                <option value="lost">Perdido</option>
              </select>
              <select
                value={lead.qualification}
                onChange={(e) => atualizarQualificacao(e.target.value)}
                className={`text-xs font-bold transition-all px-3 outline-none ${currentQual.text}`}
              >
                <option value="cold">Frio</option>
                <option value="warm">Morno</option>
                <option value="hot">Quente</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 overflow-hidden">
        {/* Sidebar Esquerda */}
        <div className="lg:col-span-4 space-y-6 overflow-y-auto pr-2 custom-scrollbar" style={{ maxHeight: 'calc(100vh - 220px)' }}>
          {/* Dados do Lead */}
          <Card className="bg-white shadow-sm border border-slate-200 overflow-hidden rounded-2xl">
            <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="font-bold text-xs text-slate-900 uppercase tracking-widest flex items-center gap-2">
                <User className="w-3.5 h-3.5 text-blue-600" />
                Informações
              </h3>
            </div>
            <div className="p-5 space-y-4">
              <div className="space-y-3">
                {lead.phone && (
                  <div className="flex items-center gap-4 p-3.5 rounded-2xl bg-slate-50 border border-slate-100">
                    <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center border border-slate-200 shadow-sm text-slate-500">
                      <Phone className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase">Fone</p>
                      <p className="text-slate-900 font-bold text-sm">{lead.phone}</p>
                    </div>
                  </div>
                )}
                {lead.email && (
                  <div className="flex items-center gap-4 p-3.5 rounded-2xl bg-slate-50 border border-slate-100">
                    <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center border border-slate-200 shadow-sm text-slate-500">
                      <Mail className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase">E-mail</p>
                      <p className="text-slate-900 font-bold text-sm truncate">{lead.email}</p>
                    </div>
                  </div>
                )}
                {lead.city && (
                  <div className="flex items-center gap-4 p-3.5 rounded-2xl bg-slate-50 border border-slate-100">
                    <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center border border-slate-200 shadow-sm text-slate-500">
                      <MapPin className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase">Cidade</p>
                      <p className="text-slate-900 font-bold text-sm">{lead.city}</p>
                    </div>
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-slate-100 mt-2">
                <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <UserCheck className="w-3.5 h-3.5" />
                  Atribuição
                </h4>
                {lead.assigned_seller ? (
                  <div className="bg-blue-50 border border-blue-100 rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center border border-blue-200 shadow-sm">
                        <User className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="font-bold text-slate-900 text-sm">{lead.assigned_seller.name}</p>
                        <p className="text-[10px] text-blue-600 font-bold uppercase">{lead.assigned_seller.whatsapp}</p>
                      </div>
                    </div>
                    <button onClick={removerAtribuicao} className="p-2 text-rose-500 hover:bg-rose-50 rounded-lg transition-all">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <select
                      onChange={(e) => atribuirVendedor(parseInt(e.target.value))}
                      disabled={atribuindoVendedor}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-xs font-bold text-slate-600 outline-none hover:border-blue-300 transition-all cursor-pointer appearance-none"
                    >
                      <option value="">👤 SELECIONAR VENDEDOR</option>
                      {sellers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                    </select>
                    <div className="p-3 bg-amber-50 rounded-xl border border-amber-100 flex items-start gap-2">
                      <Zap className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                      <p className="text-[10px] text-amber-700 font-medium leading-relaxed">
                        Notificação via WhatsApp enviada na atribuição.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* Resumo IA */}
          {lead.summary && (
            <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-violet-500 to-indigo-500 rounded-2xl blur opacity-20 group-hover:opacity-30 transition duration-1000"></div>
              <Card className="relative bg-white shadow-sm border border-slate-200 overflow-hidden rounded-2xl">
                <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/30 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-violet-500 animate-pulse" />
                  <h3 className="font-bold text-xs text-slate-900 uppercase tracking-widest">IA Strategic Summary</h3>
                </div>
                <div className="p-5">
                  <p className="text-slate-600 text-[13px] leading-relaxed font-medium italic italic">&quot;{lead.summary}&quot;</p>
                </div>
              </Card>
            </div>
          )}

          {/* Timeline Minimalista */}
          {events.length > 0 && (
            <div className="space-y-4 px-1">
              <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-widest flex items-center gap-2">
                <History className="w-3.5 h-3.5" />
                Timeline
              </h4>
              <div className="relative ml-4 space-y-6 before:absolute before:inset-y-0 before:left-0 before:w-0.5 before:bg-slate-200">
                {events.slice(0, 5).map((event) => (
                  <div key={event.id} className="relative pl-6">
                    <div className="absolute left-[-10px] top-1 w-5 h-5 rounded-full border-2 border-white bg-slate-50 flex items-center justify-center shadow-sm">
                      {getEventIcon(event.event_type)}
                    </div>
                    <div className="flex flex-col gap-0.5 ml-1">
                      <span className="text-[11px] font-bold text-slate-900 leading-none">{event.description}</span>
                      <span className="text-[10px] text-slate-400 font-medium">
                        {new Date(event.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Notas */}
          <Card className="bg-white shadow-sm border border-slate-200 overflow-hidden rounded-2xl">
            <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
              <h3 className="font-bold text-xs text-slate-900 uppercase tracking-widest flex items-center gap-2">
                <Edit2 className="w-3.5 h-3.5 text-amber-500" />
                Notas Internas
              </h3>
              <button onClick={() => setEditandoNota(true)} className="text-[10px] font-extrabold uppercase text-blue-600 hover:text-blue-700">+ Adicionar</button>
            </div>
            <div className="p-5 space-y-4">
              {editandoNota && (
                <div className="space-y-3 p-4 bg-blue-50/50 rounded-2xl border border-blue-100">
                  <textarea
                    className="w-full bg-white border border-blue-100 rounded-xl p-3 text-xs outline-none focus:ring-2 focus:ring-blue-100 resize-none font-medium"
                    rows={3}
                    value={novaNota}
                    onChange={(e) => setNovaNota(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <button onClick={salvarNota} className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-xs font-bold shadow-lg shadow-blue-100">Salvar</button>
                    <button onClick={() => { setEditandoNota(false); setNovaNota(''); }} className="px-4 py-2 text-xs font-bold text-slate-500">Cancelar</button>
                  </div>
                </div>
              )}
              {(lead.custom_data?.notas || []).map((nota: Note) => (
                <div key={nota.id} className="group relative p-3 rounded-xl bg-slate-50 border border-slate-100 hover:border-blue-100 transition-all">
                  <div className="flex justify-between mb-1.5 grayscale opacity-60 group-hover:opacity-100 group-hover:grayscale-0 transition-all">
                    <span className="text-[9px] font-bold text-slate-400">{nota.created_by}</span>
                    <button onClick={() => deletarNota(nota.id)} className="text-rose-500"><Trash2 className="w-3 h-3" /></button>
                  </div>
                  <p className="text-xs text-slate-700 font-medium leading-relaxed">{nota.content}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Chat Principal */}
        <div className="lg:col-span-8 flex flex-col h-full bg-white shadow-sm border border-slate-200 rounded-3xl overflow-hidden">
          {/* Header do Chat */}
          <div className="px-6 py-4 border-b border-slate-100 bg-white flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center border border-blue-100 shadow-sm">
                <MessageSquare className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h3 className="font-bold text-sm text-slate-900 tracking-tight">Histórico de Mensagens</h3>
                <p className="text-[10px] font-bold text-blue-600 uppercase tracking-widest leading-none mt-1">Sincronizado via WhatsApp</p>
              </div>
            </div>
            <span className="text-[10px] font-bold text-slate-400 bg-slate-100 px-3 py-1.5 rounded-full uppercase tracking-widest">
              {messages.length} Mensagens
            </span>
          </div>

          <div
            ref={chatContainerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto p-6 space-y-8 bg-slate-50/20 custom-scrollbar"
          >
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-400">
                <MessageSquare className="w-12 h-12 mb-2 opacity-20" />
                <p className="text-sm font-bold">Inicie uma conversa</p>
              </div>
            ) : (
              <>
                {Array.from(messageGroups.entries()).map(([date, dateMessages]) => (
                  <div key={date}>
                    <div className="flex items-center justify-center my-8">
                      <div className="h-px bg-slate-200 flex-1" />
                      <span className="px-5 py-2 text-[10px] font-bold text-slate-500 bg-white border border-slate-200 rounded-full mx-4 uppercase tracking-widest shadow-sm">
                        {formatDateLabel(date, dateMessages[0].created_at)}
                      </span>
                      <div className="h-px bg-slate-200 flex-1" />
                    </div>

                    <div className="space-y-6">
                      {dateMessages.map((msg, idx) => {
                        const isAssistant = msg.role === 'assistant';
                        const showAvatar = idx === 0 || dateMessages[idx - 1]?.role !== msg.role;

                        return (
                          <div key={msg.id} className={`flex ${isAssistant ? 'justify-start' : 'justify-end'} animate-in fade-in slide-in-from-bottom-2 duration-500`}>
                            {isAssistant && (
                              <div className={`flex-shrink-0 mr-3 ${showAvatar ? 'visible' : 'invisible'}`}>
                                <div className="w-9 h-9 bg-slate-900 rounded-xl flex items-center justify-center shadow-lg">
                                  <Bot className="w-5 h-5 text-white" />
                                </div>
                              </div>
                            )}

                            <div className={`
                                max-w-[85%] px-5 py-4 rounded-3xl text-[13px] font-medium leading-relaxed
                                ${isAssistant
                                ? 'bg-white text-slate-700 shadow-sm border border-slate-100 rounded-tl-none'
                                : 'bg-blue-600 text-white shadow-lg shadow-blue-100 rounded-tr-none'
                              }
                             `}>
                              <p>{msg.content}</p>
                              <div className={`flex items-center gap-1.5 mt-2 ${isAssistant ? 'text-slate-400' : 'text-blue-100'}`}>
                                <Clock className="w-3 h-3" />
                                <span className="text-[10px] font-bold">
                                  {new Date(msg.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                            </div>

                            {!isAssistant && (
                              <div className={`flex-shrink-0 ml-3 ${showAvatar ? 'visible' : 'invisible'}`}>
                                <div className="w-9 h-9 bg-blue-100 rounded-xl flex items-center justify-center border border-blue-200">
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

          <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-center">
            <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-slate-200 shadow-sm text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-blue-500" />
              Sincronizado via Velaris Strategic Hub
            </div>
          </div>

          {showScrollButton && (
            <button
              onClick={scrollToBottom}
              className="absolute bottom-24 right-10 p-3.5 bg-white border border-slate-200 rounded-full shadow-2xl text-blue-600 hover:bg-slate-50 transition-all hover:-translate-y-1"
            >
              <ChevronDown className="w-6 h-6" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}