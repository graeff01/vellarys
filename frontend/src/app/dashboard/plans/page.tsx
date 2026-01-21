'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  CreditCard, 
  Plus, 
  Check,
  X,
  ChevronDown,
  ChevronUp,
  Edit,
  Star,
  Users,
  MessageSquare,
  UserPlus,
  Zap,
  Shield,
  BarChart3,
  Code,
  Headphones,
  Palette
} from 'lucide-react';
import { getToken, getUser } from '@/lib/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Plan {
  id: number;
  slug: string;
  name: string;
  description: string;
  price_monthly: number;
  price_yearly: number;
  limits: {
    leads_per_month: number;
    messages_per_month: number;
    sellers: number;
    ai_tokens_per_month: number;
  };
  features: {
    [key: string]: boolean | string;
  };
  sort_order: number;
  is_featured: boolean;
  active: boolean;
  created_at: string;
}

const defaultPlan = {
  name: '',
  slug: '',
  description: '',
  price_monthly: 0,
  price_yearly: 0,
  sort_order: 0,
  is_featured: false,
  limits: {
    leads_per_month: 100,
    messages_per_month: 1000,
    sellers: 2,
    ai_tokens_per_month: 100000,
  },
  features: {
    ai_qualification: false,
    whatsapp_integration: false,
    web_chat: false,
    push_notifications: false,
    basic_reports: false,
    lead_export: false,
    appointment_booking: false,
    calendar_integration: false,
    reengagement: false,
    advanced_reports: false,
    humanized_voice: false,
    multi_channel: false,
    semantic_search: false,
    api_access: false,
    white_label: false,
    priority_support: false,
  },
};

export default function PlansPage() {
  const router = useRouter();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  
  // Modal states
  const [showModal, setShowModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<Plan | null>(null);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState(defaultPlan);

  useEffect(() => {
    const user = getUser();
    if (user?.role !== 'superadmin') {
      router.push('/dashboard');
      return;
    }
    fetchPlans();
  }, [router]);

  async function fetchPlans() {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/plans`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setPlans(data.plans);
      }
    } catch (err) {
      console.error('Erro ao carregar planos:', err);
    } finally {
      setLoading(false);
    }
  }

  async function savePlan() {
    if (!formData.name || !formData.slug) {
      alert('Preencha nome e slug');
      return;
    }

    setSaving(true);
    try {
      const token = getToken();
      const url = editingPlan 
        ? `${API_URL}/admin/plans/${editingPlan.id}`
        : `${API_URL}/admin/plans`;
      
      const method = editingPlan ? 'PATCH' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setShowModal(false);
        setEditingPlan(null);
        setFormData(defaultPlan);
        fetchPlans();
      } else {
        const error = await response.json();
        alert(error.detail || 'Erro ao salvar plano');
      }
    } catch (err) {
      console.error('Erro ao salvar plano:', err);
      alert('Erro ao salvar plano');
    } finally {
      setSaving(false);
    }
  }

  async function togglePlan(plan: Plan) {
    const action = plan.active ? 'desativar' : 'ativar';
    if (!confirm(`Tem certeza que deseja ${action} o plano "${plan.name}"?`)) {
      return;
    }

    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/plans/${plan.id}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ active: !plan.active }),
      });

      if (response.ok) {
        fetchPlans();
      } else {
        const error = await response.json();
        alert(error.detail || 'Erro ao atualizar plano');
      }
    } catch (err) {
      console.error('Erro ao atualizar plano:', err);
    }
  }

  function openEditModal(plan: Plan) {
    setEditingPlan(plan);
    setFormData({
      name: plan.name,
      slug: plan.slug,
      description: plan.description || '',
      price_monthly: plan.price_monthly,
      price_yearly: plan.price_yearly,
      sort_order: plan.sort_order,
      is_featured: plan.is_featured,
      limits: { ...plan.limits },
      features: { ...plan.features },
    });
    setShowModal(true);
  }

  function openCreateModal() {
    setEditingPlan(null);
    setFormData(defaultPlan);
    setShowModal(true);
  }

  function generateSlug(name: string) {
    return name
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
  }

  function formatCurrency(value: number) {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value);
  }

  function formatLimit(value: number) {
    if (value === -1) return '∞';
    return value.toLocaleString('pt-BR');
  }

  const featureLabels: Record<string, { label: string; icon: React.ReactNode; category: string }> = {
    // Básicas
    ai_qualification: { label: 'Qualificação IA', icon: <Zap className="w-4 h-4" />, category: 'Básico' },
    whatsapp_integration: { label: 'WhatsApp', icon: <MessageSquare className="w-4 h-4" />, category: 'Básico' },
    web_chat: { label: 'Chat Web', icon: <MessageSquare className="w-4 h-4" />, category: 'Básico' },
    push_notifications: { label: 'Notificações', icon: <Zap className="w-4 h-4" />, category: 'Básico' },
    basic_reports: { label: 'Relatórios Básicos', icon: <BarChart3 className="w-4 h-4" />, category: 'Básico' },
    lead_export: { label: 'Exportar Leads', icon: <Users className="w-4 h-4" />, category: 'Básico' },

    // Avançadas
    appointment_booking: { label: 'Agendamento de Visitas', icon: <Check className="w-4 h-4" />, category: 'Avançado' },
    calendar_integration: { label: 'Google Calendar', icon: <Check className="w-4 h-4" />, category: 'Avançado' },
    reengagement: { label: 'Reengajamento Auto', icon: <Zap className="w-4 h-4" />, category: 'Avançado' },
    advanced_reports: { label: 'Relatórios Avançados', icon: <BarChart3 className="w-4 h-4" />, category: 'Avançado' },
    humanized_voice: { label: 'Voz Humanizada', icon: <Headphones className="w-4 h-4" />, category: 'Avançado' },
    multi_channel: { label: 'Multicanal', icon: <MessageSquare className="w-4 h-4" />, category: 'Avançado' },
    semantic_search: { label: 'Busca Semântica', icon: <Zap className="w-4 h-4" />, category: 'Avançado' },

    // Enterprise
    api_access: { label: 'API Completa', icon: <Code className="w-4 h-4" />, category: 'Enterprise' },
    webhooks: { label: 'Webhooks', icon: <Code className="w-4 h-4" />, category: 'Enterprise' },
    white_label: { label: 'White Label', icon: <Palette className="w-4 h-4" />, category: 'Enterprise' },
    priority_support: { label: 'Suporte Prioritário', icon: <Headphones className="w-4 h-4" />, category: 'Enterprise' },
    account_manager: { label: 'Account Manager', icon: <UserPlus className="w-4 h-4" />, category: 'Enterprise' },
    custom_integrations: { label: 'Integrações Custom', icon: <Shield className="w-4 h-4" />, category: 'Enterprise' },
    appointment_auto_create: { label: 'Agendamento Automático', icon: <Check className="w-4 h-4" />, category: 'Enterprise' },
    appointment_reminders: { label: 'Lembretes Automáticos', icon: <Zap className="w-4 h-4" />, category: 'Enterprise' },
    calendar_email_invites: { label: 'Convites por Email', icon: <MessageSquare className="w-4 h-4" />, category: 'Enterprise' },
    sla_99_5: { label: 'SLA 99.5%', icon: <Shield className="w-4 h-4" />, category: 'Enterprise' },
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Planos</h1>
          <p className="text-gray-600">Gerencie os planos de assinatura disponíveis</p>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5" />
          Novo Plano
        </button>
      </div>

      {/* Plans Grid */}
      <div className="grid gap-4">
        {loading ? (
          <div className="text-center text-gray-500 py-8">Carregando...</div>
        ) : plans.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <p>Nenhum plano cadastrado</p>
            <button
              onClick={async () => {
                const token = getToken();
                await fetch(`${API_URL}/admin/plans/seed-defaults`, {
                  method: 'POST',
                  headers: { 'Authorization': `Bearer ${token}` },
                });
                fetchPlans();
              }}
              className="mt-2 text-purple-600 hover:underline"
            >
              Criar planos padrão
            </button>
          </div>
        ) : (
          plans.map((plan) => (
            <div
              key={plan.id}
              className={`bg-white rounded-xl shadow-sm border overflow-hidden ${
                plan.is_featured ? 'border-purple-300 ring-2 ring-purple-100' : 'border-gray-200'
              }`}
            >
              {/* Header do Card */}
              <div 
                className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
                onClick={() => setExpandedId(expandedId === plan.id ? null : plan.id)}
              >
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                    plan.slug === 'enterprise' ? 'bg-purple-100' :
                    plan.slug === 'professional' ? 'bg-blue-100' :
                    'bg-gray-100'
                  }`}>
                    <CreditCard className={`w-6 h-6 ${
                      plan.slug === 'enterprise' ? 'text-purple-600' :
                      plan.slug === 'professional' ? 'text-blue-600' :
                      'text-gray-600'
                    }`} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
                      {plan.is_featured && (
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full font-medium">
                          <Star className="w-3 h-3" />
                          Popular
                        </span>
                      )}
                    </div>
                    <p className="text-gray-500 text-sm">
                      {formatCurrency(plan.price_monthly)}/mês • {formatCurrency(plan.price_yearly)}/ano
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="hidden md:flex items-center gap-4 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      {formatLimit(plan.limits.leads_per_month)} leads
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare className="w-4 h-4" />
                      {formatLimit(plan.limits.messages_per_month)} msgs
                    </span>
                    <span className="flex items-center gap-1">
                      <UserPlus className="w-4 h-4" />
                      {formatLimit(plan.limits.sellers)} vendedores
                    </span>
                  </div>
                  
                  {plan.active ? (
                    <span className="flex items-center gap-1 text-green-600 text-sm">
                      <Check className="w-4 h-4" />
                      Ativo
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-red-500 text-sm">
                      <X className="w-4 h-4" />
                      Inativo
                    </span>
                  )}
                  
                  {expandedId === plan.id ? (
                    <ChevronUp className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  )}
                </div>
              </div>

              {/* Conteúdo Expandido */}
              {expandedId === plan.id && (
                <div className="px-4 pb-4 border-t border-gray-100 pt-4">
                  {/* Descrição */}
                  {plan.description && (
                    <p className="text-gray-600 mb-4">{plan.description}</p>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Limites */}
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-3">Limites</h4>
                      <div className="space-y-2">
                        <div className="flex justify-between py-2 border-b border-gray-100">
                          <span className="text-gray-600 flex items-center gap-2">
                            <Users className="w-4 h-4" /> Leads/mês
                          </span>
                          <span className="font-medium text-gray-900">
                            {formatLimit(plan.limits.leads_per_month)}
                          </span>
                        </div>
                        <div className="flex justify-between py-2 border-b border-gray-100">
                          <span className="text-gray-600 flex items-center gap-2">
                            <MessageSquare className="w-4 h-4" /> Mensagens/mês
                          </span>
                          <span className="font-medium text-gray-900">
                            {formatLimit(plan.limits.messages_per_month)}
                          </span>
                        </div>
                        <div className="flex justify-between py-2 border-b border-gray-100">
                          <span className="text-gray-600 flex items-center gap-2">
                            <UserPlus className="w-4 h-4" /> Corretores
                          </span>
                          <span className="font-medium text-gray-900">
                            {formatLimit(plan.limits.sellers)}
                          </span>
                        </div>
                        <div className="flex justify-between py-2">
                          <span className="text-gray-600 flex items-center gap-2">
                            <Zap className="w-4 h-4" /> Tokens IA/mês
                          </span>
                          <span className="font-medium text-gray-900">
                            {formatLimit(plan.limits.ai_tokens_per_month)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Features */}
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-3">Features Incluídas</h4>
                      <div className="space-y-3">
                        {/* Agrupar features por categoria */}
                        {['Básico', 'Avançado', 'Enterprise'].map((category) => {
                          const categoryFeatures = Object.entries(featureLabels).filter(
                            ([, data]) => data.category === category
                          );

                          const hasAnyFeature = categoryFeatures.some(
                            ([key]) => plan.features[key]
                          );

                          if (!hasAnyFeature) return null;

                          return (
                            <div key={category}>
                              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{category}</p>
                              <div className="space-y-1">
                                {categoryFeatures.map(([key, { label, icon }]) => {
                                  const isEnabled = plan.features[key];
                                  if (!isEnabled) return null;

                                  return (
                                    <div key={key} className="flex items-center gap-2 text-sm">
                                      <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                                      <span className="text-gray-700">{label}</span>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Info adicional */}
                  <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between text-sm text-gray-500">
                    <span>Ordem: {plan.sort_order}</span>
                    <span>Criado em: {plan.created_at ? new Date(plan.created_at).toLocaleDateString('pt-BR') : '-'}</span>
                  </div>

                  {/* Ações */}
                  <div className="flex gap-3 mt-4 pt-4 border-t border-gray-100">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openEditModal(plan);
                      }}
                      className="flex items-center gap-2 px-4 py-2 bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-colors"
                    >
                      <Edit className="w-4 h-4" />
                      Editar
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        togglePlan(plan);
                      }}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        plan.active
                          ? 'bg-red-50 text-red-600 hover:bg-red-100'
                          : 'bg-green-50 text-green-600 hover:bg-green-100'
                      }`}
                    >
                      {plan.active ? 'Desativar' : 'Ativar'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Modal Criar/Editar Plano */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              {editingPlan ? 'Editar Plano' : 'Novo Plano'}
            </h2>

            <div className="space-y-6">
              {/* Dados Básicos */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">Dados Básicos</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => {
                        setFormData({
                          ...formData,
                          name: e.target.value,
                          slug: editingPlan ? formData.slug : generateSlug(e.target.value),
                        });
                      }}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="Ex: Professional"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Slug</label>
                    <input
                      type="text"
                      value={formData.slug}
                      onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                      disabled={!!editingPlan}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:bg-gray-100"
                      placeholder="professional"
                    />
                  </div>
                </div>
                
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="Breve descrição do plano"
                  />
                </div>
              </div>

              {/* Preços */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">Preços</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Preço Mensal (R$)</label>
                    <input
                      type="number"
                      value={formData.price_monthly}
                      onChange={(e) => setFormData({ ...formData, price_monthly: parseFloat(e.target.value) || 0 })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      min="0"
                      step="0.01"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Preço Anual (R$)</label>
                    <input
                      type="number"
                      value={formData.price_yearly}
                      onChange={(e) => setFormData({ ...formData, price_yearly: parseFloat(e.target.value) || 0 })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      min="0"
                      step="0.01"
                    />
                  </div>
                </div>
              </div>

              {/* Limites */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">
                  Limites 
                  <span className="text-xs font-normal text-gray-500 ml-2">(-1 = ilimitado)</span>
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Leads/mês</label>
                    <input
                      type="number"
                      value={formData.limits.leads_per_month}
                      onChange={(e) => setFormData({
                        ...formData,
                        limits: { ...formData.limits, leads_per_month: parseInt(e.target.value) || 0 }
                      })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      min="-1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Mensagens/mês</label>
                    <input
                      type="number"
                      value={formData.limits.messages_per_month}
                      onChange={(e) => setFormData({
                        ...formData,
                        limits: { ...formData.limits, messages_per_month: parseInt(e.target.value) || 0 }
                      })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      min="-1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Corretores</label>
                    <input
                      type="number"
                      value={formData.limits.sellers}
                      onChange={(e) => setFormData({
                        ...formData,
                        limits: { ...formData.limits, sellers: parseInt(e.target.value) || 0 }
                      })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      min="-1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Tokens IA/mês</label>
                    <input
                      type="number"
                      value={formData.limits.ai_tokens_per_month}
                      onChange={(e) => setFormData({
                        ...formData,
                        limits: { ...formData.limits, ai_tokens_per_month: parseInt(e.target.value) || 0 }
                      })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      min="-1"
                    />
                  </div>
                </div>
              </div>

              {/* Features */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">Features</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {Object.entries(featureLabels).map(([key, { label, icon }]) => (
                    <label
                      key={key}
                      className={`flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors ${
                        (formData.features[key as keyof typeof formData.features] || false)
                          ? 'border-purple-500 bg-purple-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={formData.features[key as keyof typeof formData.features] || false}
                        onChange={(e) => setFormData({
                          ...formData,
                          features: { ...formData.features, [key]: e.target.checked }
                        })}
                        className="sr-only"
                      />
                      <span className={(formData.features[key as keyof typeof formData.features] || false) ? 'text-purple-600' : 'text-gray-400'}>
                        {icon}
                      </span>
                      <span className={`text-sm ${(formData.features[key as keyof typeof formData.features] || false) ? 'text-purple-700' : 'text-gray-600'}`}>
                        {label}
                      </span>
                      {(formData.features[key as keyof typeof formData.features] || false) && (
                        <Check className="w-4 h-4 text-purple-600 ml-auto" />
                      )}
                    </label>
                  ))}
                </div>
              </div>

              {/* Opções */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">Opções</h3>
                <div className="flex flex-wrap gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Ordem de exibição</label>
                    <input
                      type="number"
                      value={formData.sort_order}
                      onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
                      className="w-24 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      min="0"
                    />
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
                      <input
                        type="checkbox"
                        checked={formData.is_featured}
                        onChange={(e) => setFormData({ ...formData, is_featured: e.target.checked })}
                        className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                      />
                      <Star className="w-4 h-4 text-yellow-500" />
                      <span className="text-sm text-gray-700">Plano em destaque</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6 pt-4 border-t border-gray-200">
              <button
                onClick={() => {
                  setShowModal(false);
                  setEditingPlan(null);
                  setFormData(defaultPlan);
                }}
                className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={savePlan}
                disabled={saving}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
              >
                {saving ? 'Salvando...' : editingPlan ? 'Salvar Alterações' : 'Criar Plano'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}