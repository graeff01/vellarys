/**
 * Página: CRM Inbox - WhatsApp Web Style
 * Interface inspirada no WhatsApp Web para melhor familiaridade dos corretores
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { InboxLeadList } from '@/components/dashboard/inbox/inbox-lead-list';
import { InboxConversation } from '@/components/dashboard/inbox/inbox-conversation';
import { MessageSearch } from '@/components/dashboard/inbox/message-search';
import { ShortcutsHelp } from '@/components/dashboard/inbox/shortcuts-help';
import { ArchiveModal } from '@/components/dashboard/inbox/archive-modal';
import { FiltersPanel, InboxFilters } from '@/components/dashboard/inbox/filters-panel';
import { MetricsDashboard } from '@/components/dashboard/inbox/metrics-dashboard';
import { ConnectionIndicator } from '@/components/dashboard/inbox/connection-indicator';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { useKeyboardShortcuts, createShortcut } from '@/hooks/use-keyboard-shortcuts';
import {
  InboxLead,
  SellerInfo,
  getInboxLeads,
  getSellerInfo,
  checkInboxAvailable,
} from '@/lib/inbox';
import {
  RefreshCw,
  Archive,
  Search,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function InboxPage() {
  const router = useRouter();
  const { toast } = useToast();

  const [sellerInfo, setSellerInfo] = useState<SellerInfo | null>(null);
  const [leads, setLeads] = useState<InboxLead[]>([]);
  const [selectedLead, setSelectedLead] = useState<InboxLead | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showConversation, setShowConversation] = useState(false);
  const [showMetrics, setShowMetrics] = useState(true);

  // Filtros
  const [filters, setFilters] = useState<InboxFilters>({
    attendedBy: 'all',
  });

  // Bulk selection
  const [selectedLeadIds, setSelectedLeadIds] = useState<number[]>([]);
  const [bulkMode, setBulkMode] = useState(false);

  // Modais
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [showShortcutsHelp, setShowShortcutsHelp] = useState(false);
  const [showArchiveModal, setShowArchiveModal] = useState(false);

  // SSE Connection status
  const [sseStatus, setSseStatus] = useState<'connected' | 'connecting' | 'disconnected'>('disconnected');

  // Atalhos de teclado globais
  useKeyboardShortcuts({
    shortcuts: [
      createShortcut('k', 'Buscar mensagens', () => setShowSearchModal(true), { ctrl: true }),
      createShortcut('a', 'Arquivar lead selecionado', () => {
        if (selectedLead) {
          setSelectedLeadIds([selectedLead.id]);
          setShowArchiveModal(true);
        } else if (selectedLeadIds.length > 0) {
          setShowArchiveModal(true);
        }
      }, { ctrl: true }),
      createShortcut('?', 'Mostrar ajuda de atalhos', () => setShowShortcutsHelp(true)),
      createShortcut('Escape', 'Fechar modais/bulk mode', () => {
        setShowSearchModal(false);
        setShowShortcutsHelp(false);
        setShowArchiveModal(false);
        setBulkMode(false);
        setSelectedLeadIds([]);
      })
    ],
    enabled: true
  });

  useEffect(() => {
    checkAccess();
  }, []);

  useEffect(() => {
    if (sellerInfo?.can_use_inbox) {
      loadLeads();
    }
  }, [sellerInfo, filters]);

  const checkAccess = async () => {
    try {
      // Verifica se inbox está disponível
      const available = await checkInboxAvailable();

      if (!available.available) {
        toast({
          variant: 'destructive',
          title: 'Inbox não disponível',
          description: available.reason,
        });
        router.push('/dashboard');
        return;
      }

      // Carrega info do corretor
      const info = await getSellerInfo();
      setSellerInfo(info);
      setSseStatus('connected'); // Simula conexão SSE
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Erro ao acessar inbox',
        description: error.response?.data?.detail || 'Tente novamente',
      });
      router.push('/dashboard');
    }
  };

  const loadLeads = async () => {
    if (!sellerInfo) return;

    setLoading(true);
    try {
      const data = await getInboxLeads({
        attended_filter: filters.attendedBy,
        status: filters.status,
        // Backend ainda não suporta estes filtros, mas preparamos o frontend
        // qualification: filters.qualification,
        // date_from: filters.dateFrom,
        // date_to: filters.dateTo,
      });
      setLeads(data);

      // Se tinha um lead selecionado, atualiza ele
      if (selectedLead) {
        const updatedLead = data.find((l) => l.id === selectedLead.id);
        if (updatedLead) {
          setSelectedLead(updatedLead);
        }
      }

      // Busca fotos de perfil em background para leads sem foto
      fetchMissingProfilePictures(data);
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Erro ao carregar leads',
        description: error.response?.data?.detail || 'Tente novamente',
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchMissingProfilePictures = async (leadsData: InboxLead[]) => {
    // Busca fotos apenas para leads que não têm foto ainda
    const leadsWithoutPicture = leadsData.filter(l => !l.profile_picture_url);

    if (leadsWithoutPicture.length === 0) return;

    // Importa a função de busca de foto
    const { fetchProfilePicture } = await import('@/lib/inbox');

    // Busca fotos em paralelo (máximo 5 por vez para não sobrecarregar)
    const batchSize = 5;
    for (let i = 0; i < leadsWithoutPicture.length; i += batchSize) {
      const batch = leadsWithoutPicture.slice(i, i + batchSize);

      await Promise.all(
        batch.map(async (lead) => {
          try {
            const result = await fetchProfilePicture(lead.id);
            if (result.success && result.url) {
              // Atualiza o lead com a foto
              setLeads(prev => prev.map(l =>
                l.id === lead.id ? { ...l, profile_picture_url: result.url } : l
              ));

              // Se é o lead selecionado, atualiza também
              if (selectedLead?.id === lead.id) {
                setSelectedLead(prev => prev ? { ...prev, profile_picture_url: result.url } : null);
              }
            }
          } catch (error) {
            // Ignora erros silenciosamente - foto não é crítica
            console.debug(`Foto não disponível para lead ${lead.id}`);
          }
        })
      );

      // Pequeno delay entre batches para não sobrecarregar
      if (i + batchSize < leadsWithoutPicture.length) {
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadLeads();
    setRefreshing(false);
    toast({
      title: 'Conversas atualizadas!',
      description: 'Leads carregados com sucesso.',
    });
  };

  const handleSelectLead = (lead: InboxLead) => {
    if (bulkMode) {
      // Modo bulk: toggle selection
      setSelectedLeadIds(prev =>
        prev.includes(lead.id)
          ? prev.filter(id => id !== lead.id)
          : [...prev, lead.id]
      );
    } else {
      // Modo normal: abre conversa
      setSelectedLead(lead);
      setShowConversation(true);
    }
  };

  const handleLeadUpdated = () => {
    loadLeads();
  };

  const handleArchiveSuccess = () => {
    loadLeads();
    setSelectedLeadIds([]);
    setBulkMode(false);
    toast({
      title: 'Lead(s) arquivado(s)!',
      description: 'Pode recuperar depois em "Arquivados".',
    });
  };

  const toggleBulkMode = () => {
    setBulkMode(!bulkMode);
    setSelectedLeadIds([]);
  };

  if (!sellerInfo) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#f0f2f5]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#075e54]"></div>
      </div>
    );
  }

  const totalLeads = leads.length;
  const unattendedLeads = leads.filter((l) => !l.is_taken_over).length;
  const attendedLeads = leads.filter((l) => l.is_taken_over).length;
  const selectedLeadNames = selectedLeadIds.map(id => leads.find(l => l.id === id)?.name || '');

  return (
    <div className="h-screen flex flex-col bg-[#f0f2f5]" style={{ fontFamily: 'Segoe UI, Helvetica Neue, Arial, sans-serif' }}>
      {/* Métricas Dashboard - Colapsável */}
      {showMetrics && (
        <div className="px-4 pt-3 pb-2 bg-white border-b border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-700">Suas Métricas</h3>
            <button
              onClick={() => setShowMetrics(false)}
              className="p-1 hover:bg-gray-100 rounded"
            >
              <ChevronUp className="h-4 w-4 text-gray-500" />
            </button>
          </div>
          <MetricsDashboard />
        </div>
      )}

      {!showMetrics && (
        <div className="px-4 py-1.5 bg-white border-b border-gray-200">
          <button
            onClick={() => setShowMetrics(true)}
            className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700"
          >
            <ChevronDown className="h-3 w-3" />
            Mostrar métricas
          </button>
        </div>
      )}

      {/* Main Content - Layout estilo WhatsApp */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Painel lateral (Lista de Leads) */}
        <div
          className={cn(
            "w-full lg:w-[400px] border-r border-gray-300 bg-white flex flex-col",
            showConversation ? 'hidden lg:flex' : 'flex'
          )}
        >
          {/* Header do painel lateral - estilo WhatsApp */}
          <div className="bg-white border-b border-gray-200">
            {/* Barra superior principal */}
            <div className="px-4 py-3 flex items-center justify-between border-b border-gray-100">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                {/* Avatar do usuário */}
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                  <span className="text-base font-semibold text-white">
                    {sellerInfo.user_name ? sellerInfo.user_name.charAt(0).toUpperCase() : 'V'}
                  </span>
                </div>

                {/* Info e status */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-semibold text-gray-900">CRM Inbox</h2>
                    <ConnectionIndicator status={sseStatus} />
                  </div>
                  <p className="text-xs text-gray-500 truncate">
                    {totalLeads > 0 ? (
                      <>
                        {attendedLeads > 0 && `${attendedLeads} atendendo`}
                        {attendedLeads > 0 && unattendedLeads > 0 && ' • '}
                        {unattendedLeads > 0 && `${unattendedLeads} com IA`}
                      </>
                    ) : (
                      'Nenhuma conversa'
                    )}
                  </p>
                </div>
              </div>

              {/* Ações rápidas */}
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setShowSearchModal(true)}
                  className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Buscar mensagens (Ctrl+K)"
                >
                  <Search className="h-4 w-4" />
                </button>

                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                  title="Atualizar conversas"
                >
                  <RefreshCw className={cn("h-4 w-4", refreshing && 'animate-spin')} />
                </button>
              </div>
            </div>

            {/* Barra de filtros e ações */}
            <div className="px-4 py-2 flex items-center gap-2 bg-gray-50">
              <FiltersPanel
                filters={filters}
                onFiltersChange={setFilters}
                leadsCount={totalLeads}
              />

              {/* Bulk Actions */}
              {bulkMode && selectedLeadIds.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowArchiveModal(true)}
                  className="gap-1.5 h-8 text-xs border-orange-200 bg-orange-50 hover:bg-orange-100 text-orange-700"
                >
                  <Archive className="h-3.5 w-3.5" />
                  Arquivar ({selectedLeadIds.length})
                </Button>
              )}

              <Button
                variant={bulkMode ? "default" : "outline"}
                size="sm"
                onClick={toggleBulkMode}
                className={cn(
                  "ml-auto h-8 text-xs",
                  bulkMode ? "bg-blue-600 hover:bg-blue-700 text-white" : "border-gray-300"
                )}
              >
                {bulkMode ? 'Cancelar seleção' : 'Selecionar'}
              </Button>
            </div>
          </div>

          {/* Lista de conversas */}
          <div className="flex-1 overflow-hidden">
            <InboxLeadList
              leads={leads}
              selectedLeadId={selectedLead?.id || null}
              onSelectLead={handleSelectLead}
              loading={loading}
              bulkMode={bulkMode}
              selectedLeadIds={selectedLeadIds}
            />
          </div>
        </div>

        {/* Área de Conversa */}
        <div
          className={cn(
            "flex-1 h-full",
            showConversation ? 'block' : 'hidden lg:block'
          )}
        >
          <InboxConversation
            lead={selectedLead}
            onBack={() => setShowConversation(false)}
            onLeadUpdated={handleLeadUpdated}
          />
        </div>
      </div>

      {/* Modais */}
      <MessageSearch
        open={showSearchModal}
        onOpenChange={setShowSearchModal}
      />

      <ShortcutsHelp
        open={showShortcutsHelp}
        onOpenChange={setShowShortcutsHelp}
      />

      <ArchiveModal
        open={showArchiveModal}
        onOpenChange={setShowArchiveModal}
        leadIds={selectedLeadIds}
        leadNames={selectedLeadNames}
        onSuccess={handleArchiveSuccess}
      />
    </div>
  );
}
