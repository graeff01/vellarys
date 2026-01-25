/**
 * Página: CRM Inbox - WhatsApp Web Style
 * Interface inspirada no WhatsApp Web para melhor familiaridade dos corretores
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { InboxLeadList } from '@/components/dashboard/inbox/inbox-lead-list';
import { InboxConversation } from '@/components/dashboard/inbox/inbox-conversation';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import {
  InboxLead,
  SellerInfo,
  getInboxLeads,
  getSellerInfo,
  checkInboxAvailable,
} from '@/lib/inbox';
import {
  RefreshCw,
  Filter,
  MoreVertical,
  Menu,
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export default function InboxPage() {
  const router = useRouter();
  const { toast } = useToast();

  const [sellerInfo, setSellerInfo] = useState<SellerInfo | null>(null);
  const [leads, setLeads] = useState<InboxLead[]>([]);
  const [selectedLead, setSelectedLead] = useState<InboxLead | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [attendedFilter, setAttendedFilter] = useState<'all' | 'ai' | 'seller'>('all');
  const [showConversation, setShowConversation] = useState(false);

  useEffect(() => {
    checkAccess();
  }, []);

  useEffect(() => {
    if (sellerInfo?.can_use_inbox) {
      loadLeads();
    }
  }, [sellerInfo, attendedFilter]);

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
        attended_filter: attendedFilter,
      });
      setLeads(data);

      // Se tinha um lead selecionado, atualiza ele
      if (selectedLead) {
        const updatedLead = data.find((l) => l.id === selectedLead.id);
        if (updatedLead) {
          setSelectedLead(updatedLead);
        }
      }
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
    setSelectedLead(lead);
    setShowConversation(true);
  };

  const handleLeadUpdated = () => {
    loadLeads();
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

  return (
    <div className="h-screen flex flex-col bg-[#f0f2f5]" style={{ fontFamily: 'Segoe UI, Helvetica Neue, Arial, sans-serif' }}>
      {/* Main Content - Layout estilo WhatsApp */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Painel lateral (Lista de Leads) */}
        <div
          className={`w-full lg:w-[400px] border-r border-gray-300 bg-white flex flex-col ${
            showConversation ? 'hidden lg:flex' : 'flex'
          }`}
        >
          {/* Header do painel lateral - estilo WhatsApp */}
          <div className="bg-[#f0f2f5] border-b border-gray-300">
            {/* Barra superior com avatar e ações */}
            <div className="px-4 py-2.5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                {/* Avatar do usuário */}
                <div className="w-10 h-10 rounded-full bg-[#dfe5e7] flex items-center justify-center">
                  <span className="text-lg font-medium text-gray-700">
                    {sellerInfo.user_name ? sellerInfo.user_name.charAt(0).toUpperCase() : 'V'}
                  </span>
                </div>
                {/* Badge Vellarys - branding sutil */}
                <div className="hidden md:block">
                  <p className="text-sm font-medium text-gray-900">CRM Inbox</p>
                  <p className="text-xs text-gray-500">
                    {attendedLeads > 0 && `${attendedLeads} atendendo`}
                    {attendedLeads > 0 && unattendedLeads > 0 && ' • '}
                    {unattendedLeads > 0 && `${unattendedLeads} com IA`}
                  </p>
                </div>
              </div>

              {/* Botões de ação */}
              <div className="flex items-center gap-1">
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="p-2 text-gray-600 hover:bg-gray-200/50 rounded-full transition-colors"
                  title="Atualizar conversas"
                >
                  <RefreshCw className={`h-5 w-5 ${refreshing ? 'animate-spin' : ''}`} />
                </button>
                <button
                  className="p-2 text-gray-600 hover:bg-gray-200/50 rounded-full transition-colors"
                  title="Menu"
                >
                  <MoreVertical className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Barra de filtro */}
            <div className="px-3 pb-2">
              <Select value={attendedFilter} onValueChange={(value: any) => setAttendedFilter(value)}>
                <SelectTrigger className="w-full h-9 bg-white border-gray-300 text-sm">
                  <div className="flex items-center gap-2">
                    <Filter className="h-3.5 w-3.5 text-gray-500" />
                    <SelectValue />
                  </div>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">
                    Todas as conversas ({totalLeads})
                  </SelectItem>
                  <SelectItem value="ai">
                    IA atendendo ({unattendedLeads})
                  </SelectItem>
                  <SelectItem value="seller">
                    Você atendendo ({attendedLeads})
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Lista de conversas */}
          <div className="flex-1 overflow-hidden">
            <InboxLeadList
              leads={leads}
              selectedLeadId={selectedLead?.id || null}
              onSelectLead={handleSelectLead}
              loading={loading}
            />
          </div>
        </div>

        {/* Área de Conversa */}
        <div
          className={`flex-1 h-full ${
            showConversation ? 'block' : 'hidden lg:block'
          }`}
        >
          <InboxConversation
            lead={selectedLead}
            onBack={() => setShowConversation(false)}
            onLeadUpdated={handleLeadUpdated}
          />
        </div>
      </div>

      {/* Rodapé sutil com informação do modo (opcional) */}
      {sellerInfo.handoff_mode === 'crm_inbox' && false && ( // Desabilitado por padrão para visual limpo
        <div className="border-t border-gray-300 bg-[#f0f2f5] px-4 py-2">
          <p className="text-xs text-gray-600 text-center">
            Modo CRM Inbox • Mensagens enviadas via WhatsApp Business da empresa
          </p>
        </div>
      )}
    </div>
  );
}
