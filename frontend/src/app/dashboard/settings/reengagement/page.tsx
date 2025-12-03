'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader } from '@/components/ui/card';
import { getToken } from '@/lib/auth';
import { 
  RefreshCw, 
  Clock, 
  Hash, 
  MessageSquare, 
  ToggleLeft, 
  ToggleRight,
  Play,
  Users,
  CheckCircle,
  XCircle,
  AlertCircle,
  Eye,
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface ReengagementConfig {
  enabled: boolean;
  inactivity_hours: number;
  max_attempts: number;
  min_hours_between_attempts: number;
  respect_business_hours: boolean;
  exclude_hot_leads: boolean;
  exclude_handed_off: boolean;
  custom_message: string | null;
}

interface ReengagementStats {
  total_attempts: number;
  recovered_leads: number;
  success_rate: number;
  pending: number;
  by_status: {
    none: number;
    sent: number;
    responded: number;
    given_up: number;
    failed: number;
  };
}

interface PendingLead {
  id: number;
  name: string | null;
  phone: string | null;
  qualification: string;
  last_activity_at: string | null;
  reengagement_attempts: number;
  reengagement_status: string;
}

export default function ReengagementPage() {
  const [config, setConfig] = useState<ReengagementConfig | null>(null);
  const [stats, setStats] = useState<ReengagementStats | null>(null);
  const [pendingLeads, setPendingLeads] = useState<PendingLead[]>([]);
  const [previewMessage, setPreviewMessage] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState(false);

  async function fetchData() {
    try {
      const token = getToken();
      const headers = { Authorization: `Bearer ${token}` };

      const [configRes, statsRes, pendingRes] = await Promise.all([
        fetch(`${API_URL}/reengagement/config`, { headers }),
        fetch(`${API_URL}/reengagement/stats`, { headers }),
        fetch(`${API_URL}/reengagement/pending`, { headers }),
      ]);

      const configData = await configRes.json();
      const statsData = await statsRes.json();
      const pendingData = await pendingRes.json();

      setConfig(configData.config);
      setStats(statsData);
      setPendingLeads(pendingData.leads || []);

      // Preview message
      const previewRes = await fetch(`${API_URL}/reengagement/preview-message?attempt=1`, { headers });
      const previewData = await previewRes.json();
      setPreviewMessage(previewData.message);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, []);

  async function saveConfig(updates: Partial<ReengagementConfig>) {
    setSaving(true);
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/reengagement/config`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(updates),
      });

      if (response.ok) {
        const data = await response.json();
        setConfig(data.config);
      }
    } catch (error) {
      console.error('Erro ao salvar:', error);
    } finally {
      setSaving(false);
    }
  }

  async function executeReengagement() {
    setExecuting(true);
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/reengagement/execute`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Reengajamento executado!\n\nProcessados: ${result.processed}\nSucesso: ${result.success}\nFalha: ${result.failed}`);
        fetchData(); // Recarrega dados
      }
    } catch (error) {
      console.error('Erro ao executar:', error);
      alert('Erro ao executar reengajamento');
    } finally {
      setExecuting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Carregando...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Reengajamento</h1>
          <p className="text-gray-500">Configure a recuperação automática de leads inativos</p>
        </div>
        <button
          onClick={executeReengagement}
          disabled={executing || !config?.enabled}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Play className="w-4 h-4" />
          {executing ? 'Executando...' : 'Executar Agora'}
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Users className="w-5 h-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Pendentes</p>
                <p className="text-xl font-bold">{stats.pending}</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <MessageSquare className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Tentativas</p>
                <p className="text-xl font-bold">{stats.total_attempts}</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Recuperados</p>
                <p className="text-xl font-bold text-green-600">{stats.recovered_leads}</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <RefreshCw className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Taxa de Sucesso</p>
                <p className="text-xl font-bold">{stats.success_rate}%</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Configurações */}
        <Card>
          <CardHeader title="Configurações" subtitle="Defina como o reengajamento funciona" />
          
          {config && (
            <div className="space-y-6">
              {/* Toggle Ativo */}
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">Reengajamento Automático</p>
                  <p className="text-sm text-gray-500">Ativar recuperação de leads inativos</p>
                </div>
                <button
                  onClick={() => saveConfig({ enabled: !config.enabled })}
                  disabled={saving}
                  className="text-gray-600 hover:text-gray-900"
                >
                  {config.enabled ? (
                    <ToggleRight className="w-10 h-10 text-green-600" />
                  ) : (
                    <ToggleLeft className="w-10 h-10 text-gray-400" />
                  )}
                </button>
              </div>

              {/* Tempo de Inatividade */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <Clock className="w-4 h-4" />
                  Tempo de Inatividade (horas)
                </label>
                <select
                  value={config.inactivity_hours}
                  onChange={(e) => saveConfig({ inactivity_hours: Number(e.target.value) })}
                  disabled={saving}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value={12}>12 horas</option>
                  <option value={24}>24 horas</option>
                  <option value={48}>48 horas</option>
                  <option value={72}>72 horas</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Lead será reengajado após ficar inativo por este tempo
                </p>
              </div>

              {/* Máximo de Tentativas */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <Hash className="w-4 h-4" />
                  Máximo de Tentativas
                </label>
                <select
                  value={config.max_attempts}
                  onChange={(e) => saveConfig({ max_attempts: Number(e.target.value) })}
                  disabled={saving}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value={1}>1 tentativa</option>
                  <option value={2}>2 tentativas</option>
                  <option value={3}>3 tentativas</option>
                  <option value={5}>5 tentativas</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Após isso, lead será marcado como desistência
                </p>
              </div>

              {/* Opções Adicionais */}
              <div className="space-y-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.respect_business_hours}
                    onChange={(e) => saveConfig({ respect_business_hours: e.target.checked })}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-sm text-gray-700">Respeitar horário comercial (8h-20h)</span>
                </label>

                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.exclude_hot_leads}
                    onChange={(e) => saveConfig({ exclude_hot_leads: e.target.checked })}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-sm text-gray-700">Não reengajar leads quentes</span>
                </label>

                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.exclude_handed_off}
                    onChange={(e) => saveConfig({ exclude_handed_off: e.target.checked })}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-sm text-gray-700">Não reengajar leads já transferidos</span>
                </label>
              </div>
            </div>
          )}
        </Card>

        {/* Preview e Leads Pendentes */}
        <div className="space-y-6">
          {/* Preview da Mensagem */}
          <Card>
            <CardHeader title="Preview da Mensagem" subtitle="Como o lead receberá" />
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                  <MessageSquare className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-800">{previewMessage}</p>
                  <p className="text-xs text-gray-500 mt-2">Tentativa 1 de {config?.max_attempts || 3}</p>
                </div>
              </div>
            </div>
          </Card>

          {/* Leads Pendentes */}
          <Card>
            <CardHeader 
              title="Leads Pendentes" 
              subtitle={`${pendingLeads.length} leads aguardando reengajamento`}
            />
            {pendingLeads.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {pendingLeads.slice(0, 10).map((lead) => (
                  <div 
                    key={lead.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <p className="font-medium text-gray-900">{lead.name || lead.phone}</p>
                      <p className="text-xs text-gray-500">
                        {lead.reengagement_attempts} tentativa(s) • {lead.qualification}
                      </p>
                    </div>
                    <div className="text-xs text-gray-400">
                      {lead.last_activity_at 
                        ? new Date(lead.last_activity_at).toLocaleDateString('pt-BR')
                        : 'Sem atividade'
                      }
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="w-12 h-12 mx-auto mb-2 text-green-500" />
                <p>Nenhum lead pendente!</p>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}