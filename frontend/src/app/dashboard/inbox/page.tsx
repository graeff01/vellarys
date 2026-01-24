/**
 * Página: CRM Inbox
 * Interface para corretores atenderem leads via CRM
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { InboxLeadList } from '@/components/dashboard/inbox/inbox-lead-list';
import { InboxConversation } from '@/components/dashboard/inbox/inbox-conversation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import {
  InboxLead,
  SellerInfo,
  getInboxLeads,
  getSellerInfo,
  checkInboxAvailable,
} from '@/lib/inbox';
import {
  MessageCircle,
  Users,
  TrendingUp,
  AlertCircle,
  RefreshCw,
  Filter,
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
      title: 'Inbox atualizado!',
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
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  const totalLeads = leads.length;
  const unattendedLeads = leads.filter((l) => !l.is_taken_over).length;
  const attendedLeads = leads.filter((l) => l.is_taken_over).length;

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="border-b bg-white p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">CRM Inbox</h1>
            <p className="text-sm text-gray-500">
              Atenda seus leads diretamente pelo painel
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Atualizar
            </Button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total de Leads</p>
                <p className="text-2xl font-bold">{totalLeads}</p>
              </div>
              <Users className="h-8 w-8 text-blue-600" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">IA Atendendo</p>
                <p className="text-2xl font-bold">{unattendedLeads}</p>
              </div>
              <MessageCircle className="h-8 w-8 text-orange-600" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Você Atendendo</p>
                <p className="text-2xl font-bold">{attendedLeads}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-600" />
            </div>
          </Card>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Lista de Leads - Desktop sempre visível, Mobile esconde quando seleciona */}
        <div
          className={`w-full lg:w-96 border-r bg-white flex flex-col ${
            showConversation ? 'hidden lg:flex' : 'flex'
          }`}
        >
          {/* Filtros */}
          <div className="p-4 border-b">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <Select value={attendedFilter} onValueChange={(value: any) => setAttendedFilter(value)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos os leads</SelectItem>
                  <SelectItem value="ai">IA atendendo</SelectItem>
                  <SelectItem value="seller">Você atendendo</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Lista */}
          <div className="flex-1 overflow-hidden">
            <InboxLeadList
              leads={leads}
              selectedLeadId={selectedLead?.id || null}
              onSelectLead={handleSelectLead}
              loading={loading}
            />
          </div>
        </div>

        {/* Área de Conversa - Desktop sempre visível, Mobile mostra quando seleciona */}
        <div
          className={`flex-1 bg-gray-50 ${
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

      {/* Info sobre modo CRM Inbox */}
      {sellerInfo.handoff_mode === 'crm_inbox' && (
        <div className="border-t bg-blue-50 p-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-blue-600 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-blue-900">
                <strong>Modo CRM Inbox ativo:</strong> Você atende os leads diretamente
                pelo painel. As mensagens são enviadas via WhatsApp da empresa.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
