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
  updateLeadCustomData
} from '@/lib/api';
import { getSellers } from '@/lib/sellers';
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
  History
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

// Helper para agrupar mensagens por data
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

  // ===============================================
  // FUNÇÕES DE ATUALIZAÇÃO
  // ===============================================

  const atualizarQualificacao = async (novaQualificacao: string) => {
    if (!lead) return;
    
    try {
      await updateLead(lead.id, { qualification: novaQualificacao });
      setLead({ ...lead, qualification: novaQualificacao });
      
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
    } catch (error) {
      console.error('Erro ao atualizar qualificação:', error);
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
    } catch (error) {
      console.error('Erro ao atualizar status:', error);
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
    } catch (error) {
      console.error('Erro ao salvar nome:', error);
      alert('Erro ao salvar nome');
    }
  };

  // ===============================================
  // FUNÇÕES DE NOTAS
  // ===============================================

  const salvarNota = async () => {
    if (!lead || !novaNota.trim()) return;
    
    try {
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
    } catch (error) {
      console.error('Erro ao salvar nota:', error);
      alert('Erro ao salvar nota');
    }
  };

  const deletarNota = async (notaId: number) => {
    if (!lead || !confirm('Tem certeza que deseja excluir esta nota?')) return;
    
    try {
      const notasAtuais = lead.custom_data?.notas || [];
      const notasFiltradas = notasAtuais.filter((n: any) => n.id !== notaId);
      
      const customDataAtualizado = {
        ...lead.custom_data,
        notas: notasFiltradas,
      };
      
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
    } catch (error) {
      console.error('Erro ao deletar nota:', error);
      alert('Erro ao deletar nota');
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
    } catch (error) {
      console.error('Erro ao adicionar tag:', error);
      alert('Erro ao adicionar tag');
    }
  };

  const removerTag = async (tag: string) => {
    if (!lead) return;
    
    try {
      const tagsAtuais = lead.custom_data?.tags || [];
      const tagsFiltradas = tagsAtuais.filter((t: string) => t !== tag);
      
      const customDataAtualizado = {
        ...lead.custom_data,
        tags: tagsFiltradas,
      };
      
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
    } catch (error) {
      console.error('Erro ao remover tag:', error);
      alert('Erro ao remover tag');
    }
  };

  // ===============================================
  // FUNÇÕES DE VENDEDOR
  // ===============================================

  const atribuirVendedor = async (sellerId: number) => {
    if (!lead || !sellerId) return;
    
    try {
      await assignSellerToLead(lead.id, sellerId);
      
      const leadAtualizado = await getLead(lead.id);
      setLead(leadAtualizado as Lead);
      
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
    } catch (error) {
      console.error('Erro ao atribuir vendedor:', error);
      alert('Erro ao atribuir vendedor');
    }
  };

  const removerAtribuicao = async () => {
    if (!lead || !confirm('Tem certeza que deseja remover a atribuição?')) return;
    
    try {
      await unassignSellerFromLead(lead.id);
      setLead({ ...lead, assigned_seller: null });
      
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
    } catch (error) {
      console.error('Erro ao remover atribuição:', error);
      alert('Erro ao remover atribuição');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="text-gray-500 text-sm">Carregando conversa...</span>
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-4">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
          <User className="w-8 h-8 text-gray-400" />
        </div>
        <p className="text-gray-500">Lead não encontrado</p>
        <button onClick={() => router.back()} className="text-blue-600 hover:underline text-sm">
          Voltar
        </button>
      </div>
    );
  }

  const qualificationLabels: Record<string, string> = {
    hot: 'QUENTE', warm: 'MORNO', cold: 'FRIO',
    quente: 'QUENTE', morno: 'MORNO', frio: 'FRIO'
  };

  const statusLabels: Record<string, string> = {
    novo: 'Novo', new: 'Novo',
    em_atendimento: 'Em Atendimento', in_progress: 'Em Atendimento',
    qualificado: 'Qualificado', qualified: 'Qualificado',
    transferido: 'Transferido', handed_off: 'Transferido',
    convertido: 'Convertido', converted: 'Convertido',
    perdido: 'Perdido', lost: 'Perdido'
  };

  const messageGroups = groupMessagesByDate(messages);

  return (
    <div className="space-y-4 md:space-y-6 pb-4">
      {/* Header */}
      <div className="flex items-center gap-3 md:gap-4">
        <button onClick={() => router.back()} className="p-2 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0">
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
                className="text-xl md:text-2xl font-bold border-b-2 border-blue-600 bg-transparent outline-none flex-1"
                autoFocus
              />
              <button onClick={salvarNome} className="text-green-600">
                <Check className="w-5 h-5" />
              </button>
              <button onClick={() => setEditandoNome(false)} className="text-red-600">
                <X className="w-5 h-5" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 group">
              <h1 className="text-xl md:text-2xl font-bold text-gray-900 truncate">
                {lead.name || 'Lead sem nome'}
              </h1>
              <button
                onClick={() => {
                  setNomeTemp(lead.name || '');
                  setEditandoNome(true);
                }}
                className="opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Edit2 className="w-4 h-4 text-gray-400" />
              </button>
            </div>
          )}
          
          {/* Tags + Badges */}
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {/* Tags customizadas */}
            {(lead.custom_data?.tags || []).map((tag: string) => (
              <Badge key={tag} variant="outline" className="flex items-center gap-1 bg-blue-50 text-blue-700 border-blue-200">
                🏷️ {tag}
                <X className="w-3 h-3 cursor-pointer hover:text-red-600" onClick={() => removerTag(tag)} />
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
                className="border border-blue-300 rounded px-2 py-0.5 text-sm w-24 outline-none"
                placeholder="Nova tag"
                autoFocus
              />
            ) : (
              <button onClick={() => setAdicionandoTag(true)} className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                <Plus className="w-3 h-3" /> Tag
              </button>
            )}
            
            <span className="text-gray-400 hidden sm:inline">•</span>
            
            {/* Qualificação editável */}
            <select
              value={lead.qualification}
              onChange={(e) => atualizarQualificacao(e.target.value)}
              className="border-none bg-transparent text-sm font-medium cursor-pointer outline-none"
              style={{
                color: lead.qualification === 'quente' || lead.qualification === 'hot' ? '#dc2626' :
                       lead.qualification === 'morno' || lead.qualification === 'warm' ? '#f59e0b' : '#3b82f6'
              }}
            >
              <option value="frio">❄️ Frio</option>
              <option value="morno">🌤️ Morno</option>
              <option value="quente">🔥 Quente</option>
            </select>
            
            <span className="text-gray-400 hidden sm:inline">•</span>
            
            {/* Status editável */}
            <select
              value={lead.status}
              onChange={(e) => atualizarStatus(e.target.value)}
              className="border-none bg-transparent text-gray-500 text-sm cursor-pointer outline-none"
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

      {/* Layout Principal */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        
        {/* Coluna Esquerda */}
        <div className="lg:col-span-1 space-y-4 order-2 lg:order-1">
          
          {/* Card de Informações */}
          <Card>
            <CardHeader title="Informações" />
            <div className="space-y-3 p-4 pt-0">
              {lead.phone && (
                <a href={`tel:${lead.phone}`} className="flex items-center gap-3 p-2 -mx-2 rounded-lg hover:bg-gray-50 transition-colors group">
                  <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <Phone className="w-4 h-4 text-green-600" />
                  </div>
                  <span className="text-gray-700 group-hover:text-green-600 transition-colors truncate">
                    {lead.phone}
                  </span>
                </a>
              )}
              
              {lead.email && (
                <a href={`mailto:${lead.email}`} className="flex items-center gap-3 p-2 -mx-2 rounded-lg hover:bg-gray-50 transition-colors group">
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <Mail className="w-4 h-4 text-blue-600" />
                  </div>
                  <span className="text-gray-700 group-hover:text-blue-600 transition-colors truncate">
                    {lead.email}
                  </span>
                </a>
              )}
              
              {lead.city && (
                <div className="flex items-center gap-3 p-2 -mx-2">
                  <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <MapPin className="w-4 h-4 text-purple-600" />
                  </div>
                  <span className="text-gray-700 truncate">{lead.city}</span>
                </div>
              )}

              <div className="flex items-center gap-3 p-2 -mx-2">
                <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <Calendar className="w-4 h-4 text-gray-500" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-gray-400">Criado em</p>
                  <p className="text-gray-700 text-sm">
                    {new Date(lead.created_at).toLocaleDateString('pt-BR', {
                      day: '2-digit', month: 'short', year: 'numeric',
                      hour: '2-digit', minute: '2-digit'
                    })}
                  </p>
                </div>
              </div>

              {/* Atribuir Vendedor */}
              <div className="border-t border-gray-100 pt-4 mt-4">
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider block mb-2">
                  Vendedor
                </label>
                
                {lead.assigned_seller ? (
                  <div className="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg p-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                        <User className="w-4 h-4 text-white" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{lead.assigned_seller.name}</p>
                        <p className="text-xs text-gray-500">{lead.assigned_seller.whatsapp}</p>
                      </div>
                    </div>
                    <button onClick={removerAtribuicao} className="text-red-600 text-sm hover:underline">
                      Remover
                    </button>
                  </div>
                ) : (
                  <select
                    onChange={(e) => atribuirVendedor(parseInt(e.target.value))}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    defaultValue=""
                  >
                    <option value="" disabled>Selecione um vendedor...</option>
                    {sellers.map(seller => (
                      <option key={seller.id} value={seller.id}>
                        {seller.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Dados Adicionais */}
              {lead.custom_data && Object.entries(lead.custom_data)
                .filter(([key]) => !['notas', 'tags', 'imovel_portal', 'empreendimento_id', 'empreendimento_nome', 'contexto_ativo', 'primeira_mensagem'].includes(key))
                .length > 0 && (
                <div className="pt-3 mt-3 border-t border-gray-100">
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
                    Dados adicionais
                  </p>
                  <div className="space-y-2">
                    {Object.entries(lead.custom_data)
                      .filter(([key]) => !['notas', 'tags', 'imovel_portal', 'empreendimento_id', 'empreendimento_nome', 'contexto_ativo', 'primeira_mensagem'].includes(key))
                      .map(([key, value]) => (
                        <div key={key} className="flex justify-between items-start gap-2 text-sm py-1">
                          <span className="text-gray-500 flex-shrink-0">{key}:</span>
                          <span className="text-gray-900 text-right truncate">
                            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Timeline de Eventos */}
          {events.length > 0 && (
            <Card>
              <CardHeader title="📜 Histórico de Eventos" />
              <div className="p-4">
                <div className="space-y-3">
                  {events.slice(0, 5).map((event, idx) => (
                    <div key={event.id} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                          {getEventIcon(event.event_type)}
                        </div>
                        {idx < events.length - 1 && (
                          <div className="w-0.5 h-full bg-gray-200 mt-1"></div>
                        )}
                      </div>
                      
                      <div className="flex-1 pb-4">
                        <p className="text-sm font-medium text-gray-900">
                          {event.description}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-gray-500">
                            {new Date(event.created_at).toLocaleDateString('pt-BR', {
                              day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                            })}
                          </span>
                          {event.old_value && event.new_value && (
                            <span className="text-xs text-gray-400">
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

          {/* Resumo IA */}
          {lead.summary && (
            <Card>
              <CardHeader title={
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-500" />
                  <span>Resumo da IA</span>
                </div>
              } />
              <div className="p-4 pt-0">
                <p className="text-gray-600 text-sm leading-relaxed">
                  {lead.summary}
                </p>
              </div>
            </Card>
          )}

          {/* Notas Internas */}
          <Card>
            <div className="flex items-center justify-between p-4 pb-3">
              <h3 className="font-semibold text-gray-900">📝 Notas Internas</h3>
              <button onClick={() => setEditandoNota(true)} className="text-sm text-blue-600 hover:underline">
                + Nova Nota
              </button>
            </div>
            
            <div className="px-4 pb-4 space-y-3">
              {(lead.custom_data?.notas || []).map((nota: any) => (
                <div key={nota.id} className="bg-yellow-50 border-l-4 border-yellow-400 p-3 rounded">
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs text-gray-500">
                      {nota.created_by} • {new Date(nota.created_at).toLocaleDateString('pt-BR')}
                    </span>
                    <button onClick={() => deletarNota(nota.id)} className="text-red-500 text-xs hover:underline">
                      Excluir
                    </button>
                  </div>
                  <p className="text-sm text-gray-700">{nota.content}</p>
                </div>
              ))}

              {editandoNota && (
                <div className="space-y-2">
                  <textarea
                    value={novaNota}
                    onChange={(e) => setNovaNota(e.target.value)}
                    placeholder="Digite sua nota..."
                    className="w-full border rounded-lg p-3 text-sm"
                    rows={3}
                  />
                  <div className="flex gap-2">
                    <button onClick={salvarNota} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">
                      Salvar
                    </button>
                    <button onClick={() => {setEditandoNota(false); setNovaNota('');}} className="px-4 py-2 border rounded-lg text-sm">
                      Cancelar
                    </button>
                  </div>
                </div>
              )}
              
              {!editandoNota && (lead.custom_data?.notas || []).length === 0 && (
                <p className="text-sm text-gray-400 text-center py-2">
                  Nenhuma nota ainda
                </p>
              )}
            </div>
          </Card>
        </div>

        {/* Coluna Direita - Chat */}
        <div className="lg:col-span-2 order-1 lg:order-2">
          <Card className="flex flex-col h-[60vh] md:h-[70vh] lg:h-[calc(100vh-220px)] min-h-[400px]">
            <div className="flex items-center justify-between p-4 border-b border-gray-100 flex-shrink-0">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-gray-400" />
                <h3 className="font-semibold text-gray-900">Histórico da Conversa</h3>
              </div>
              <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
                {messages.length} {messages.length === 1 ? 'mensagem' : 'mensagens'}
              </span>
            </div>

            <div
              ref={chatContainerRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth"
              style={{ scrollbarWidth: 'thin', scrollbarColor: '#E5E7EB transparent' }}
            >
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
                  <MessageSquare className="w-12 h-12 opacity-50" />
                  <p>Nenhuma mensagem ainda</p>
                </div>
              ) : (
                <>
                  {Array.from(messageGroups.entries()).map(([date, dateMessages]) => (
                    <div key={date}>
                      <div className="flex items-center justify-center my-4">
                        <div className="flex-1 h-px bg-gray-200"></div>
                        <span className="px-3 text-xs text-gray-400 bg-white">
                          {formatDateLabel(date, dateMessages[0].created_at)}
                        </span>
                        <div className="flex-1 h-px bg-gray-200"></div>
                      </div>

                      <div className="space-y-3">
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
                                <div className={`flex-shrink-0 mr-2 ${showAvatar ? 'visible' : 'invisible'}`}>
                                  <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center shadow-sm">
                                    <Bot className="w-4 h-4 text-white" />
                                  </div>
                                </div>
                              )}

                              <div className={`relative max-w-[85%] sm:max-w-[75%] px-4 py-2.5 rounded-2xl ${isAssistant ? 'bg-gray-100 text-gray-800 rounded-tl-md' : 'bg-blue-600 text-white rounded-tr-md'}`}>
                                <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                                  {msg.content}
                                </p>
                                
                                <div className={`flex items-center gap-1 mt-1 ${isAssistant ? 'text-gray-400' : 'text-blue-200'}`}>
                                  <Clock className="w-3 h-3" />
                                  <span className="text-xs">
                                    {new Date(msg.created_at).toLocaleTimeString('pt-BR', {
                                      hour: '2-digit', minute: '2-digit'
                                    })}
                                  </span>
                                </div>

                                {hoveredMessage === msg.id && (
                                  <div className={`absolute -top-8 px-2 py-1 text-xs bg-gray-900 text-white rounded whitespace-nowrap z-10 shadow-lg ${isAssistant ? 'left-0' : 'right-0'}`}>
                                    {new Date(msg.created_at).toLocaleString('pt-BR')}
                                  </div>
                                )}
                              </div>

                              {!isAssistant && (
                                <div className={`flex-shrink-0 ml-2 ${showAvatar ? 'visible' : 'invisible'}`}>
                                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center shadow-sm">
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
                <button onClick={scrollToBottom} className="p-2 bg-white border border-gray-200 rounded-full shadow-lg hover:bg-gray-50 transition-all hover:scale-105">
                  <ChevronDown className="w-5 h-5 text-gray-600" />
                </button>
              </div>
            )}

            <div className="p-3 border-t border-gray-100 bg-gray-50/50 flex-shrink-0 rounded-b-xl">
              <p className="text-xs text-gray-400 text-center">
                Conversa gerenciada pela IA do Velaris
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}