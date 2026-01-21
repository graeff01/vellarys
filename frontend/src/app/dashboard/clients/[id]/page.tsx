'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { 
  ArrowLeft,
  Building2, 
  Users,
  MessageSquare,
  TrendingUp,
  Calendar,
  Mail,
  Phone,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Settings,
  UserPlus,
  Zap,
  Crown,
  Target
} from 'lucide-react';
import { getToken, getUser } from '@/lib/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface TenantDetails {
  id: number;
  name: string;
  slug: string;
  plan: string;
  active: boolean;
  settings: Record<string, unknown>;
  created_at: string;
  // Subscription info
  subscription?: {
    status: string;
    billing_cycle: string;
    trial_started_at?: string;
    trial_ends_at?: string;
    is_trial: boolean;
    days_remaining_trial: number;
    is_blocked: boolean;
    limit_exceeded_reason?: string;
  };
  // Usage info
  usage?: {
    period: string;
    leads_count: number;
    messages_count: number;
    ai_tokens_used: number;
  };
  // Plan limits
  plan_limits?: {
    leads_per_month: number;
    messages_per_month: number;
    sellers: number;
  };
  // Counts
  leads_count: number;
  users_count: number;
  sellers_count: number;
  messages_count: number;
  // Lists
  users?: Array<{
    id: number;
    name: string;
    email: string;
    role: string;
    active: boolean;
  }>;
  sellers?: Array<{
    id: number;
    name: string;
    email?: string;
    phone?: string;
    active: boolean;
    leads_count: number;
  }>;
  recent_leads?: Array<{
    id: number;
    name: string;
    phone?: string;
    qualification: string;
    status: string;
    created_at: string;
  }>;
}

interface Plan {
  id: number;
  slug: string;
  name: string;
  limits: {
    leads_per_month: number;
    messages_per_month: number;
    sellers: number;
  };
}

export default function ClientDetailsPage() {
  const router = useRouter();
  const params = useParams();
  const tenantId = params.id as string;
  
  const [tenant, setTenant] = useState<TenantDetails | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Modal states
  const [showChangePlanModal, setShowChangePlanModal] = useState(false);
  const [showExtendTrialModal, setShowExtendTrialModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('');
  const [trialDays, setTrialDays] = useState(7);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    const user = getUser();
    if (user?.role !== 'superadmin') {
      router.push('/dashboard');
      return;
    }
    fetchTenantDetails();
    fetchPlans();
  }, [router, tenantId]);

  async function fetchTenantDetails() {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/tenants/${tenantId}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setTenant(data);
      } else {
        setError('Cliente não encontrado');
      }
    } catch (err) {
      console.error('Erro ao carregar cliente:', err);
      setError('Erro ao carregar dados do cliente');
    } finally {
      setLoading(false);
    }
  }

  async function fetchPlans() {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/plans?active_only=true`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setPlans(data.plans);
      }
    } catch (err) {
      console.error('Erro ao carregar planos:', err);
    }
  }

  async function changePlan() {
    if (!selectedPlan) return;
    
    setActionLoading(true);
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/tenants/${tenantId}/subscription`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ plan: selectedPlan }),
      });

      if (response.ok) {
        alert('Plano alterado com sucesso!');
        setShowChangePlanModal(false);
        fetchTenantDetails();
      } else {
        const error = await response.json();
        alert(error.detail || 'Erro ao alterar plano');
      }
    } catch (err) {
      console.error('Erro ao alterar plano:', err);
      alert('Erro ao alterar plano');
    } finally {
      setActionLoading(false);
    }
  }

  async function extendTrial() {
    setActionLoading(true);
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/tenants/${tenantId}/subscription`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ extend_trial_days: trialDays }),
      });

      if (response.ok) {
        alert(`Trial estendido em ${trialDays} dias!`);
        setShowExtendTrialModal(false);
        fetchTenantDetails();
      } else {
        const error = await response.json();
        alert(error.detail || 'Erro ao estender trial');
      }
    } catch (err) {
      console.error('Erro ao estender trial:', err);
      alert('Erro ao estender trial');
    } finally {
      setActionLoading(false);
    }
  }

  async function resetLimits() {
    if (!confirm('Tem certeza que deseja resetar os limites e desbloquear o cliente?')) {
      return;
    }

    setActionLoading(true);
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/tenants/${tenantId}/subscription`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reset_limits: true }),
      });

      if (response.ok) {
        alert('Limites resetados com sucesso!');
        fetchTenantDetails();
      } else {
        const error = await response.json();
        alert(error.detail || 'Erro ao resetar limites');
      }
    } catch (err) {
      console.error('Erro ao resetar limites:', err);
      alert('Erro ao resetar limites');
    } finally {
      setActionLoading(false);
    }
  }

  async function toggleTenantStatus() {
    if (!tenant) return;
    
    const action = tenant.active ? 'desativar' : 'ativar';
    if (!confirm(`Tem certeza que deseja ${action} este cliente?`)) {
      return;
    }

    setActionLoading(true);
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/tenants/${tenantId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ active: !tenant.active }),
      });

      if (response.ok) {
        fetchTenantDetails();
      }
    } catch (err) {
      console.error('Erro ao atualizar status:', err);
    } finally {
      setActionLoading(false);
    }
  }

  // Helper functions
  function getUsagePercentage(current: number, limit: number): number {
    if (limit === -1) return 0; // Unlimited
    if (limit === 0) return 100;
    return Math.min((current / limit) * 100, 100);
  }

  function getUsageColor(percentage: number): string {
    if (percentage >= 100) return 'bg-red-500';
    if (percentage >= 80) return 'bg-yellow-500';
    return 'bg-green-500';
  }

  function getUsageTextColor(percentage: number): string {
    if (percentage >= 100) return 'text-red-600';
    if (percentage >= 80) return 'text-yellow-600';
    return 'text-green-600';
  }

  function getQualificationBadge(qualification: string) {
    const badges: Record<string, { bg: string; text: string; label: string }> = {
      hot: { bg: 'bg-red-100', text: 'text-red-700', label: '🔥 Hot' },
      warm: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: '🟡 Warm' },
      cold: { bg: 'bg-blue-100', text: 'text-blue-700', label: '🔵 Cold' },
    };
    return badges[qualification] || badges.cold;
  }

  function getStatusBadge(status: string) {
    const badges: Record<string, { bg: string; text: string; label: string }> = {
      new: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Novo' },
      in_progress: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Em Atendimento' },
      qualified: { bg: 'bg-green-100', text: 'text-green-700', label: 'Qualificado' },
      converted: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Convertido' },
      lost: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Perdido' },
    };
    return badges[status] || badges.new;
  }

  function formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  }

  function formatDateTime(dateString: string): string {
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  const planColors: Record<string, string> = {
    essencial: 'bg-gray-100 text-gray-700 border-gray-300',
    starter: 'bg-gray-100 text-gray-700 border-gray-300', // backward compatibility
    professional: 'bg-blue-100 text-blue-700 border-blue-300',
    enterprise: 'bg-purple-100 text-purple-700 border-purple-300',
  };

  const planLabels: Record<string, string> = {
    essencial: 'Essencial',
    starter: 'Starter', // backward compatibility
    professional: 'Professional',
    enterprise: 'Enterprise',
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  if (error || !tenant) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <XCircle className="w-16 h-16 text-red-500" />
        <p className="text-gray-600">{error || 'Cliente não encontrado'}</p>
        <button
          onClick={() => router.push('/dashboard/clients')}
          className="text-purple-600 hover:underline"
        >
          Voltar para lista
        </button>
      </div>
    );
  }

  // Calculate usage
  const leadsLimit = tenant.plan_limits?.leads_per_month || 100;
  const messagesLimit = tenant.plan_limits?.messages_per_month || 1000;
  const sellersLimit = tenant.plan_limits?.sellers || 2;
  
  const leadsUsed = tenant.usage?.leads_count || 0;
  const messagesUsed = tenant.usage?.messages_count || 0;
  const sellersUsed = tenant.sellers_count || 0;

  const leadsPercentage = getUsagePercentage(leadsUsed, leadsLimit);
  const messagesPercentage = getUsagePercentage(messagesUsed, messagesLimit);
  const sellersPercentage = getUsagePercentage(sellersUsed, sellersLimit);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.push('/dashboard/clients')}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{tenant.name}</h1>
            <span className={`px-3 py-1 rounded-full text-xs font-medium border ${planColors[tenant.plan] || planColors.starter}`}>
              {planLabels[tenant.plan] || tenant.plan}
            </span>
            {tenant.active ? (
              <span className="flex items-center gap-1 text-green-600 text-sm">
                <CheckCircle className="w-4 h-4" />
                Ativo
              </span>
            ) : (
              <span className="flex items-center gap-1 text-red-500 text-sm">
                <XCircle className="w-4 h-4" />
                Inativo
              </span>
            )}
          </div>
          <p className="text-gray-500 text-sm mt-1">
            {tenant.slug} • Criado em {formatDate(tenant.created_at)}
          </p>
        </div>
        <button
          onClick={() => fetchTenantDetails()}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="Atualizar"
        >
          <RefreshCw className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {/* Trial / Subscription Status */}
      {tenant.subscription && (
        <div className={`rounded-xl p-4 border ${
          tenant.subscription.is_blocked 
            ? 'bg-red-50 border-red-200' 
            : tenant.subscription.is_trial 
              ? 'bg-blue-50 border-blue-200' 
              : 'bg-green-50 border-green-200'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {tenant.subscription.is_blocked ? (
                <>
                  <AlertTriangle className="w-6 h-6 text-red-600" />
                  <div>
                    <p className="font-semibold text-red-700">Cliente Bloqueado</p>
                    <p className="text-sm text-red-600">
                      Motivo: {tenant.subscription.limit_exceeded_reason || 'Limite excedido'}
                    </p>
                  </div>
                </>
              ) : tenant.subscription.is_trial ? (
                <>
                  <Clock className="w-6 h-6 text-blue-600" />
                  <div>
                    <p className="font-semibold text-blue-700">Período de Teste</p>
                    <p className="text-sm text-blue-600">
                      {tenant.subscription.days_remaining_trial > 0 
                        ? `${tenant.subscription.days_remaining_trial} dias restantes`
                        : 'Trial expirado'}
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <CheckCircle className="w-6 h-6 text-green-600" />
                  <div>
                    <p className="font-semibold text-green-700">Assinatura Ativa</p>
                    <p className="text-sm text-green-600">
                      Ciclo: {tenant.subscription.billing_cycle === 'yearly' ? 'Anual' : 'Mensal'}
                    </p>
                  </div>
                </>
              )}
            </div>
            <div className="flex gap-2">
              {tenant.subscription.is_trial && (
                <button
                  onClick={() => setShowExtendTrialModal(true)}
                  className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Estender Trial
                </button>
              )}
              {tenant.subscription.is_blocked && (
                <button
                  onClick={resetLimits}
                  disabled={actionLoading}
                  className="px-3 py-1.5 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  Desbloquear
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Usage Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Leads */}
        <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Users className="w-5 h-5 text-purple-600" />
              </div>
              <span className="font-medium text-gray-700">Leads</span>
            </div>
            <span className={`text-sm font-semibold ${getUsageTextColor(leadsPercentage)}`}>
              {leadsPercentage.toFixed(0)}%
            </span>
          </div>
          <div className="mb-2">
            <span className="text-2xl font-bold text-gray-900">{leadsUsed}</span>
            <span className="text-gray-500">
              {leadsLimit === -1 ? ' / ∞' : ` / ${leadsLimit}`}
            </span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div 
              className={`h-full ${getUsageColor(leadsPercentage)} transition-all`}
              style={{ width: `${Math.min(leadsPercentage, 100)}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">Este mês</p>
        </div>

        {/* Messages */}
        <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-blue-100 rounded-lg">
                <MessageSquare className="w-5 h-5 text-blue-600" />
              </div>
              <span className="font-medium text-gray-700">Mensagens</span>
            </div>
            <span className={`text-sm font-semibold ${getUsageTextColor(messagesPercentage)}`}>
              {messagesPercentage.toFixed(0)}%
            </span>
          </div>
          <div className="mb-2">
            <span className="text-2xl font-bold text-gray-900">{messagesUsed}</span>
            <span className="text-gray-500">
              {messagesLimit === -1 ? ' / ∞' : ` / ${messagesLimit}`}
            </span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div 
              className={`h-full ${getUsageColor(messagesPercentage)} transition-all`}
              style={{ width: `${Math.min(messagesPercentage, 100)}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">Este mês</p>
        </div>

        {/* Sellers */}
        <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-green-100 rounded-lg">
                <UserPlus className="w-5 h-5 text-green-600" />
              </div>
              <span className="font-medium text-gray-700">Vendedores</span>
            </div>
            <span className={`text-sm font-semibold ${getUsageTextColor(sellersPercentage)}`}>
              {sellersPercentage.toFixed(0)}%
            </span>
          </div>
          <div className="mb-2">
            <span className="text-2xl font-bold text-gray-900">{sellersUsed}</span>
            <span className="text-gray-500">
              {sellersLimit === -1 ? ' / ∞' : ` / ${sellersLimit}`}
            </span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div 
              className={`h-full ${getUsageColor(sellersPercentage)} transition-all`}
              style={{ width: `${Math.min(sellersPercentage, 100)}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">Ativos</p>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Team */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <Users className="w-5 h-5 text-purple-600" />
              Equipe ({tenant.users_count} usuários, {tenant.sellers_count} vendedores)
            </h2>
          </div>
          <div className="p-4 space-y-4 max-h-80 overflow-y-auto">
            {/* Users */}
            {tenant.users && tenant.users.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Usuários</p>
                {tenant.users.map((user) => (
                  <div key={user.id} className="flex items-center justify-between py-2">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                        <span className="text-purple-600 font-medium text-sm">
                          {user.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{user.name}</p>
                        <p className="text-xs text-gray-500">{user.email}</p>
                      </div>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      user.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-700'
                    }`}>
                      {user.role === 'admin' ? 'Admin' : 'Usuário'}
                    </span>
                  </div>
                ))}
              </div>
            )}
            
            {/* Sellers */}
            {tenant.sellers && tenant.sellers.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Vendedores</p>
                {tenant.sellers.map((seller) => (
                  <div key={seller.id} className="flex items-center justify-between py-2">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                        <span className="text-green-600 font-medium text-sm">
                          {seller.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{seller.name}</p>
                        <p className="text-xs text-gray-500">
                          {seller.leads_count} leads atribuídos
                        </p>
                      </div>
                    </div>
                    {seller.active ? (
                      <span className="text-xs text-green-600">Ativo</span>
                    ) : (
                      <span className="text-xs text-gray-400">Inativo</span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {(!tenant.users || tenant.users.length === 0) && (!tenant.sellers || tenant.sellers.length === 0) && (
              <p className="text-gray-500 text-sm text-center py-4">Nenhum membro cadastrado</p>
            )}
          </div>
        </div>

        {/* Recent Leads */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <Target className="w-5 h-5 text-purple-600" />
              Leads Recentes ({tenant.leads_count} total)
            </h2>
          </div>
          <div className="p-4 space-y-2 max-h-80 overflow-y-auto">
            {tenant.recent_leads && tenant.recent_leads.length > 0 ? (
              tenant.recent_leads.map((lead) => {
                const qualBadge = getQualificationBadge(lead.qualification);
                const statusBadge = getStatusBadge(lead.status);
                return (
                  <div key={lead.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {lead.name || 'Sem nome'}
                      </p>
                      <p className="text-xs text-gray-500">
                        {lead.phone || 'Sem telefone'} • {formatDateTime(lead.created_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-1 rounded-full ${qualBadge.bg} ${qualBadge.text}`}>
                        {qualBadge.label}
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-gray-500 text-sm text-center py-4">Nenhum lead cadastrado</p>
            )}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Settings className="w-5 h-5 text-gray-600" />
          Ações
        </h2>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => {
              setSelectedPlan(tenant.plan);
              setShowChangePlanModal(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100 transition-colors"
          >
            <Crown className="w-4 h-4" />
            Mudar Plano
          </button>
          
          {tenant.subscription?.is_trial && (
            <button
              onClick={() => setShowExtendTrialModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
            >
              <Clock className="w-4 h-4" />
              Estender Trial
            </button>
          )}
          
          <button
            onClick={resetLimits}
            disabled={actionLoading}
            className="flex items-center gap-2 px-4 py-2 bg-yellow-50 text-yellow-700 rounded-lg hover:bg-yellow-100 transition-colors disabled:opacity-50"
          >
            <RefreshCw className="w-4 h-4" />
            Resetar Limites
          </button>
          
          <button
            onClick={toggleTenantStatus}
            disabled={actionLoading}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors disabled:opacity-50 ${
              tenant.active 
                ? 'bg-red-50 text-red-700 hover:bg-red-100' 
                : 'bg-green-50 text-green-700 hover:bg-green-100'
            }`}
          >
            {tenant.active ? (
              <>
                <XCircle className="w-4 h-4" />
                Desativar Cliente
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4" />
                Ativar Cliente
              </>
            )}
          </button>
        </div>
      </div>

      {/* Modal: Change Plan */}
      {showChangePlanModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Mudar Plano</h2>
            
            <div className="space-y-3 mb-6">
              {plans.map((plan) => (
                <label
                  key={plan.slug}
                  className={`flex items-center gap-3 p-4 border rounded-lg cursor-pointer transition-colors ${
                    selectedPlan === plan.slug 
                      ? 'border-purple-500 bg-purple-50' 
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="plan"
                    value={plan.slug}
                    checked={selectedPlan === plan.slug}
                    onChange={(e) => setSelectedPlan(e.target.value)}
                    className="text-purple-600"
                  />
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{plan.name}</p>
                    <p className="text-sm text-gray-500">
                      {plan.limits.leads_per_month === -1 ? '∞' : plan.limits.leads_per_month} leads, 
                      {plan.limits.messages_per_month === -1 ? ' ∞' : ` ${plan.limits.messages_per_month}`} msgs, 
                      {plan.limits.sellers === -1 ? ' ∞' : ` ${plan.limits.sellers}`} vendedores
                    </p>
                  </div>
                </label>
              ))}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowChangePlanModal(false)}
                className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={changePlan}
                disabled={actionLoading || selectedPlan === tenant.plan}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
              >
                {actionLoading ? 'Salvando...' : 'Confirmar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Extend Trial */}
      {showExtendTrialModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Estender Trial</h2>
            
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Quantos dias adicionar?
              </label>
              <div className="flex gap-2">
                {[7, 15, 30].map((days) => (
                  <button
                    key={days}
                    onClick={() => setTrialDays(days)}
                    className={`flex-1 py-2 rounded-lg border transition-colors ${
                      trialDays === days 
                        ? 'border-blue-500 bg-blue-50 text-blue-700' 
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {days} dias
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowExtendTrialModal(false)}
                className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={extendTrial}
                disabled={actionLoading}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {actionLoading ? 'Salvando...' : `Adicionar ${trialDays} dias`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}