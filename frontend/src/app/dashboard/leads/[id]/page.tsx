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
    case 'status_change': return <History className="w-3 h-3 text-blue-600" />;
    case 'qualification_change': return <Sparkles className="w-3 h-3 text-purple-600" />;
    case 'seller_assigned': return <UserPlus className="w-3 h-3 text-green-600" />;
    case 'seller_unassigned': return <X className="w-3 h-3 text-red-600" />;
    default: return <Clock className="w-3 h-3 text-gray-600" />;
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
    setTimeout(() => setMensagemSucesso(''), 2000);
  };

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
      mostrarSucesso('Nota adicionada!');
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
      mostrarSucesso('Nota excluída!');
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
      mostrarSucesso('Tag adicionada!');
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
      mostrarSucesso('Tag removida!');
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
      await assignSellerToLead(lead.id, sellerId);
      const leadAtualizado = await getLead(lead.id);
      setLead(leadAtualizado as Lead);
      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
      mostrarSucesso('✅ Vendedor notificado!');
    } catch (error) {
      alert('Erro ao atribuir vendedor');
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
      mostrarSucesso('Atribuição removida!');
    } catch (error) {
      alert('Erro ao remover atribuição');
    } finally {
      setSalvando(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-2">
          <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-600 border-t-transparent"></div>
          <span className="text-gray-500 text-sm">Carregando...</span>
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-3">
        <h3 className="text-lg font-semibold">Lead não encontrado</h3>
        <button onClick={() => router.back()} className="px-4 py-2 bg-blue-600 text-white rounded-lg">
          Voltar
        </button>
      </div>
    );
  }

  const messageGroups = groupMessagesByDate(messages);
  const qualificationColors = {
    quente: 'bg-red-100 text-red-700 border-red-300',
    hot: 'bg-red-100 text-red-700 border-red-300',
    morno: 'bg-orange-100 text-orange-700 border-orange-300',
    warm: 'bg-orange-100 text-orange-700 border-orange-300',
    frio: 'bg-blue-100 text-blue-700 border-blue-300',
    cold: 'bg-blue-100 text-blue-700 border-blue-300',
  };

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col">
      {/* Toast de Sucesso */}
      {mensagemSucesso && (
        <div className="fixed top-4 right-4 z-50 bg-green-50 border-2 border-green-500 rounded-lg px-4 py-2 shadow-lg flex items-center gap-2 animate-in slide-in-from-top">
          <CheckCircle2 className="w-4 h-4 text-green-600" />
          <span className="text-green-800 text-sm font-medium">{mensagemSucesso}</span>
        </div>
      )}

      {/* Header Compacto */}
      <div className="bg-white border-b border-gray-200 px-4 py-2 flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="p-1.5 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="w-5 h-5 text-gray-600" />
          </button>
          
          <div className="flex-1 min-w-0">
            {editandoNome ? (
              <div className="flex items-center gap-1">
                <input
                  type="text"
                  value={nomeTemp}
                  onChange={(e) => setNomeTemp(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') salvarNome();
                    if (e.key === 'Escape') setEditandoNome(false);
                  }}
                  className="text-lg font-bold border-b-2 border-blue-600 bg-transparent outline-none flex-1"
                  autoFocus
                />
                <button onClick={salvarNome} className="p-1 text-green-600"><Check className="w-4 h-4" /></button>
                <button onClick={() => setEditandoNome(false)} className="p-1 text-red-600"><X className="w-4 h-4" /></button>
              </div>
            ) : (
              <div className="flex items-center gap-1 group">
                <h1 className="text-lg font-bold text-gray-900 truncate">{lead.name || 'Lead sem nome'}</h1>
                <button onClick={() => { setNomeTemp(lead.name || ''); setEditandoNome(true); }} className="opacity-0 group-hover:opacity-100 p-1">
                  <Edit2 className="w-3 h-3 text-gray-400" />
                </button>
              </div>
            )}
            
            {/* Tags + Badges Compactos */}
            <div className="flex items-center gap-1.5 mt-1 flex-wrap text-xs">
              {(lead.custom_data?.tags || []).map((tag: string) => (
                <Badge key={tag} variant="outline" className="flex items-center gap-1 bg-blue-50 text-blue-700 border-blue-200 px-2 py-0.5">
                  🏷️ {tag}
                  <X className="w-2.5 h-2.5 cursor-pointer" onClick={() => removerTag(tag)} />
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
                  className="border border-blue-400 rounded px-2 py-0.5 text-xs w-20 outline-none"
                  placeholder="Tag"
                  autoFocus
                />
              ) : (
                <button onClick={() => setAdicionandoTag(true)} className="text-xs text-blue-600 hover:bg-blue-50 px-2 py-0.5 rounded">
                  + Tag
                </button>
              )}
              
              <span className="text-gray-300">•</span>
              
              <select
                value={lead.qualification}
                onChange={(e) => atualizarQualificacao(e.target.value)}
                className={`border rounded px-2 py-0.5 text-xs font-semibold cursor-pointer outline-none ${qualificationColors[lead.qualification as keyof typeof qualificationColors]}`}
              >
                <option value="frio">❄️ Frio</option>
                <option value="morno">🌤️ Morno</option>
                <option value="quente">🔥 Quente</option>
              </select>
              
              <span className="text-gray-300">•</span>
              
              <select
                value={lead.status}
                onChange={(e) => atualizarStatus(e.target.value)}
                className="border border-gray-200 bg-white rounded px-2 py-0.5 text-xs font-medium text-gray-700 cursor-pointer outline-none"
              >
                <option value="new">Novo</option>
                <option value="in_progress">Atendimento</option>
                <option value="qualified">Qualificado</option>
                <option value="handed_off">Transferido</option>
                <option value="converted">Convertido</option>
                <option value="lost">Perdido</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Layout Principal - Altura Fixa */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-3 p-3 overflow-hidden">
        
        {/* Coluna Esquerda - Scroll Interno */}
        <div className="lg:col-span-1 space-y-3 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 180px)' }}>
          
          {/* Card Informações Compacto */}
          <Card className="shadow-sm">
            <div className="p-3">
              <h3 className="font-bold text-sm mb-2 flex items-center gap-1">
                <User className="w-4 h-4 text-blue-600" />
                Informações
              </h3>
              <div className="space-y-2 text-xs">
                {lead.phone && (
                  <a href={`tel:${lead.phone}`} className="flex items-center gap-2 p-1.5 rounded hover:bg-green-50">
                    <div className="w-6 h-6 bg-green-500 rounded-lg flex items-center justify-center">
                      <Phone className="w-3 h-3 text-white" />
                    </div>
                    <span className="text-gray-700 font-medium">{lead.phone}</span>
                  </a>
                )}
                
                {lead.email && (
                  <a href={`mailto:${lead.email}`} className="flex items-center gap-2 p-1.5 rounded hover:bg-blue-50">
                    <div className="w-6 h-6 bg-blue-500 rounded-lg flex items-center justify-center">
                      <Mail className="w-3 h-3 text-white" />
                    </div>
                    <span className="text-gray-700 font-medium truncate">{lead.email}</span>
                  </a>
                )}
                
                {lead.city && (
                  <div className="flex items-center gap-2 p-1.5 bg-purple-50 rounded">
                    <div className="w-6 h-6 bg-purple-500 rounded-lg flex items-center justify-center">
                      <MapPin className="w-3 h-3 text-white" />
                    </div>
                    <span className="text-gray-800 font-medium">{lead.city}</span>
                  </div>
                )}

                <div className="flex items-center gap-2 p-1.5 bg-gray-50 rounded">
                  <div className="w-6 h-6 bg-gray-500 rounded-lg flex items-center justify-center">
                    <Calendar className="w-3 h-3 text-white" />
                  </div>
                  <div>
                    <p className="text-[10px] text-gray-500">Criado em</p>
                    <p className="text-gray-800 font-semibold">
                      {new Date(lead.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                    </p>
                  </div>
                </div>

                {/* Vendedor Compacto */}
                <div className="border-t pt-2 mt-2">
                  <label className="text-[10px] font-bold text-gray-500 uppercase block mb-1">
                    Vendedor
                  </label>
                  
                  {lead.assigned_seller ? (
                    <div className="bg-green-50 border border-green-300 rounded-lg p-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 bg-green-500 rounded-lg flex items-center justify-center">
                            <User className="w-3 h-3 text-white" />
                          </div>
                          <div>
                            <p className="font-bold text-gray-900 text-xs">{lead.assigned_seller.name}</p>
                            <p className="text-[10px] text-gray-600">{lead.assigned_seller.whatsapp}</p>
                          </div>
                        </div>
                        <button onClick={removerAtribuicao} className="text-red-600 text-[10px] hover:bg-red-100 px-1.5 py-0.5 rounded">
                          Remover
                        </button>
                      </div>
                    </div>
                  ) : (
                    <select
                      onChange={(e) => atribuirVendedor(parseInt(e.target.value))}
                      className="w-full border rounded-lg px-2 py-1.5 text-xs"
                      defaultValue=""
                      disabled={atribuindoVendedor}
                    >
                      <option value="" disabled>
                        {atribuindoVendedor ? '📲 Notificando...' : 'Selecione...'}
                      </option>
                      {sellers.filter(s => s.active).map(seller => (
                        <option key={seller.id} value={seller.id}>{seller.name}</option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
            </div>
          </Card>

          {/* Timeline Compacta */}
          {events.length > 0 && (
            <Card className="shadow-sm">
              <div className="p-3">
                <h3 className="font-bold text-sm mb-2 flex items-center gap-1">
                  <History className="w-4 h-4 text-purple-600" />
                  Eventos
                </h3>
                <div className="space-y-2 text-xs">
                  {events.slice(0, 3).map((event) => (
                    <div key={event.id} className="flex gap-2">
                      <div className="w-6 h-6 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
                        {getEventIcon(event.event_type)}
                      </div>
                      <div className="flex-1">
                        <p className="text-gray-900 font-medium">{event.description}</p>
                        <span className="text-[10px] text-gray-500">
                          {new Date(event.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}

          {/* Resumo IA Compacto */}
          {lead.summary && (
            <Card className="shadow-sm bg-purple-50 border border-purple-200">
              <div className="p-3">
                <h3 className="font-bold text-sm mb-1 flex items-center gap-1 text-purple-900">
                  <Sparkles className="w-4 h-4" />
                  Resumo IA
                </h3>
                <p className="text-gray-700 text-xs leading-relaxed">{lead.summary}</p>
              </div>
            </Card>
          )}

          {/* Notas Compactas */}
          <Card className="shadow-sm">
            <div className="p-3">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-bold text-sm">📝 Notas</h3>
                <button onClick={() => setEditandoNota(true)} className="text-xs text-blue-600 hover:bg-blue-50 px-2 py-0.5 rounded">
                  + Nova
                </button>
              </div>
              
              <div className="space-y-2">
                {(lead.custom_data?.notas || []).slice(0, 2).map((nota: any) => (
                  <div key={nota.id} className="bg-yellow-50 border-l-2 border-yellow-400 p-2 rounded text-xs">
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-[10px] text-gray-600">
                        {nota.created_by} • {new Date(nota.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                      </span>
                      <button onClick={() => deletarNota(nota.id)} className="text-red-600 text-[10px]">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                    <p className="text-gray-800">{nota.content}</p>
                  </div>
                ))}

                {editandoNota && (
                  <div className="space-y-2 border-2 border-blue-200 rounded-lg p-2">
                    <textarea
                      value={novaNota}
                      onChange={(e) => setNovaNota(e.target.value)}
                      placeholder="Nova nota..."
                      className="w-full border rounded p-2 text-xs resize-none"
                      rows={2}
                    />
                    <div className="flex gap-1">
                      <button onClick={salvarNota} className="flex-1 px-2 py-1 bg-blue-600 text-white rounded text-xs font-medium">
                        Salvar
                      </button>
                      <button onClick={() => {setEditandoNota(false); setNovaNota('');}} className="px-2 py-1 border rounded text-xs">
                        Cancelar
                      </button>
                    </div>
                  </div>
                )}
                
                {!editandoNota && (lead.custom_data?.notas || []).length === 0 && (
                  <p className="text-xs text-gray-400 text-center py-2">Sem notas</p>
                )}
              </div>
            </div>
          </Card>
        </div>

        {/* Chat - Altura Fixa */}
        <div className="lg:col-span-2">
          <Card className="h-full flex flex-col shadow-sm">
            <div className="flex items-center justify-between p-3 border-b flex-shrink-0">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-blue-600" />
                <h3 className="font-bold text-sm">Conversa</h3>
              </div>
              <span className="text-[10px] text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                {messages.length} msgs
              </span>
            </div>

            <div
              ref={chatContainerRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto p-3 space-y-2 bg-gray-50"
            >
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-400">
                  <MessageSquare className="w-8 h-8 mb-2 opacity-50" />
                  <p className="text-sm">Sem mensagens</p>
                </div>
              ) : (
                <>
                  {Array.from(messageGroups.entries()).map(([date, dateMessages]) => (
                    <div key={date}>
                      <div className="flex items-center justify-center my-3">
                        <span className="px-3 py-0.5 text-[10px] font-bold text-gray-500 bg-white border rounded-full">
                          {formatDateLabel(date, dateMessages[0].created_at)}
                        </span>
                      </div>

                      <div className="space-y-2">
                        {dateMessages.map((msg, idx) => {
                          const isAssistant = msg.role === 'assistant';
                          const showAvatar = idx === 0 || dateMessages[idx - 1]?.role !== msg.role;
                          
                          return (
                            <div key={msg.id} className={`flex ${isAssistant ? 'justify-start' : 'justify-end'}`}>
                              {isAssistant && (
                                <div className={`flex-shrink-0 mr-2 ${showAvatar ? 'visible' : 'invisible'}`}>
                                  <div className="w-6 h-6 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
                                    <Bot className="w-3 h-3 text-white" />
                                  </div>
                                </div>
                              )}

                              <div className={`max-w-[75%] px-3 py-1.5 rounded-lg text-xs ${isAssistant ? 'bg-white text-gray-800 border' : 'bg-blue-600 text-white'}`}>
                                <p className="leading-relaxed">{msg.content}</p>
                                <span className={`text-[10px] ${isAssistant ? 'text-gray-400' : 'text-blue-100'}`}>
                                  {new Date(msg.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>

                              {!isAssistant && (
                                <div className={`flex-shrink-0 ml-2 ${showAvatar ? 'visible' : 'invisible'}`}>
                                  <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center">
                                    <User className="w-3 h-3 text-white" />
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
              <div className="absolute bottom-16 right-6">
                <button onClick={scrollToBottom} className="p-2 bg-white border rounded-full shadow-lg">
                  <ChevronDown className="w-4 h-4 text-blue-600" />
                </button>
              </div>
            )}

            <div className="p-2 border-t bg-gray-50 flex-shrink-0">
              <p className="text-[10px] text-gray-400 text-center">
                💬 Gerenciado pela IA vellarys
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}