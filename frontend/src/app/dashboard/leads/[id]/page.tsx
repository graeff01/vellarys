'use client';

/**
 * LEAD DETAIL PAGE (v2)
 * =====================
 *
 * Página de detalhes do lead com sistema de widgets customizáveis.
 * Usa o mesmo sistema de drag-and-drop do dashboard principal.
 */

import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Badge } from '@/components/ui/badge';
import {
  getLead,
  getLeadMessages,
  updateLead,
  getLeadEvents,
  unassignSellerFromLead,
  updateLeadCustomData,
  getSellers,
  getLeadOpportunities,
  getLeadPageConfig,
  updateLeadPageConfig,
  Opportunity,
  WidgetConfig,
} from '@/lib/api';
import { assignAndHandoff } from '@/lib/handoff';
import {
  ArrowLeft,
  ChevronDown,
  Edit2,
  X,
  CheckCircle2,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { DraggableGrid, GridWidget } from '@/components/dashboard/draggable-grid';
import { LeadWidgetRenderer } from '@/components/lead-page';
import { getDefaultLeadPageLayout, getLeadWidgetsByCategory, CATEGORY_LABELS, CATEGORY_COLORS, LeadWidgetMeta } from '@/components/lead-page/lead-widget-registry';

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

// =============================================
// HELPERS
// =============================================

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

// =============================================
// WIDGET CATALOG MODAL
// =============================================

interface WidgetCatalogModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectWidget: (widgetId: string) => void;
  existingWidgetTypes: string[];
}

function WidgetCatalogModal({ isOpen, onClose, onSelectWidget, existingWidgetTypes }: WidgetCatalogModalProps) {
  if (!isOpen) return null;

  const widgetsByCategory = getLeadWidgetsByCategory();

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">Adicionar Widget</h2>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {(Object.keys(widgetsByCategory) as (keyof typeof widgetsByCategory)[]).map((category) => {
            const widgets = widgetsByCategory[category];
            if (!widgets || widgets.length === 0) return null;

            const colors = CATEGORY_COLORS[category];

            return (
              <div key={category} className="mb-6">
                <h3 className={`text-xs font-bold uppercase tracking-wider mb-3 ${colors.text}`}>
                  {CATEGORY_LABELS[category]}
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  {widgets.map((widget: LeadWidgetMeta) => {
                    const Icon = widget.icon;
                    const alreadyAdded = existingWidgetTypes.includes(widget.id);

                    return (
                      <button
                        key={widget.id}
                        onClick={() => {
                          if (!alreadyAdded) {
                            onSelectWidget(widget.id);
                            onClose();
                          }
                        }}
                        disabled={alreadyAdded}
                        className={`
                          p-4 rounded-xl border-2 text-left transition-all
                          ${alreadyAdded
                            ? 'border-slate-200 bg-slate-50 opacity-50 cursor-not-allowed'
                            : `${colors.border} ${colors.bg} hover:shadow-lg hover:scale-[1.02] cursor-pointer`
                          }
                        `}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${widget.previewBg || 'bg-slate-200'}`}>
                            <Icon className="w-5 h-5 text-white" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-bold text-slate-900 text-sm">{widget.name}</p>
                            <p className="text-xs text-slate-500 mt-0.5">{widget.description}</p>
                            {alreadyAdded && (
                              <p className="text-xs text-slate-400 mt-1 italic">Já adicionado</p>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// =============================================
// MAIN COMPONENT
// =============================================

export default function LeadDetailPage() {
  const params = useParams();
  const router = useRouter();

  // Data states
  const [lead, setLead] = useState<Lead | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [events, setEvents] = useState<LeadEvent[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);

  // Layout states
  const [widgets, setWidgets] = useState<GridWidget[]>([]);
  const [originalWidgets, setOriginalWidgets] = useState<GridWidget[]>([]);
  const [editMode, setEditMode] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showCatalog, setShowCatalog] = useState(false);

  // UI states
  const [mensagemSucesso, setMensagemSucesso] = useState('');
  const [editandoNome, setEditandoNome] = useState(false);
  const [nomeTemp, setNomeTemp] = useState('');
  const [adicionandoTag, setAdicionandoTag] = useState(false);
  const [novaTag, setNovaTag] = useState('');
  const [atribuindoVendedor, setAtribuindoVendedor] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // =============================================
  // DATA LOADING
  // =============================================

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [leadData, messagesData, eventsData, sellersData, oppsData, layoutConfig] = await Promise.all([
          getLead(Number(params.id)),
          getLeadMessages(Number(params.id)),
          getLeadEvents(Number(params.id)).catch(() => []),
          getSellers().catch(() => ({ sellers: [] })),
          getLeadOpportunities(Number(params.id)).catch(() => []),
          getLeadPageConfig().catch(() => ({ widgets: getDefaultLeadPageLayout(), is_default: true })),
        ]);

        setLead(leadData as Lead);
        setMessages(messagesData as Message[]);
        setEvents(eventsData as LeadEvent[]);
        setSellers((sellersData as { sellers: Seller[] }).sellers || []);
        setOpportunities(oppsData as Opportunity[]);

        // Load widgets from config or use default
        const widgetConfig = layoutConfig.widgets?.length > 0
          ? layoutConfig.widgets.map((w: any) => ({
              i: w.i || w.id,
              type: w.type,
              x: w.x ?? 0,
              y: w.y ?? 0,
              w: w.w ?? 4,
              h: w.h ?? 2,
              minW: w.minW ?? 2,
              maxW: w.maxW ?? 12,
              minH: w.minH ?? 1,
              maxH: w.maxH ?? 8,
            }))
          : getDefaultLeadPageLayout();

        setWidgets(widgetConfig);
        setOriginalWidgets(JSON.parse(JSON.stringify(widgetConfig)));
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

  // =============================================
  // LAYOUT HANDLERS
  // =============================================

  const handleLayoutChange = useCallback((newWidgets: GridWidget[]) => {
    setWidgets(newWidgets);
    setHasChanges(JSON.stringify(newWidgets) !== JSON.stringify(originalWidgets));
  }, [originalWidgets]);

  const handleRemoveWidget = useCallback((widgetId: string) => {
    const updated = widgets.filter(w => w.i !== widgetId);
    setWidgets(updated);
    setHasChanges(true);
  }, [widgets]);

  const handleAddWidget = useCallback((widgetId: string) => {
    const maxY = widgets.reduce((max, w) => Math.max(max, w.y + w.h), 0);
    const newWidget: GridWidget = {
      i: `${widgetId}_${Date.now()}`,
      type: widgetId,
      x: 0,
      y: maxY,
      w: 4,
      h: 3,
      minW: 2,
      maxW: 12,
      minH: 1,
      maxH: 8,
    };
    setWidgets([...widgets, newWidget]);
    setHasChanges(true);
  }, [widgets]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const configWidgets: WidgetConfig[] = widgets.map(w => ({
        id: w.i,
        type: w.type,
        enabled: true,
        position: 0,
        size: 'full',
        i: w.i,
        x: w.x,
        y: w.y,
        w: w.w,
        h: w.h,
        minW: w.minW,
        maxW: w.maxW,
        minH: w.minH,
        maxH: w.maxH,
      }));

      await updateLeadPageConfig(configWidgets, { layout_version: 'v2' });
      setOriginalWidgets(JSON.parse(JSON.stringify(widgets)));
      setHasChanges(false);
      setEditMode(false);
      mostrarSucesso('Layout salvo!');
    } catch (error) {
      console.error('Erro ao salvar layout:', error);
    } finally {
      setSaving(false);
    }
  }, [widgets]);

  const handleReset = useCallback(() => {
    if (confirm('Restaurar layout padrão?')) {
      const defaultLayout = getDefaultLeadPageLayout();
      setWidgets(defaultLayout);
      setHasChanges(true);
    }
  }, []);

  // =============================================
  // LEAD HANDLERS
  // =============================================

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

    // Encontrar o vendedor selecionado para update otimista
    const selectedSeller = sellers.find(s => s.id === sellerId);
    if (!selectedSeller) return;

    try {
      setAtribuindoVendedor(true);

      // Chamada API com notificação (Handoff)
      await assignAndHandoff(lead.id, sellerId, {
        notifySeller: true,
        notes: 'Atribuição manual via painel do lead'
      });

      // Update Otimista
      setLead(prev => prev ? ({
        ...prev,
        status: 'in_progress',
        assigned_seller: {
          id: selectedSeller.id,
          name: selectedSeller.name,
          whatsapp: selectedSeller.whatsapp
        }
      }) : null);

      // Atualiza eventos em background
      getLeadEvents(lead.id).then(events => setEvents(events as LeadEvent[]));

      mostrarSucesso(`Lead atribuído para ${selectedSeller.name} (Notificação enviada)`);
    } catch (error) {
      console.error(error);
      alert('Erro ao atribuir vendedor. Verifique se o backend está rodando.');
    } finally {
      setAtribuindoVendedor(false);
    }
  };

  const removerAtribuicao = async () => {
    if (!lead || !confirm('Remover atribuição?')) return;
    try {
      await unassignSellerFromLead(lead.id);

      // Update otimista
      setLead(prev => prev ? ({ ...prev, assigned_seller: null }) : null);

      const novosEventos = await getLeadEvents(lead.id);
      setEvents(novosEventos as LeadEvent[]);
      mostrarSucesso('Atribuição removida');
    } catch {
      alert('Erro ao remover atribuição');
    }
  };

  const adicionarNota = async (content: string) => {
    if (!lead) return;
    try {
      const notasAtuais: Note[] = lead.custom_data?.notas || [];
      const novaNota: Note = {
        id: Date.now(),
        content,
        created_by: 'Usuário',
        created_at: new Date().toISOString(),
      };
      const customDataAtualizado = { ...lead.custom_data, notas: [...notasAtuais, novaNota] };
      await updateLeadCustomData(lead.id, customDataAtualizado);
      setLead({ ...lead, custom_data: customDataAtualizado });
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

  const reloadOpportunities = async () => {
    if (!lead) return;
    try {
      const opps = await getLeadOpportunities(lead.id);
      setOpportunities(opps);
    } catch (error) {
      console.error('Erro ao recarregar oportunidades:', error);
    }
  };

  // =============================================
  // RENDER
  // =============================================

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

  const qualBadge = getQualificationBadge(lead.qualification);
  const statusBadge = getStatusBadge(lead.status);
  const existingWidgetTypes = widgets.map(w => w.type);

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Toast de Sucesso */}
      {mensagemSucesso && (
        <div className="fixed top-4 right-4 z-50 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl px-6 py-3 shadow-2xl flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-white" />
            <span className="text-sm font-semibold text-white">{mensagemSucesso}</span>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="bg-white/80 backdrop-blur-xl border-b border-slate-200/50 shadow-sm flex-shrink-0">
        <div className="px-6 py-3.5">
          <div className="flex items-center justify-between gap-4">
            {/* Esquerda - Voltar + Nome + Tags */}
            <div className="flex items-center gap-4 min-w-0 flex-1">
              <button
                onClick={() => router.back()}
                className="p-2 hover:bg-slate-100 rounded-xl transition-all hover:scale-105 active:scale-95 flex-shrink-0 group"
              >
                <ArrowLeft className="w-5 h-5 text-slate-600 group-hover:text-slate-900" />
              </button>

              <div className="min-w-0 flex-1">
                {editandoNome ? (
                  <input
                    type="text"
                    value={nomeTemp}
                    onChange={(e) => setNomeTemp(e.target.value)}
                    onBlur={salvarNome}
                    onKeyDown={(e) => e.key === 'Enter' && salvarNome()}
                    className="text-xl font-bold text-slate-900 w-full border-b-2 border-blue-500 outline-none bg-transparent"
                    autoFocus
                  />
                ) : (
                  <div className="flex items-center gap-2 group cursor-pointer" onClick={() => { setNomeTemp(lead.name || ''); setEditandoNome(true); }}>
                    <h1 className="text-xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent truncate">
                      {lead.name || 'Lead sem nome'}
                    </h1>
                    <Edit2 className="w-4 h-4 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                  </div>
                )}

                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {(lead.custom_data?.tags || []).map((tag: string) => (
                    <Badge key={tag} className="bg-gradient-to-r from-slate-100 to-slate-200 text-slate-700 border-0 px-2.5 py-0.5 text-xs font-semibold rounded-full hover:from-slate-200 hover:to-slate-300 transition-all shadow-sm">
                      {tag}
                      <button onClick={(e) => { e.stopPropagation(); removerTag(tag); }} className="ml-1.5 hover:text-red-600 transition-colors">
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
                      className="border border-slate-300 rounded-full px-3 py-0.5 text-xs w-28 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                      autoFocus
                    />
                  ) : (
                    <button onClick={() => setAdicionandoTag(true)} className="text-xs font-semibold text-slate-500 hover:text-slate-900 px-2.5 py-0.5 border border-dashed border-slate-300 rounded-full hover:border-slate-400 transition-all hover:bg-white flex items-center gap-1">
                      <Sparkles className="w-3 h-3" />
                      Tag
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Direita - Status e Qualificação */}
            <div className="flex items-center gap-2.5 flex-shrink-0">
              <div className="relative">
                <select
                  value={lead.status}
                  onChange={(e) => atualizarStatus(e.target.value)}
                  className={`${statusBadge.bg} ${statusBadge.text} px-4 py-2 rounded-xl font-bold text-sm cursor-pointer border-0 appearance-none pr-9 shadow-lg hover:shadow-xl transition-all`}
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
                  className={`${qualBadge.bg} ${qualBadge.text} px-4 py-2 rounded-xl font-bold text-sm cursor-pointer border-0 appearance-none pr-9 shadow-lg hover:shadow-xl transition-all`}
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

      {/* Conteúdo Principal - Draggable Grid */}
      <div className="flex-1 p-4 overflow-auto">
        <DraggableGrid
          widgets={widgets}
          onLayoutChange={handleLayoutChange}
          onRemoveWidget={handleRemoveWidget}
          onAddWidget={() => setShowCatalog(true)}
          renderWidget={(widget) => (
            <LeadWidgetRenderer
              config={widget}
              lead={lead}
              messages={messages}
              events={events}
              sellers={sellers}
              opportunities={opportunities}
              onAssignSeller={atribuirVendedor}
              onRemoveSeller={removerAtribuicao}
              onAddNote={adicionarNota}
              onDeleteNote={deletarNota}
              onReloadOpportunities={reloadOpportunities}
              assigningSeller={atribuindoVendedor}
              chatScrollRef={chatEndRef}
            />
          )}
          editMode={editMode}
          onToggleEditMode={() => setEditMode(!editMode)}
          onSave={handleSave}
          onReset={handleReset}
          hasChanges={hasChanges}
          saving={saving}
        />
      </div>

      {/* Widget Catalog Modal */}
      <WidgetCatalogModal
        isOpen={showCatalog}
        onClose={() => setShowCatalog(false)}
        onSelectWidget={handleAddWidget}
        existingWidgetTypes={existingWidgetTypes}
      />
    </div>
  );
}
