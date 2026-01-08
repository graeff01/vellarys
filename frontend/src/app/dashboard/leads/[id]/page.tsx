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
  Send,
  AlertCircle,
  CheckCircle2,
  Flame,
  Circle
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

// ===============================================
// HELPERS
// ===============================================

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

function isToday(dateString: string): boolean {
  const date = new Date(dateString);
  const today = new Date();
  return date.toDateString() === today.toDateString();
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
  switch (eventType) {
    case 'status_change':
      return <History className="w-4 h-4 text-blue-600" />;
    case 'qualification_change':
      return <Sparkles className="w-4 h-4 text-purple-600" />;
    case 'seller_assigned':
      return <UserPlus className="w-4 h-4 text-green-600" />;
    case 'seller_unassigned':
      return <X className="w-4 h-4 text-red-600" />;
    default:
      return <Clock className="w-4 h-4 text-gray-600" />;
  }
}

// ===============================================
// COMPONENTE PRINCIPAL
// ===============================================

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
  
  // Estados de feedback
  const [salvando, setSalvando] = useState(false);
  const [mensagemSucesso, setMensagemSucesso] = useState('');
  const [atribuindoVendedor, setAtribuindoVendedor] = useState(false);
  
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Carrega dados
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

  // Feedback de sucesso
  const mostrarSucesso = (mensagem: string) => {
    setMensagemSucesso(mensagem);
    setTimeout(() => setMensagemSucesso(''), 3000);
  };

  // ===============================================
  // FUNÇÕES DE ATUALIZAÇÃO
  // ===============================================

  const atualizarQualificacao = async (novaQualificacao: string) => {
    if (!lead) return;
    
    try {
      setSalvando(true);
      await updateLead(lead.id, { qualification: novaQualificacao });
      setLead({ ...lead, qualification: novaQualificacao });
      
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
      
      mostrarSucesso('Qualificação atualizada!');
    } catch (error) {
      console.error('Erro ao atualizar qualificação:', error);
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
      
      mostrarSucesso('Status atualizado!');
    } catch (error) {
      console.error('Erro ao atualizar status:', error);
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
      mostrarSucesso('Nome atualizado!');
    } catch (error) {
      console.error('Erro ao salvar nome:', error);
      alert('Erro ao salvar nome');
    } finally {
      setSalvando(false);
    }
  };

  // ===============================================
  // FUNÇÕES DE NOTAS
  // ===============================================

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
      
      const customDataAtualizado = {
        ...lead.custom_data,
        notas: [...notasAtuais, novaNot],
      };
      
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
      setNovaNota('');
      setEditandoNota(false);
      mostrarSucesso('Nota adicionada!');
    } catch (error) {
      console.error('Erro ao salvar nota:', error);
      alert('Erro ao salvar nota');
    } finally {
      setSalvando(false);
    }
  };

  const deletarNota = async (notaId: number) => {
    if (!lead || !confirm('Tem certeza que deseja excluir esta nota?')) return;
    
    try {
      setSalvando(true);
      const notasAtuais = lead.custom_data?.notas || [];
      const notasFiltradas = notasAtuais.filter((n: any) => n.id !== notaId);
      
      const customDataAtualizado = {
        ...lead.custom_data,
        notas: notasFiltradas,
      };
      
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
      mostrarSucesso('Nota excluída!');
    } catch (error) {
      console.error('Erro ao deletar nota:', error);
      alert('Erro ao deletar nota');
    } finally {
      setSalvando(false);
    }
  };

  // ===============================================
  // FUNÇÕES DE TAGS
  // ===============================================

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
      
      const customDataAtualizado = {
        ...lead.custom_data,
        tags: [...tagsAtuais, tagFormatada],
      };
      
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
      setNovaTag('');
      setAdicionandoTag(false);
      mostrarSucesso('Tag adicionada!');
    } catch (error) {
      console.error('Erro ao adicionar tag:', error);
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
      
      const customDataAtualizado = {
        ...lead.custom_data,
        tags: tagsFiltradas,
      };
      
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
      mostrarSucesso('Tag removida!');
    } catch (error) {
      console.error('Erro ao remover tag:', error);
      alert('Erro ao remover tag');
    } finally {
      setSalvando(false);
    }
  };

  // ===============================================
  // FUNÇÕES DE VENDEDOR (COM NOTIFICAÇÃO!)
  // ===============================================

  const atribuirVendedor = async (sellerId: number) => {
    if (!lead || !sellerId) return;
    
    try {
      setAtribuindoVendedor(true);
      
      // Backend já envia notificação automaticamente!
      await assignSellerToLead(lead.id, sellerId);
      
      const leadAtualizado = await getLead(lead.id);
      setLead(leadAtualizado as Lead);
      
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
      
      mostrarSucesso('✅ Vendedor atribuído e notificado no WhatsApp!');
    } catch (error) {
      console.error('Erro ao atribuir vendedor:', error);
      alert('Erro ao atribuir vendedor');
    } finally {
      setAtribuindoVendedor(false);
    }
  };

  const removerAtribuicao = async () => {
    if (!lead || !confirm('Tem certeza que deseja remover a atribuição?')) return;
    
    try {
      setSalvando(true);
      await unassignSellerFromLead(lead.id);
      setLead({ ...lead, assigned_seller: null });
      
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
      
      mostrarSucesso('Atribuição removida!');
    } catch (error) {
      console.error('Erro ao remover atribuição:', error);
      alert('Erro ao remover atribuição');
    } finally {
      setSalvando(false);
    }
  };

  // ===============================================
  // RENDER
  // ===============================================

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-blue-600 border-t-transparent"></div>
          <span className="text-gray-500 text-sm font-medium">Carregando detalhes...</span>
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <div className="w-20 h-20 bg-red-50 rounded-full flex items-center justify-center">
          <AlertCircle className="w-10 h-10 text-red-600" />
        </div>
        <div className="text-center">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">Lead não encontrado</h3>
          <p className="text-gray-500 text-sm">Este lead pode ter sido removido ou você não tem permissão.</p>
        </div>
        <button
          onClick={() => router.back()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Voltar aos Leads
        </button>
      </div>
    );
  }

  const messageGroups = groupMessagesByDate(messages);

  // Mapeamento de cores por qualificação
  const qualificationColors = {
    quente: 'bg-red-100 text-red-700 border-red-300',
    hot: 'bg-red-100 text-red-700 border-red-300',
    morno: 'bg-orange-100 text-orange-700 border-orange-300',
    warm: 'bg-orange-100 text-orange-700 border-orange-300',
    frio: 'bg-blue-100 text-blue-700 border-blue-300',
    cold: 'bg-blue-100 text-blue-700 border-blue-300',
  };

  const qualificationIcons = {
    quente: '🔥',
    hot: '🔥',
    morno: '🌤️',
    warm: '🌤️',
    frio: '❄️',
    cold: '❄️',
  };

  return (
    <div className="space-y-6 pb-6">
      {/* Feedback de sucesso */}
      {mensagemSucesso && (
        <div className="fixed top-4 right-4 z-50 animate-in slide-in-from-top duration-300">
          <div className="bg-green-50 border-2 border-green-500 rounded-lg px-6 py-3 shadow-lg flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-green-600" />
            <span className="text-green-800 font-medium">{mensagemSucesso}</span>
          </div>
        </div>
      )}

      {/* Header Melhorado */}
      <div className="bg-white border-b border-gray-200 -mx-6 -mt-6 px-6 py-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="p-2.5 hover:bg-gray-100 rounded-lg transition-all hover:scale-105 active:scale-95"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600" />
          </button>
          
          <div className="flex-1 min-w-0">
            {/* Nome editável */}
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
                  className="text-2xl font-bold border-b-2 border-blue-600 bg-transparent outline-none flex-1"
                  autoFocus
                  disabled={salvando}
                />
                <button 
                  onClick={salvarNome} 
                  className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                  disabled={salvando}
                >
                  <Check className="w-5 h-5" />
                </button>
                <button 
                  onClick={() => setEditandoNome(false)} 
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  disabled={salvando}
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2 group">
                <h1 className="text-2xl font-bold text-gray-900 truncate">
                  {lead.name || 'Lead sem nome'}
                </h1>
                <button
                  onClick={() => {
                    setNomeTemp(lead.name || '');
                    setEditandoNome(true);
                  }}
                  className="p-1.5 opacity-0 group-hover:opacity-100 hover:bg-gray-100 rounded transition-all"
                >
                  <Edit2 className="w-4 h-4 text-gray-400" />
                </button>
              </div>
            )}
            
            {/* Tags + Qualificação + Status */}
            <div className="flex items-center gap-2 mt-3 flex-wrap">
              {/* Tags customizadas */}
              {(lead.custom_data?.tags || []).map((tag: string) => (
                <Badge 
                  key={tag} 
                  variant="outline"
                  className="flex items-center gap-1.5 bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border-blue-200 font-medium px-3 py-1"
                >
                  <span className="text-base">🏷️</span>
                  {tag}
                  <button
                    onClick={() => removerTag(tag)}
                    className="hover:bg-blue-200 rounded-full p-0.5 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </Badge>
              ))}
              
              {/* Adicionar tag */}
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
                  className="border-2 border-blue-400 rounded-lg px-3 py-1 text-sm outline-none w-32"
                  placeholder="Nova tag"
                  autoFocus
                  disabled={salvando}
                />
              ) : (
                <button
                  onClick={() => setAdicionandoTag(true)}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:bg-blue-50 px-3 py-1 rounded-lg font-medium transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" /> Tag
                </button>
              )}
              
              <span className="text-gray-300">•</span>
              
              {/* Qualificação com ícone */}
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-gray-400" />
                <select
                  value={lead.qualification}
                  onChange={(e) => atualizarQualificacao(e.target.value)}
                  disabled={salvando}
                  className={`
                    border-2 rounded-lg px-3 py-1 text-sm font-semibold cursor-pointer outline-none transition-all
                    ${qualificationColors[lead.qualification as keyof typeof qualificationColors] || 'bg-gray-100 text-gray-700 border-gray-300'}
                  `}
                >
                  <option value="frio">❄️ Frio</option>
                  <option value="morno">🌤️ Morno</option>
                  <option value="quente">🔥 Quente</option>
                </select>
              </div>
              
              <span className="text-gray-300">•</span>
              
              {/* Status com ícone */}
              <div className="flex items-center gap-2">
                <Circle className="w-4 h-4 text-gray-400" />
                <select
                  value={lead.status}
                  onChange={(e) => atualizarStatus(e.target.value)}
                  disabled={salvando}
                  className="border-2 border-gray-200 bg-white rounded-lg px-3 py-1 text-sm font-medium text-gray-700 cursor-pointer outline-none hover:border-gray-300 transition-colors"
                >
                  <option value="new">Novo</option>
                  <option value="in_progress">Em Atendimento</option>
                  <option value="qualified">Qualificado</option>
                  <option value="handed_off">Transferido</option>
                  <option value="converted">Convertido</option>
                  <option value="lost">Perdido</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Layout Principal */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Coluna Esquerda */}
        <div className="lg:col-span-1 space-y-6 order-2 lg:order-1">
          
          {/* Card de Informações MELHORADO */}
          <Card className="shadow-sm hover:shadow-md transition-shadow">
            <CardHeader title={
              <div className="flex items-center gap-2">
                <User className="w-5 h-5 text-blue-600" />
                <span>Informações</span>
              </div>
            } />
            <div className="space-y-4 p-5 pt-0">
              {lead.phone && (
                <a 
                  href={`tel:${lead.phone}`}
                  className="flex items-center gap-3 p-3 -mx-3 rounded-xl hover:bg-gradient-to-r hover:from-green-50 hover:to-emerald-50 transition-all group border border-transparent hover:border-green-200"
                >
                  <div className="w-10 h-10 bg-gradient-to-br from-green-400 to-emerald-500 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm">
                    <Phone className="w-5 h-5 text-white" />
                  </div>
                  <span className="text-gray-700 group-hover:text-green-700 transition-colors font-medium truncate">
                    {lead.phone}
                  </span>
                </a>
              )}
              
              {lead.email && (
                <a 
                  href={`mailto:${lead.email}`}
                  className="flex items-center gap-3 p-3 -mx-3 rounded-xl hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 transition-all group border border-transparent hover:border-blue-200"
                >
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-indigo-500 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm">
                    <Mail className="w-5 h-5 text-white" />
                  </div>
                  <span className="text-gray-700 group-hover:text-blue-700 transition-colors font-medium truncate">
                    {lead.email}
                  </span>
                </a>
              )}
              
              {lead.city && (
                <div className="flex items-center gap-3 p-3 -mx-3 rounded-xl bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-100">
                  <div className="w-10 h-10 bg-gradient-to-br from-purple-400 to-pink-500 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm">
                    <MapPin className="w-5 h-5 text-white" />
                  </div>
                  <span className="text-gray-800 font-medium truncate">{lead.city}</span>
                </div>
              )}

              <div className="flex items-center gap-3 p-3 -mx-3 rounded-xl bg-gray-50 border border-gray-100">
                <div className="w-10 h-10 bg-gradient-to-br from-gray-400 to-gray-500 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm">
                  <Calendar className="w-5 h-5 text-white" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">Criado em</p>
                  <p className="text-gray-800 text-sm font-semibold">
                    {new Date(lead.created_at).toLocaleDateString('pt-BR', {
                      day: '2-digit', month: 'short', year: 'numeric',
                      hour: '2-digit', minute: '2-digit'
                    })}
                  </p>
                </div>
              </div>

              {/* Atribuir Vendedor MELHORADO */}
              <div className="border-t-2 border-gray-100 pt-5 mt-5">
                <label className="text-xs font-bold text-gray-500 uppercase tracking-wider block mb-3 flex items-center gap-2">
                  <UserPlus className="w-4 h-4" />
                  Vendedor Responsável
                </label>
                
                {lead.assigned_seller ? (
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300 rounded-xl p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center shadow-lg">
                          <User className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <p className="font-bold text-gray-900">{lead.assigned_seller.name}</p>
                          <p className="text-sm text-gray-600 flex items-center gap-1">
                            <Phone className="w-3 h-3" />
                            {lead.assigned_seller.whatsapp}
                          </p>
                        </div>
                      </div>
                      <button 
                        onClick={removerAtribuicao} 
                        className="text-red-600 text-sm font-medium hover:bg-red-100 px-3 py-1 rounded-lg transition-colors"
                        disabled={salvando}
                      >
                        Remover
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="relative">
                    <select
                      onChange={(e) => atribuirVendedor(parseInt(e.target.value))}
                      className="w-full border-2 border-gray-300 rounded-xl px-4 py-3 text-sm font-medium appearance-none cursor-pointer hover:border-blue-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all bg-white"
                      defaultValue=""
                      disabled={atribuindoVendedor}
                    >
                      <option value="" disabled>
                        {atribuindoVendedor ? '📲 Notificando vendedor...' : '👤 Selecione um vendedor...'}
                      </option>
                      {sellers.filter(s => s.active).map(seller => (
                        <option key={seller.id} value={seller.id}>
                          {seller.name} {seller.available ? '✅' : '⏸️'}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
                    
                    {atribuindoVendedor && (
                      <div className="absolute inset-0 bg-white/80 rounded-xl flex items-center justify-center">
                        <div className="flex items-center gap-2 text-blue-600">
                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div>
                          <span className="text-sm font-medium">Enviando notificação...</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                {!lead.assigned_seller && (
                  <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
                    <Send className="w-3 h-3" />
                    O vendedor será notificado automaticamente no WhatsApp
                  </p>
                )}
              </div>

              {/* Dados Adicionais */}
              {lead.custom_data && Object.entries(lead.custom_data)
                .filter(([key]) => !['notas', 'tags', 'imovel_portal', 'empreendimento_id', 'empreendimento_nome', 'contexto_ativo', 'primeira_mensagem'].includes(key))
                .length > 0 && (
                <div className="pt-5 mt-5 border-t-2 border-gray-100">
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">
                    Dados adicionais
                  </p>
                  <div className="space-y-2 bg-gray-50 rounded-xl p-3">
                    {Object.entries(lead.custom_data)
                      .filter(([key]) => !['notas', 'tags', 'imovel_portal', 'empreendimento_id', 'empreendimento_nome', 'contexto_ativo', 'primeira_mensagem'].includes(key))
                      .map(([key, value]) => (
                        <div key={key} className="flex justify-between items-start gap-2 text-sm">
                          <span className="text-gray-600 font-medium flex-shrink-0">{key}:</span>
                          <span className="text-gray-900 text-right font-semibold truncate">
                            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Timeline de Eventos MELHORADA */}
          {events.length > 0 && (
            <Card className="shadow-sm hover:shadow-md transition-shadow">
              <CardHeader title={
                <div className="flex items-center gap-2">
                  <History className="w-5 h-5 text-purple-600" />
                  <span>Histórico de Eventos</span>
                </div>
              } />
              <div className="p-5 pt-0">
                <div className="space-y-4">
                  {events.slice(0, 5).map((event, idx) => (
                    <div key={event.id} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-100 to-indigo-100 flex items-center justify-center flex-shrink-0 border-2 border-blue-200">
                          {getEventIcon(event.event_type)}
                        </div>
                        {idx < Math.min(events.length, 5) - 1 && (
                          <div className="w-0.5 h-full bg-gradient-to-b from-gray-200 to-transparent mt-1"></div>
                        )}
                      </div>
                      
                      <div className="flex-1 pb-4">
                        <p className="text-sm font-semibold text-gray-900 mb-1">
                          {event.description}
                        </p>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                            {new Date(event.created_at).toLocaleDateString('pt-BR', {
                              day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                            })}
                          </span>
                          {event.old_value && event.new_value && (
                            <span className="text-xs font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full">
                              {event.old_value} → {event.new_value}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}

          {/* Resumo IA MELHORADO */}
          {lead.summary && (
            <Card className="shadow-sm hover:shadow-md transition-shadow bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-100">
              <CardHeader title={
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-purple-600" />
                  <span className="text-purple-900">Resumo da IA</span>
                </div>
              } />
              <div className="p-5 pt-0">
                <p className="text-gray-700 text-sm leading-relaxed font-medium">
                  {lead.summary}
                </p>
              </div>
            </Card>
          )}

          {/* Notas Internas MELHORADAS */}
          <Card className="shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between p-5 pb-4">
              <h3 className="font-bold text-gray-900 flex items-center gap-2">
                <span className="text-2xl">📝</span>
                Notas Internas
              </h3>
              <button 
                onClick={() => setEditandoNota(true)} 
                className="flex items-center gap-1 text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-lg font-semibold transition-colors"
                disabled={salvando}
              >
                <Plus className="w-4 h-4" /> Nova
              </button>
            </div>
            
            <div className="px-5 pb-5 space-y-3">
              {(lead.custom_data?.notas || []).map((nota: any) => (
                <div key={nota.id} className="bg-gradient-to-r from-yellow-50 to-amber-50 border-l-4 border-yellow-400 p-4 rounded-lg shadow-sm">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-semibold text-gray-600 bg-white px-2 py-1 rounded-full">
                      {nota.created_by} • {new Date(nota.created_at).toLocaleDateString('pt-BR')}
                    </span>
                    <button 
                      onClick={() => deletarNota(nota.id)} 
                      className="text-red-600 hover:bg-red-100 p-1 rounded transition-colors"
                      disabled={salvando}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <p className="text-sm text-gray-800 font-medium leading-relaxed">{nota.content}</p>
                </div>
              ))}

              {editandoNota && (
                <div className="space-y-3 bg-white border-2 border-blue-200 rounded-xl p-4 shadow-sm">
                  <textarea
                    value={novaNota}
                    onChange={(e) => setNovaNota(e.target.value)}
                    placeholder="Digite sua nota aqui..."
                    className="w-full border-2 border-gray-200 rounded-lg p-3 text-sm font-medium focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none transition-all resize-none"
                    rows={4}
                    disabled={salvando}
                  />
                  <div className="flex gap-2">
                    <button 
                      onClick={salvarNota} 
                      className="flex-1 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-semibold hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md hover:shadow-lg disabled:opacity-50"
                      disabled={salvando || !novaNota.trim()}
                    >
                      {salvando ? 'Salvando...' : 'Salvar Nota'}
                    </button>
                    <button 
                      onClick={() => {setEditandoNota(false); setNovaNota('');}} 
                      className="px-4 py-2.5 border-2 border-gray-300 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
                      disabled={salvando}
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              )}
              
              {!editandoNota && (lead.custom_data?.notas || []).length === 0 && (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <span className="text-3xl">📝</span>
                  </div>
                  <p className="text-sm text-gray-500 font-medium">
                    Nenhuma nota ainda
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Clique em "Nova" para adicionar
                  </p>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Coluna Direita - Chat */}
        <div className="lg:col-span-2 order-1 lg:order-2">
          <Card className="flex flex-col h-[60vh] md:h-[70vh] lg:h-[calc(100vh-220px)] min-h-[500px] shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between p-5 border-b-2 border-gray-100 flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-md">
                  <MessageSquare className="w-5 h-5 text-white" />
                </div>
                <h3 className="font-bold text-gray-900 text-lg">Histórico da Conversa</h3>
              </div>
              <span className="text-xs font-bold text-gray-500 bg-gray-100 px-3 py-1.5 rounded-full">
                {messages.length} {messages.length === 1 ? 'mensagem' : 'mensagens'}
              </span>
            </div>

            <div
              ref={chatContainerRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto p-5 space-y-4 scroll-smooth bg-gradient-to-b from-gray-50 to-white"
              style={{ scrollbarWidth: 'thin', scrollbarColor: '#93C5FD transparent' }}
            >
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
                  <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center">
                    <MessageSquare className="w-10 h-10 opacity-50" />
                  </div>
                  <p className="font-semibold text-lg">Nenhuma mensagem ainda</p>
                  <p className="text-sm text-gray-400">Aguardando primeira interação do lead</p>
                </div>
              ) : (
                <>
                  {Array.from(messageGroups.entries()).map(([date, dateMessages]) => (
                    <div key={date}>
                      <div className="flex items-center justify-center my-6">
                        <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
                        <span className="px-4 py-1 text-xs font-bold text-gray-500 bg-white border-2 border-gray-200 rounded-full shadow-sm">
                          {formatDateLabel(date, dateMessages[0].created_at)}
                        </span>
                        <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
                      </div>

                      <div className="space-y-4">
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
                              {isAssistant && (
                                <div className={`flex-shrink-0 mr-3 ${showAvatar ? 'visible' : 'invisible'}`}>
                                  <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center shadow-lg ring-2 ring-purple-100">
                                    <Bot className="w-5 h-5 text-white" />
                                  </div>
                                </div>
                              )}

                              <div className={`
                                relative max-w-[85%] sm:max-w-[75%] px-5 py-3 rounded-2xl shadow-md
                                ${isAssistant 
                                  ? 'bg-white text-gray-800 rounded-tl-sm border-2 border-gray-100' 
                                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-tr-sm'
                                }
                              `}>
                                <p className="text-sm leading-relaxed whitespace-pre-wrap break-words font-medium">
                                  {msg.content}
                                </p>
                                
                                <div className={`flex items-center gap-1.5 mt-2 ${isAssistant ? 'text-gray-400' : 'text-blue-100'}`}>
                                  <Clock className="w-3.5 h-3.5" />
                                  <span className="text-xs font-semibold">
                                    {new Date(msg.created_at).toLocaleTimeString('pt-BR', {
                                      hour: '2-digit', minute: '2-digit'
                                    })}
                                  </span>
                                </div>

                                {hoveredMessage === msg.id && (
                                  <div className={`
                                    absolute -top-10 px-3 py-1.5 text-xs font-bold bg-gray-900 text-white rounded-lg
                                    whitespace-nowrap z-10 shadow-xl border border-gray-700
                                    ${isAssistant ? 'left-0' : 'right-0'}
                                  `}>
                                    {new Date(msg.created_at).toLocaleString('pt-BR')}
                                  </div>
                                )}
                              </div>

                              {!isAssistant && (
                                <div className={`flex-shrink-0 ml-3 ${showAvatar ? 'visible' : 'invisible'}`}>
                                  <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-full flex items-center justify-center shadow-lg ring-2 ring-blue-100">
                                    <User className="w-5 h-5 text-white" />
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
              <div className="absolute bottom-24 right-8">
                <button 
                  onClick={scrollToBottom} 
                  className="p-3 bg-white border-2 border-blue-300 rounded-full shadow-xl hover:bg-blue-50 transition-all hover:scale-110 active:scale-95"
                >
                  <ChevronDown className="w-5 h-5 text-blue-600" />
                </button>
              </div>
            )}

            <div className="p-4 border-t-2 border-gray-100 bg-gradient-to-r from-gray-50 to-blue-50 flex-shrink-0 rounded-b-xl">
              <p className="text-xs text-gray-500 text-center font-medium">
                💬 Conversa gerenciada automaticamente pela IA do Velaris
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}