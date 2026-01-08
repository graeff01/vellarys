'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardHeader } from '@/components/ui/card';
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
  Calendar,
  Clock,
  MessageSquare,
  Sparkles,
  Edit2,
  Check,
  X,
  Plus,
  Trash2,
  UserPlus,
  History,
  CheckCircle2,
  Loader2,
  Zap,
  TrendingUp
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
    default: return <Clock className={`${iconClass} text-gray-600`} />;
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
  const [hoveredMessage, setHoveredMessage] = useState<number | null>(null);
  
  const [editandoNome, setEditandoNome] = useState(false);
  const [nomeTemp, setNomeTemp] = useState('');
  
  const [editandoNota, setEditandoNota] = useState(false);
  const [novaNota, setNovaNota] = useState('');
  
  const [adicionandoTag, setAdicionandoTag] = useState(false);
  const [novaTag, setNovaTag] = useState('');
  
  const [salvando, setSalvando] = useState(false);
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
        setSellers((sellersData as any).sellers || []);
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
      setSalvando(true);
      await updateLead(lead.id, { qualification: novaQualificacao });
      setLead({ ...lead, qualification: novaQualificacao });
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
      mostrarSucesso('✨ Qualificação atualizada!');
    } catch (error) {
      alert('Erro ao atualizar qualificação');
    } finally {
      setSalvando(false);
    }
  };

  const atualizarStatus = async (novoStatus: string) => {
    if (!lead) return;
    try {
      setSalvando(true);
      await updateLead(lead.id, { status: novoStatus });
      setLead({ ...lead, status: novoStatus });
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
      mostrarSucesso('✅ Status atualizado!');
    } catch (error) {
      alert('Erro ao atualizar status');
    } finally {
      setSalvando(false);
    }
  };

  const salvarNome = async () => {
    if (!lead || !nomeTemp.trim()) {
      setEditandoNome(false);
      return;
    }
    try {
      setSalvando(true);
      await updateLead(lead.id, { name: nomeTemp.trim() });
      setLead({ ...lead, name: nomeTemp.trim() });
      setEditandoNome(false);
      mostrarSucesso('👤 Nome atualizado!');
    } catch (error) {
      alert('Erro ao salvar nome');
    } finally {
      setSalvando(false);
    }
  };

  const salvarNota = async () => {
    if (!lead || !novaNota.trim()) return;
    try {
      setSalvando(true);
      const notasAtuais = lead.custom_data?.notas || [];
      const novaNot = {
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
    } catch (error) {
      alert('Erro ao salvar nota');
    } finally {
      setSalvando(false);
    }
  };

  const deletarNota = async (notaId: number) => {
    if (!lead || !confirm('Excluir nota?')) return;
    try {
      setSalvando(true);
      const notasAtuais = lead.custom_data?.notas || [];
      const notasFiltradas = notasAtuais.filter((n: any) => n.id !== notaId);
      const customDataAtualizado = { ...lead.custom_data, notas: notasFiltradas };
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
      mostrarSucesso('🗑️ Nota excluída!');
    } catch (error) {
      alert('Erro ao deletar nota');
    } finally {
      setSalvando(false);
    }
  };

  const adicionarTag = async () => {
    if (!lead || !novaTag.trim()) {
      setAdicionandoTag(false);
      return;
    }
    try {
      setSalvando(true);
      const tagsAtuais = lead.custom_data?.tags || [];
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
    } catch (error) {
      alert('Erro ao adicionar tag');
    } finally {
      setSalvando(false);
    }
  };

  const removerTag = async (tag: string) => {
    if (!lead) return;
    try {
      setSalvando(true);
      const tagsAtuais = lead.custom_data?.tags || [];
      const tagsFiltradas = tagsAtuais.filter((t: string) => t !== tag);
      const customDataAtualizado = { ...lead.custom_data, tags: tagsFiltradas };
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
      mostrarSucesso('🏷️ Tag removida!');
    } catch (error) {
      alert('Erro ao remover tag');
    } finally {
      setSalvando(false);
    }
  };

  const atribuirVendedor = async (sellerId: number) => {
    if (!lead || !sellerId) return;
    
    try {
      setAtribuindoVendedor(true);
      console.log('🔔 Atribuindo vendedor e enviando notificação...');
      
      // Backend envia notificação automática via WhatsApp!
      await assignSellerToLead(lead.id, sellerId);
      
      console.log('✅ Vendedor atribuído com sucesso!');
      
      // Recarrega dados
      const leadAtualizado = await getLead(lead.id);
      setLead(leadAtualizado as Lead);
      
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
      
      mostrarSucesso('🎉 Vendedor atribuído e notificado no WhatsApp!');
    } catch (error) {
      console.error('❌ Erro ao atribuir vendedor:', error);
      alert('Erro ao atribuir vendedor. Verifique o console.');
    } finally {
      setAtribuindoVendedor(false);
    }
  };

  const removerAtribuicao = async () => {
    if (!lead || !confirm('Remover atribuição?')) return;
    try {
      setSalvando(true);
      await unassignSellerFromLead(lead.id);
      setLead({ ...lead, assigned_seller: null });
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
      mostrarSucesso('👋 Atribuição removida!');
    } catch (error) {
      alert('Erro ao remover atribuição');
    } finally {
      setSalvando(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <div className="flex flex-col items-center gap-3">
          <div className="relative">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-200 border-t-blue-600"></div>
            <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-blue-400 to-purple-400 opacity-20 blur-xl"></div>
          </div>
          <span className="text-gray-600 text-sm font-semibold">Carregando detalhes...</span>
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4 bg-gradient-to-br from-red-50 via-white to-orange-50">
        <div className="w-20 h-20 bg-gradient-to-br from-red-400 to-orange-500 rounded-2xl flex items-center justify-center shadow-lg">
          <X className="w-10 h-10 text-white" />
        </div>
        <div className="text-center">
          <h3 className="text-xl font-bold text-gray-900 mb-2">Lead não encontrado</h3>
          <p className="text-gray-600 text-sm">Este lead pode ter sido removido.</p>
        </div>
        <button onClick={() => router.back()} className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all hover:scale-105">
          ← Voltar aos Leads
        </button>
      </div>
    );
  }

  const messageGroups = groupMessagesByDate(messages);
  
  const qualificationConfig = {
    quente: { bg: 'bg-gradient-to-r from-red-500 to-orange-500', text: 'text-white', icon: '🔥', label: 'Quente' },
    hot: { bg: 'bg-gradient-to-r from-red-500 to-orange-500', text: 'text-white', icon: '🔥', label: 'Quente' },
    morno: { bg: 'bg-gradient-to-r from-orange-400 to-yellow-400', text: 'text-white', icon: '🌤️', label: 'Morno' },
    warm: { bg: 'bg-gradient-to-r from-orange-400 to-yellow-400', text: 'text-white', icon: '🌤️', label: 'Morno' },
    frio: { bg: 'bg-gradient-to-r from-blue-500 to-cyan-500', text: 'text-white', icon: '❄️', label: 'Frio' },
    cold: { bg: 'bg-gradient-to-r from-blue-500 to-cyan-500', text: 'text-white', icon: '❄️', label: 'Frio' },
  };

  const currentQual = qualificationConfig[lead.qualification as keyof typeof qualificationConfig] || qualificationConfig.frio;

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Toast de Sucesso - Melhorado */}
      {mensagemSucesso && (
        <div className="fixed top-6 right-6 z-50 animate-in slide-in-from-top-2 duration-300">
          <div className="bg-white border-2 border-green-400 rounded-2xl px-5 py-3 shadow-2xl flex items-center gap-3 backdrop-blur-sm">
            <div className="w-10 h-10 bg-gradient-to-br from-green-400 to-emerald-500 rounded-xl flex items-center justify-center animate-bounce">
              <CheckCircle2 className="w-6 h-6 text-white" />
            </div>
            <span className="text-gray-800 font-bold">{mensagemSucesso}</span>
          </div>
        </div>
      )}

      {/* Header Premium */}
      <div className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 shadow-sm px-4 py-3 flex-shrink-0">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => router.back()} 
            className="p-2 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 rounded-xl transition-all hover:scale-110 active:scale-95 group"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600 group-hover:text-blue-600 transition-colors" />
          </button>
          
          <div className="flex-1 min-w-0">
            {editandoNome ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={nomeTemp}
                  onChange={(e) => setNomeTemp(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') salvarNome();
                    if (e.key === 'Escape') setEditandoNome(false);
                  }}
                  className="text-xl font-bold border-b-2 border-blue-600 bg-transparent outline-none flex-1"
                  autoFocus
                />
                <button onClick={salvarNome} className="p-1.5 bg-green-100 hover:bg-green-200 rounded-lg transition-colors">
                  <Check className="w-4 h-4 text-green-700" />
                </button>
                <button onClick={() => setEditandoNome(false)} className="p-1.5 bg-red-100 hover:bg-red-200 rounded-lg transition-colors">
                  <X className="w-4 h-4 text-red-700" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2 group">
                <h1 className="text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent truncate">
                  {lead.name || 'Lead sem nome'}
                </h1>
                <button
                  onClick={() => { setNomeTemp(lead.name || ''); setEditandoNome(true); }}
                  className="p-1 opacity-0 group-hover:opacity-100 hover:bg-blue-50 rounded-lg transition-all"
                >
                  <Edit2 className="w-3.5 h-3.5 text-gray-400" />
                </button>
              </div>
            )}
            
            {/* Tags + Badges Premium */}
            <div className="flex items-center gap-2 mt-2 flex-wrap text-xs">
              {(lead.custom_data?.tags || []).map((tag: string) => (
                <Badge 
                  key={tag} 
                  className="flex items-center gap-1.5 bg-gradient-to-r from-blue-500 to-indigo-500 text-white border-0 px-3 py-1 shadow-md hover:shadow-lg transition-all hover:scale-105"
                >
                  <span className="text-base">🏷️</span>
                  {tag}
                  <button onClick={() => removerTag(tag)} className="hover:bg-white/20 rounded-full p-0.5 transition-colors">
                    <X className="w-3 h-3" />
                  </button>
                </Badge>
              ))}
              
              {adicionandoTag ? (
                <input
                  type="text"
                  value={novaTag}
                  onChange={(e) => setNovaTag(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') adicionarTag();
                    if (e.key === 'Escape') setAdicionandoTag(false);
                  }}
                  onBlur={adicionarTag}
                  className="border-2 border-blue-400 rounded-lg px-2 py-1 text-xs w-24 outline-none shadow-sm"
                  placeholder="Nova tag"
                  autoFocus
                />
              ) : (
                <button
                  onClick={() => setAdicionandoTag(true)}
                  className="flex items-center gap-1 text-xs bg-gradient-to-r from-blue-500 to-indigo-500 text-white px-3 py-1 rounded-lg font-semibold shadow-md hover:shadow-lg transition-all hover:scale-105"
                >
                  <Plus className="w-3 h-3" /> Tag
                </button>
              )}
              
              <span className="text-gray-300">•</span>
              
              {/* Qualificação Premium */}
              <select
                value={lead.qualification}
                onChange={(e) => atualizarQualificacao(e.target.value)}
                disabled={salvando}
                className={`${currentQual.bg} ${currentQual.text} border-0 rounded-lg px-3 py-1.5 text-xs font-bold cursor-pointer outline-none shadow-md hover:shadow-lg transition-all`}
              >
                <option value="frio">❄️ Frio</option>
                <option value="morno">🌤️ Morno</option>
                <option value="quente">🔥 Quente</option>
              </select>
              
              <span className="text-gray-300">•</span>
              
              {/* Status Premium */}
              <select
                value={lead.status}
                onChange={(e) => atualizarStatus(e.target.value)}
                disabled={salvando}
                className="bg-gradient-to-r from-gray-100 to-gray-200 border-2 border-gray-300 rounded-lg px-3 py-1.5 text-xs font-semibold text-gray-700 cursor-pointer outline-none hover:border-gray-400 transition-all shadow-sm"
              >
                <option value="new">🆕 Novo</option>
                <option value="in_progress">⚡ Atendimento</option>
                <option value="qualified">✅ Qualificado</option>
                <option value="handed_off">🤝 Transferido</option>
                <option value="converted">🎉 Convertido</option>
                <option value="lost">❌ Perdido</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Layout Principal */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 p-4 overflow-hidden">
        
        {/* Coluna Esquerda - Scroll Interno */}
        <div className="lg:col-span-1 space-y-3 overflow-y-auto pr-2" style={{ maxHeight: 'calc(100vh - 200px)', scrollbarWidth: 'thin', scrollbarColor: '#3B82F6 transparent' }}>
          
          {/* Card Informações Premium */}
          <Card className="bg-white/90 backdrop-blur-sm shadow-lg hover:shadow-xl transition-all border-0 overflow-hidden">
            <div className="bg-gradient-to-r from-blue-500 to-indigo-600 p-3">
              <h3 className="font-bold text-sm text-white flex items-center gap-2">
                <User className="w-4 h-4" />
                Informações do Lead
              </h3>
            </div>
            <div className="p-3 space-y-2.5">
              {lead.phone && (
                <a 
                  href={`tel:${lead.phone}`} 
                  className="flex items-center gap-3 p-2.5 rounded-xl bg-gradient-to-r from-green-50 to-emerald-50 hover:from-green-100 hover:to-emerald-100 transition-all group border border-green-200 shadow-sm hover:shadow-md"
                >
                  <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center shadow-md">
                    <Phone className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-gray-700 group-hover:text-green-700 font-semibold text-xs transition-colors">{lead.phone}</span>
                </a>
              )}
              
              {lead.email && (
                <a 
                  href={`mailto:${lead.email}`} 
                  className="flex items-center gap-3 p-2.5 rounded-xl bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 transition-all group border border-blue-200 shadow-sm hover:shadow-md"
                >
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-md">
                    <Mail className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-gray-700 group-hover:text-blue-700 font-semibold text-xs truncate transition-colors">{lead.email}</span>
                </a>
              )}
              
              {lead.city && (
                <div className="flex items-center gap-3 p-2.5 rounded-xl bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 shadow-sm">
                  <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl flex items-center justify-center shadow-md">
                    <MapPin className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-gray-800 font-semibold text-xs">{lead.city}</span>
                </div>
              )}

              <div className="flex items-center gap-3 p-2.5 rounded-xl bg-gradient-to-r from-gray-50 to-slate-50 border border-gray-200 shadow-sm">
                <div className="w-10 h-10 bg-gradient-to-br from-gray-500 to-slate-600 rounded-xl flex items-center justify-center shadow-md">
                  <Calendar className="w-4 h-4 text-white" />
                </div>
                <div>
                  <p className="text-[10px] text-gray-500 font-semibold uppercase tracking-wide">Criado em</p>
                  <p className="text-gray-900 font-bold text-xs">
                    {new Date(lead.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' })}
                  </p>
                </div>
              </div>

              {/* Vendedor Premium com Notificação */}
              <div className="border-t-2 border-gray-100 pt-3 mt-3">
                <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider block mb-2 flex items-center gap-1">
                  <UserPlus className="w-3.5 h-3.5" />
                  Vendedor Responsável
                </label>
                
                {lead.assigned_seller ? (
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-400 rounded-xl p-3 shadow-md">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center shadow-lg ring-2 ring-green-200">
                          <User className="w-5 h-5 text-white" />
                        </div>
                        <div>
                          <p className="font-bold text-gray-900 text-sm">{lead.assigned_seller.name}</p>
                          <p className="text-xs text-gray-600 flex items-center gap-1">
                            <Phone className="w-3 h-3" />
                            {lead.assigned_seller.whatsapp}
                          </p>
                        </div>
                      </div>
                      <button 
                        onClick={removerAtribuicao} 
                        disabled={salvando}
                        className="text-red-600 text-xs font-bold hover:bg-red-100 px-2 py-1 rounded-lg transition-all"
                      >
                        Remover
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="relative">
                    <select
                      onChange={(e) => atribuirVendedor(parseInt(e.target.value))}
                      className="w-full bg-white border-2 border-gray-300 rounded-xl px-3 py-2.5 text-sm font-semibold appearance-none cursor-pointer hover:border-blue-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all shadow-sm"
                      defaultValue=""
                      disabled={atribuindoVendedor}
                    >
                      <option value="" disabled>
                        {atribuindoVendedor ? '📲 Notificando vendedor...' : '👤 Selecione um vendedor...'}
                      </option>
                      {sellers.filter(s => s.active).map(seller => (
                        <option key={seller.id} value={seller.id}>
                          {seller.name} {seller.available ? '✅ Disponível' : '⏸️ Ocupado'}
                        </option>
                      ))}
                    </select>
                    
                    {atribuindoVendedor && (
                      <div className="absolute inset-0 bg-white/95 backdrop-blur-sm rounded-xl flex items-center justify-center">
                        <div className="flex items-center gap-2 text-blue-600">
                          <Loader2 className="w-5 h-5 animate-spin" />
                          <span className="text-sm font-bold">Enviando notificação...</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                {!lead.assigned_seller && (
                  <div className="mt-2 flex items-start gap-2 p-2 bg-blue-50 border border-blue-200 rounded-lg">
                    <Sparkles className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                    <p className="text-[10px] text-blue-700 font-semibold leading-relaxed">
                      O vendedor receberá automaticamente um resumo completo da conversa no WhatsApp! 📲
                    </p>
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* Timeline Premium */}
          {events.length > 0 && (
            <Card className="bg-white/90 backdrop-blur-sm shadow-lg hover:shadow-xl transition-all border-0 overflow-hidden">
              <div className="bg-gradient-to-r from-purple-500 to-pink-600 p-3">
                <h3 className="font-bold text-sm text-white flex items-center gap-2">
                  <History className="w-4 h-4" />
                  Histórico de Eventos
                </h3>
              </div>
              <div className="p-3 space-y-2.5">
                {events.slice(0, 4).map((event) => (
                  <div key={event.id} className="flex gap-2.5 group">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-100 to-indigo-100 flex items-center justify-center flex-shrink-0 border-2 border-blue-200 group-hover:scale-110 transition-transform shadow-sm">
                      {getEventIcon(event.event_type)}
                    </div>
                    <div className="flex-1">
                      <p className="text-gray-900 font-bold text-xs">{event.description}</p>
                      <span className="text-[10px] text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full inline-block mt-1">
                        {new Date(event.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Resumo IA Premium */}
          {lead.summary && (
            <Card className="bg-gradient-to-br from-purple-100 via-pink-50 to-purple-50 shadow-lg hover:shadow-xl transition-all border-2 border-purple-300 overflow-hidden">
              <div className="bg-gradient-to-r from-purple-600 to-pink-600 p-3">
                <h3 className="font-bold text-sm text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4" />
                  Resumo da IA
                </h3>
              </div>
              <div className="p-3">
                <p className="text-gray-800 text-xs leading-relaxed font-medium">{lead.summary}</p>
              </div>
            </Card>
          )}

          {/* Notas Premium */}
          <Card className="bg-white/90 backdrop-blur-sm shadow-lg hover:shadow-xl transition-all border-0 overflow-hidden">
            <div className="bg-gradient-to-r from-yellow-500 to-orange-600 p-3 flex items-center justify-between">
              <h3 className="font-bold text-sm text-white flex items-center gap-2">
                <span className="text-lg">📝</span>
                Notas Internas
              </h3>
              <button 
                onClick={() => setEditandoNota(true)} 
                disabled={salvando}
                className="flex items-center gap-1 text-xs bg-white/20 hover:bg-white/30 text-white px-2 py-1 rounded-lg font-bold transition-all"
              >
                <Plus className="w-3 h-3" /> Nova
              </button>
            </div>
            
            <div className="p-3 space-y-2.5">
              {(lead.custom_data?.notas || []).slice(0, 3).map((nota: any) => (
                <div key={nota.id} className="bg-gradient-to-r from-yellow-50 to-amber-50 border-l-4 border-yellow-500 p-3 rounded-lg shadow-sm hover:shadow-md transition-all">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[10px] font-bold text-gray-700 bg-white px-2 py-1 rounded-full shadow-sm">
                      {nota.created_by} • {new Date(nota.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                    </span>
                    <button 
                      onClick={() => deletarNota(nota.id)} 
                      disabled={salvando}
                      className="text-red-600 hover:bg-red-100 p-1 rounded transition-colors"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                  <p className="text-gray-800 text-xs font-semibold leading-relaxed">{nota.content}</p>
                </div>
              ))}

              {editandoNota && (
                <div className="space-y-2 bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-300 rounded-xl p-3 shadow-md">
                  <textarea
                    value={novaNota}
                    onChange={(e) => setNovaNota(e.target.value)}
                    placeholder="Digite sua nota aqui..."
                    className="w-full border-2 border-gray-300 rounded-lg p-2.5 text-xs font-medium focus:border-blue-400 focus:ring-2 focus:ring-blue-200 outline-none transition-all resize-none"
                    rows={3}
                    disabled={salvando}
                  />
                  <div className="flex gap-2">
                    <button 
                      onClick={salvarNota} 
                      disabled={salvando || !novaNota.trim()}
                      className="flex-1 px-3 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-bold hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md hover:shadow-lg disabled:opacity-50"
                    >
                      {salvando ? 'Salvando...' : 'Salvar Nota'}
                    </button>
                    <button 
                      onClick={() => {setEditandoNota(false); setNovaNota('');}} 
                      disabled={salvando}
                      className="px-3 py-2 border-2 border-gray-300 rounded-lg font-bold hover:bg-gray-50 transition-colors"
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              )}
              
              {!editandoNota && (lead.custom_data?.notas || []).length === 0 && (
                <div className="text-center py-6">
                  <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-2">
                    <span className="text-2xl">📝</span>
                  </div>
                  <p className="text-xs text-gray-500 font-semibold">Nenhuma nota ainda</p>
                  <p className="text-[10px] text-gray-400 mt-1">Clique em "Nova" para adicionar</p>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Chat Premium */}
        <div className="lg:col-span-2">
          <Card className="h-full flex flex-col bg-white/90 backdrop-blur-sm shadow-xl border-0 overflow-hidden">
            <div className="bg-gradient-to-r from-blue-600 to-indigo-700 p-3 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 bg-white/20 rounded-xl flex items-center justify-center shadow-lg">
                  <MessageSquare className="w-5 h-5 text-white" />
                </div>
                <h3 className="font-bold text-sm text-white">Histórico da Conversa</h3>
              </div>
              <span className="text-xs font-bold text-white/80 bg-white/20 px-3 py-1 rounded-full backdrop-blur-sm">
                {messages.length} msgs
              </span>
            </div>

            <div
              ref={chatContainerRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto p-4 space-y-3 bg-gradient-to-b from-gray-50 to-white"
              style={{ scrollbarWidth: 'thin', scrollbarColor: '#60A5FA transparent' }}
            >
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-400">
                  <div className="w-20 h-20 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-2xl flex items-center justify-center mb-3 shadow-lg">
                    <MessageSquare className="w-10 h-10 text-blue-400" />
                  </div>
                  <p className="text-sm font-bold">Sem mensagens</p>
                  <p className="text-xs text-gray-400 mt-1">Aguardando primeira interação</p>
                </div>
              ) : (
                <>
                  {Array.from(messageGroups.entries()).map(([date, dateMessages]) => (
                    <div key={date}>
                      <div className="flex items-center justify-center my-4">
                        <span className="px-4 py-1.5 text-xs font-bold text-gray-600 bg-white border-2 border-gray-200 rounded-full shadow-md">
                          {formatDateLabel(date, dateMessages[0].created_at)}
                        </span>
                      </div>

                      <div className="space-y-3">
                        {dateMessages.map((msg, idx) => {
                          const isAssistant = msg.role === 'assistant';
                          const showAvatar = idx === 0 || dateMessages[idx - 1]?.role !== msg.role;
                          
                          return (
                            <div key={msg.id} className={`flex ${isAssistant ? 'justify-start' : 'justify-end'} animate-in fade-in duration-300`}>
                              {isAssistant && (
                                <div className={`flex-shrink-0 mr-2.5 ${showAvatar ? 'visible' : 'invisible'}`}>
                                  <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center shadow-lg ring-2 ring-purple-200">
                                    <Bot className="w-4 h-4 text-white" />
                                  </div>
                                </div>
                              )}

                              <div className={`
                                max-w-[80%] px-4 py-2.5 rounded-2xl shadow-md hover:shadow-lg transition-all text-xs font-medium
                                ${isAssistant 
                                  ? 'bg-white text-gray-800 border-2 border-gray-200 rounded-tl-sm' 
                                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-tr-sm'
                                }
                              `}>
                                <p className="leading-relaxed">{msg.content}</p>
                                <div className={`flex items-center gap-1 mt-1.5 ${isAssistant ? 'text-gray-400' : 'text-blue-100'}`}>
                                  <Clock className="w-3 h-3" />
                                  <span className="text-[10px] font-bold">
                                    {new Date(msg.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                                  </span>
                                </div>
                              </div>

                              {!isAssistant && (
                                <div className={`flex-shrink-0 ml-2.5 ${showAvatar ? 'visible' : 'invisible'}`}>
                                  <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-full flex items-center justify-center shadow-lg ring-2 ring-blue-200">
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
              <div ref={chatEndRef} />
            </div>

            {showScrollButton && (
              <div className="absolute bottom-20 right-6">
                <button 
                  onClick={scrollToBottom} 
                  className="p-3 bg-white border-2 border-blue-300 rounded-full shadow-2xl hover:bg-blue-50 transition-all hover:scale-110 active:scale-95"
                >
                  <ChevronDown className="w-5 h-5 text-blue-600" />
                </button>
              </div>
            )}

            <div className="p-3 border-t-2 border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50 flex-shrink-0">
              <p className="text-[10px] text-gray-600 text-center font-semibold flex items-center justify-center gap-1">
                <Sparkles className="w-3 h-3 text-purple-500" />
                Conversa gerenciada automaticamente pela IA do Velaris
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}