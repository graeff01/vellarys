'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import {
  Building2,
  Users,
  MessageSquare,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Zap,
  PlayCircle,
  Activity,
  BarChart3,
  ArrowRight,
  RefreshCw,
  Target,
} from 'lucide-react';
import { getToken } from '@/lib/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// =============================================================================
// TIPOS
// =============================================================================

interface CEOMetrics {
  total_clients: number;
  active_clients: number;
  inactive_clients: number;
  total_leads: number;
  leads_this_week: number;
  leads_this_month: number;
  leads_growth_percent: number;
  total_messages: number;
  messages_this_week: number;
  avg_conversion_rate: number;
  total_handoffs: number;
  clients_healthy: number;
  clients_warning: number;
  clients_critical: number;
}

interface TenantHealth {
  id: number;
  name: string;
  slug: string;
  status: 'healthy' | 'warning' | 'critical' | 'inactive';
  leads_total: number;
  leads_this_week: number;
  leads_this_month: number;
  messages_total: number;
  last_activity: string | null;
  days_since_activity: number;
  conversion_rate: number;
  plan: string | null;
}

interface Alert {
  type: 'warning' | 'critical' | 'info';
  title: string;
  message: string;
  tenant_id: number | null;
  tenant_name: string | null;
  created_at: string;
}

interface WeeklyGrowth {
  week: string;
  leads: number;
  messages: number;
}

interface SchedulerStatus {
  success: boolean;
  running: boolean;
  timezone?: string;
  jobs?: Record<string, { interval_minutes: number; last_run: string | null }>;
}

// =============================================================================
// FUNÇÕES DE API
// =============================================================================

async function fetchCEOMetrics(): Promise<CEOMetrics> {
  const token = getToken();
  const res = await fetch(`${API_URL}/admin/ceo/metrics`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Erro ao carregar métricas');
  return res.json();
}

async function fetchClientsHealth(): Promise<TenantHealth[]> {
  const token = getToken();
  const res = await fetch(`${API_URL}/admin/ceo/clients-health`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Erro ao carregar saúde dos clientes');
  return res.json();
}

async function fetchAlerts(): Promise<Alert[]> {
  const token = getToken();
  const res = await fetch(`${API_URL}/admin/ceo/alerts`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Erro ao carregar alertas');
  return res.json();
}

async function fetchWeeklyGrowth(): Promise<WeeklyGrowth[]> {
  const token = getToken();
  const res = await fetch(`${API_URL}/admin/ceo/weekly-growth?weeks=8`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Erro ao carregar crescimento');
  return res.json();
}

async function fetchSchedulerStatus(): Promise<SchedulerStatus> {
  const token = getToken();
  const res = await fetch(`${API_URL}/admin/ceo/scheduler-status`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Erro ao carregar status');
  return res.json();
}

async function triggerFollowUp(): Promise<{ success: boolean; message?: string }> {
  const token = getToken();
  const res = await fetch(`${API_URL}/admin/ceo/trigger-follow-up`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.json();
}

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================

export function CEODashboard() {
  const [metrics, setMetrics] = useState<CEOMetrics | null>(null);
  const [clients, setClients] = useState<TenantHealth[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [growth, setGrowth] = useState<WeeklyGrowth[]>([]);
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggeringFollowUp, setTriggeringFollowUp] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      const [metricsData, clientsData, alertsData, growthData, schedulerData] = await Promise.all([
        fetchCEOMetrics().catch(() => null),
        fetchClientsHealth().catch(() => []),
        fetchAlerts().catch(() => []),
        fetchWeeklyGrowth().catch(() => []),
        fetchSchedulerStatus().catch(() => ({ success: false, running: false })),
      ]);

      setMetrics(metricsData);
      setClients(clientsData);
      setAlerts(alertsData);
      setGrowth(growthData);
      setScheduler(schedulerData);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleTriggerFollowUp() {
    if (triggeringFollowUp) return;
    
    setTriggeringFollowUp(true);
    try {
      const result = await triggerFollowUp();
      if (result.success) {
        alert('✅ Follow-up disparado com sucesso! Verifique os logs.');
      } else {
        alert('❌ Erro ao disparar follow-up: ' + (result.message || 'Erro desconhecido'));
      }
    } catch (error) {
      alert('❌ Erro ao disparar follow-up');
    } finally {
      setTriggeringFollowUp(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
          <div className="text-gray-500">Carregando dashboard executivo...</div>
        </div>
      </div>
    );
  }

  const maxLeads = Math.max(...growth.map(g => g.leads), 1);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard Executivo</h1>
          <p className="text-gray-500">Visão geral do seu negócio SaaS</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Atualizar
        </button>
      </div>

      {/* Cards Principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Clientes */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-purple-100 rounded-xl">
              <Building2 className="w-6 h-6 text-purple-600" />
            </div>
            <div className="flex items-center gap-1 text-green-600 text-sm font-medium">
              <CheckCircle2 className="w-4 h-4" />
              {metrics?.active_clients || 0} ativos
            </div>
          </div>
          <h3 className="text-sm font-medium text-gray-500">Total de Clientes</h3>
          <p className="text-3xl font-bold text-gray-900">{metrics?.total_clients || 0}</p>
          <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
              {metrics?.clients_healthy || 0} saudáveis
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
              {metrics?.clients_warning || 0} atenção
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-red-500 rounded-full"></span>
              {metrics?.clients_critical || 0} críticos
            </span>
          </div>
        </Card>

        {/* Leads */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-blue-100 rounded-xl">
              <Users className="w-6 h-6 text-blue-600" />
            </div>
            {(metrics?.leads_growth_percent || 0) > 0 ? (
              <div className="flex items-center gap-1 text-green-600 text-sm font-medium">
                <TrendingUp className="w-4 h-4" />
                +{metrics?.leads_growth_percent}%
              </div>
            ) : (metrics?.leads_growth_percent || 0) < 0 ? (
              <div className="flex items-center gap-1 text-red-600 text-sm font-medium">
                <TrendingDown className="w-4 h-4" />
                {metrics?.leads_growth_percent}%
              </div>
            ) : null}
          </div>
          <h3 className="text-sm font-medium text-gray-500">Total de Leads</h3>
          <p className="text-3xl font-bold text-gray-900">{metrics?.total_leads?.toLocaleString() || 0}</p>
          <div className="mt-2 text-xs text-gray-500">
            <span className="text-blue-600 font-medium">{metrics?.leads_this_week || 0}</span> esta semana •{' '}
            <span className="text-blue-600 font-medium">{metrics?.leads_this_month || 0}</span> este mês
          </div>
        </Card>

        {/* Mensagens */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-green-100 rounded-xl">
              <MessageSquare className="w-6 h-6 text-green-600" />
            </div>
          </div>
          <h3 className="text-sm font-medium text-gray-500">Mensagens Processadas</h3>
          <p className="text-3xl font-bold text-gray-900">{metrics?.total_messages?.toLocaleString() || 0}</p>
          <div className="mt-2 text-xs text-gray-500">
            <span className="text-green-600 font-medium">{metrics?.messages_this_week || 0}</span> esta semana
          </div>
        </Card>

        {/* Conversão */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-orange-100 rounded-xl">
              <Target className="w-6 h-6 text-orange-600" />
            </div>
          </div>
          <h3 className="text-sm font-medium text-gray-500">Taxa de Conversão Média</h3>
          <p className="text-3xl font-bold text-orange-600">{metrics?.avg_conversion_rate || 0}%</p>
          <div className="mt-2 text-xs text-gray-500">
            <span className="text-orange-600 font-medium">{metrics?.total_handoffs || 0}</span> handoffs realizados
          </div>
        </Card>
      </div>

      {/* Segunda linha: Saúde dos Clientes + Ações */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Saúde dos Clientes */}
        <Card className="lg:col-span-2 p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Saúde dos Clientes</h2>
              <p className="text-sm text-gray-500">Monitoramento de atividade por cliente</p>
            </div>
            <a
              href="/dashboard/clients"
              className="text-sm text-purple-600 hover:text-purple-700 flex items-center gap-1"
            >
              Ver todos <ArrowRight className="w-4 h-4" />
            </a>
          </div>

          <div className="space-y-3">
            {clients.slice(0, 6).map((client) => (
              <div
                key={client.id}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-3 h-3 rounded-full ${
                    client.status === 'healthy' ? 'bg-green-500' :
                    client.status === 'warning' ? 'bg-yellow-500' :
                    client.status === 'critical' ? 'bg-red-500' :
                    'bg-gray-400'
                  }`} />
                  <div>
                    <p className="font-medium text-gray-900">{client.name}</p>
                    <p className="text-xs text-gray-500">
                      {client.days_since_activity === 999 
                        ? 'Nunca ativo' 
                        : client.days_since_activity === 0 
                          ? 'Ativo hoje'
                          : `Há ${client.days_since_activity} dias`
                      }
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-6 text-sm">
                  <div className="text-center">
                    <p className="font-semibold text-gray-900">{client.leads_total}</p>
                    <p className="text-xs text-gray-500">leads</p>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-gray-900">{client.leads_this_week}</p>
                    <p className="text-xs text-gray-500">semana</p>
                  </div>
                  <div className="text-center">
                    <p className={`font-semibold ${
                      client.conversion_rate >= 30 ? 'text-green-600' :
                      client.conversion_rate >= 15 ? 'text-yellow-600' :
                      'text-gray-600'
                    }`}>{client.conversion_rate}%</p>
                    <p className="text-xs text-gray-500">conversão</p>
                  </div>
                </div>
              </div>
            ))}
            
            {clients.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                Nenhum cliente cadastrado ainda
              </div>
            )}
          </div>
        </Card>

        {/* Ações Rápidas */}
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Ações Rápidas</h2>
          
          <div className="space-y-4">
            {/* Status do Scheduler */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Scheduler</span>
                <span className={`flex items-center gap-1 text-xs font-medium ${
                  scheduler?.running ? 'text-green-600' : 'text-red-600'
                }`}>
                  <Activity className="w-3 h-3" />
                  {scheduler?.running ? 'Ativo' : 'Inativo'}
                </span>
              </div>
              {scheduler?.jobs?.follow_up_job && (
                <p className="text-xs text-gray-500">
                  Último run: {scheduler.jobs.follow_up_job.last_run 
                    ? new Date(scheduler.jobs.follow_up_job.last_run).toLocaleString('pt-BR')
                    : 'Nunca executou'
                  }
                </p>
              )}
            </div>

            {/* Botão Disparar Follow-up */}
            <button
              onClick={handleTriggerFollowUp}
              disabled={triggeringFollowUp}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {triggeringFollowUp ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  Disparando...
                </>
              ) : (
                <>
                  <PlayCircle className="w-5 h-5" />
                  Disparar Follow-up Agora
                </>
              )}
            </button>

            {/* Links rápidos */}
            <div className="space-y-2">
              <a
                href="/dashboard/clients"
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <Building2 className="w-5 h-5 text-gray-500" />
                <span className="text-sm text-gray-700">Gerenciar Clientes</span>
              </a>
              <a
                href="/dashboard/logs"
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <BarChart3 className="w-5 h-5 text-gray-500" />
                <span className="text-sm text-gray-700">Ver Logs do Sistema</span>
              </a>
              <a
                href="/dashboard/plans"
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <Zap className="w-5 h-5 text-gray-500" />
                <span className="text-sm text-gray-700">Gerenciar Planos</span>
              </a>
            </div>
          </div>
        </Card>
      </div>

      {/* Terceira linha: Gráfico de Crescimento + Alertas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gráfico de Crescimento */}
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Crescimento Semanal</h2>
          <p className="text-sm text-gray-500 mb-6">Leads captados por semana (todos os clientes)</p>
          
          <div className="h-48 flex items-end justify-between gap-2">
            {growth.map((week, index) => (
              <div key={index} className="flex-1 flex flex-col items-center gap-2">
                <div 
                  className="w-full bg-purple-500 rounded-t transition-all hover:bg-purple-600"
                  style={{ 
                    height: `${(week.leads / maxLeads) * 100}%`,
                    minHeight: week.leads > 0 ? '8px' : '2px'
                  }}
                  title={`${week.leads} leads`}
                />
                <span className="text-xs text-gray-500">{week.week}</span>
              </div>
            ))}
          </div>
          
          <div className="mt-4 pt-4 border-t flex items-center justify-between text-sm">
            <span className="text-gray-500">Total no período</span>
            <span className="font-semibold text-purple-600">
              {growth.reduce((sum, w) => sum + w.leads, 0)} leads
            </span>
          </div>
        </Card>

        {/* Alertas */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Alertas</h2>
              <p className="text-sm text-gray-500">Clientes que precisam de atenção</p>
            </div>
            {alerts.length > 0 && (
              <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">
                {alerts.length} alertas
              </span>
            )}
          </div>

          <div className="space-y-3 max-h-64 overflow-y-auto">
            {alerts.map((alert, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border-l-4 ${
                  alert.type === 'critical' 
                    ? 'bg-red-50 border-red-500' 
                    : alert.type === 'warning'
                      ? 'bg-yellow-50 border-yellow-500'
                      : 'bg-blue-50 border-blue-500'
                }`}
              >
                <div className="flex items-start gap-3">
                  {alert.type === 'critical' ? (
                    <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  ) : alert.type === 'warning' ? (
                    <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
                  )}
                  <div>
                    <p className="font-medium text-gray-900">{alert.tenant_name}</p>
                    <p className="text-sm text-gray-600">{alert.message}</p>
                  </div>
                </div>
              </div>
            ))}
            
            {alerts.length === 0 && (
              <div className="text-center py-8">
                <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-3" />
                <p className="text-gray-500">Nenhum alerta no momento</p>
                <p className="text-sm text-gray-400">Todos os clientes estão saudáveis!</p>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}