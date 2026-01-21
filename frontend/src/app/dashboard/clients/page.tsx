'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Building2,
  Plus,
  Search,
  Check,
  X,
  Users,
  MessageSquare,
  Eye,
  Mail,
  Lock,
  User,
  Phone,
  Key,
  Edit,
  Smartphone,
  Bot,
  Sparkles
} from 'lucide-react';
import { getToken, getUser } from '@/lib/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Tenant {
  id: number;
  name: string;
  slug: string;
  plan: string;
  active: boolean;
  settings: Record<string, unknown>;
  leads_count: number;
  users_count: number;
  created_at: string;
}

interface Niche {
  id: number;
  name: string;
  slug: string;
  icon?: string;
}

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
  features: Record<string, boolean | string>;
  sort_order: number;
  is_featured: boolean;
  active: boolean;
}

type WhatsAppProvider = 'none' | '360dialog' | 'zapi';

interface TenantFormState {
  name: string;
  slug: string;
  plan: string;
  niche: string;
  admin_name: string;
  admin_email: string;
  admin_password: string;

  // Integração WhatsApp
  whatsapp_provider: WhatsAppProvider;
  whatsapp_number: string;

  // 360dialog
  dialog360_api_key: string;
  webhook_verify_token: string;

  // Z-API
  zapi_instance_id: string;
  zapi_token: string;
}

const initialFormState: TenantFormState = {
  name: '',
  slug: '',
  plan: 'professional', // Padrão é Professional (melhor custo-benefício)
  niche: '',
  admin_name: '',
  admin_email: '',
  admin_password: '',
  whatsapp_provider: 'none',
  whatsapp_number: '',
  dialog360_api_key: '',
  webhook_verify_token: '',
  zapi_instance_id: '',
  zapi_token: '',
};

export default function ClientsPage() {
  const router = useRouter();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [niches, setNiches] = useState<Niche[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Modo: criar ou editar
  const [editingTenantId, setEditingTenantId] = useState<number | null>(null);
  const [formData, setFormData] = useState<TenantFormState>(initialFormState);

  const isEditing = editingTenantId !== null;

  useEffect(() => {
    const user = getUser();
    if (user?.role !== 'superadmin') {
      router.push('/dashboard');
      return;
    }
    fetchTenants();
    fetchNiches();
    fetchPlans();
  }, [router]);

  async function fetchTenants() {
    try {
      const token = getToken();
      const params = new URLSearchParams();
      if (search) params.set('search', search);

      const response = await fetch(`${API_URL}/admin/tenants?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setTenants(data.tenants);
      }
    } catch (err) {
      console.error('Erro ao carregar clientes:', err);
    } finally {
      setLoading(false);
    }
  }

  async function fetchNiches() {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/niches?active_only=true`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setNiches(data.niches);
      }
    } catch (err) {
      console.error('Erro ao carregar nichos:', err);
    }
  }

  async function fetchPlans() {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/plans`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        // Filtra apenas planos ativos e ordena por sort_order
        const activePlans = data.plans
          .filter((p: Plan) => p.active)
          .sort((a: Plan, b: Plan) => a.sort_order - b.sort_order);
        setPlans(activePlans);
      }
    } catch (err) {
      console.error('Erro ao carregar planos:', err);
    }
  }

  async function fetchTenantDetails(tenantId: number) {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/tenants/${tenantId}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        return data;
      }
    } catch (err) {
      console.error('Erro ao carregar detalhes do cliente:', err);
    }
    return null;
  }

  function openCreateModal() {
    setEditingTenantId(null);
    setFormData(initialFormState);
    setShowPassword(false);
    setShowModal(true);
  }

  async function openEditModal(tenant: Tenant) {
    // Busca detalhes completos do tenant
    const details = await fetchTenantDetails(tenant.id);

    if (!details) {
      alert('Erro ao carregar dados do cliente');
      return;
    }

    const settings = details.settings || {};

    // Determina qual provider está configurado
    let provider: WhatsAppProvider = 'none';
    if (settings.zapi_instance_id && settings.zapi_token) {
      provider = 'zapi';
    } else if (settings.dialog360_api_key) {
      provider = '360dialog';
    }

    setEditingTenantId(tenant.id);
    setFormData({
      name: details.name || '',
      slug: details.slug || '',
      plan: details.plan || 'essencial',
      niche: settings.niche || '',
      admin_name: '', // Não editável
      admin_email: '', // Não editável
      admin_password: '', // Não editável
      whatsapp_provider: provider,
      whatsapp_number: settings.whatsapp_number || '',
      dialog360_api_key: settings.dialog360_api_key || '',
      webhook_verify_token: settings.webhook_verify_token || 'velaris_webhook_token',
      zapi_instance_id: settings.zapi_instance_id || '',
      zapi_token: settings.zapi_token || '',
    });
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setEditingTenantId(null);
    setFormData(initialFormState);
    setShowPassword(false);
  }

  async function handleSubmit() {
    if (isEditing) {
      await updateTenant();
    } else {
      await createTenant();
    }
  }

  async function createTenant() {
    // Validações básicas
    if (!formData.name || !formData.slug) {
      alert('Preencha o nome e o slug da empresa.');
      return;
    }
    if (!formData.niche) {
      alert('Selecione um nicho.');
      return;
    }
    if (!formData.admin_name || !formData.admin_email || !formData.admin_password) {
      alert('Preencha os dados do administrador do cliente.');
      return;
    }
    if (formData.admin_password.length < 6) {
      alert('A senha deve ter pelo menos 6 caracteres.');
      return;
    }

    // Validação de integração WhatsApp
    if (formData.whatsapp_provider === '360dialog') {
      if (!formData.whatsapp_number || !formData.dialog360_api_key) {
        alert('Para usar 360dialog, preencha o número e a API Key.');
        return;
      }
    } else if (formData.whatsapp_provider === 'zapi') {
      if (!formData.whatsapp_number || !formData.zapi_instance_id || !formData.zapi_token) {
        alert('Para usar Z-API, preencha o número, Instance ID e Token.');
        return;
      }
    }

    setSaving(true);
    try {
      const token = getToken();

      const createPayload = {
        name: formData.name,
        slug: formData.slug,
        plan: formData.plan,
        niche: formData.niche,
        admin_name: formData.admin_name,
        admin_email: formData.admin_email,
        admin_password: formData.admin_password,
        // WhatsApp config
        whatsapp_provider: formData.whatsapp_provider,
        whatsapp_number: formData.whatsapp_number || null,
        // 360dialog
        dialog360_api_key: formData.whatsapp_provider === '360dialog' ? formData.dialog360_api_key : null,
        webhook_verify_token: formData.webhook_verify_token || 'velaris_webhook_token',
        // Z-API
        zapi_instance_id: formData.whatsapp_provider === 'zapi' ? formData.zapi_instance_id : null,
        zapi_token: formData.whatsapp_provider === 'zapi' ? formData.zapi_token : null,
      };

      const response = await fetch(`${API_URL}/admin/tenants`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(createPayload),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => null);
        alert(error?.detail || 'Erro ao criar cliente');
        setSaving(false);
        return;
      }

      const result = await response.json();

      let successMessage = `Cliente criado com sucesso!\n\nEmail de acesso: ${result.user.email}`;

      if (result.whatsapp?.configured) {
        successMessage += `\n\n📱 WhatsApp configurado!\nWebhook URL: ${result.whatsapp.webhook_url}`;
      }

      alert(successMessage);
      closeModal();
      fetchTenants();
    } catch (err) {
      console.error('Erro ao criar cliente:', err);
      alert('Erro ao criar cliente');
    } finally {
      setSaving(false);
    }
  }

  async function updateTenant() {
    if (!editingTenantId) return;

    // Validações básicas
    if (!formData.name) {
      alert('Preencha o nome da empresa.');
      return;
    }

    // Validação de integração WhatsApp
    if (formData.whatsapp_provider === '360dialog') {
      if (!formData.whatsapp_number || !formData.dialog360_api_key) {
        alert('Para usar 360dialog, preencha o número e a API Key.');
        return;
      }
    } else if (formData.whatsapp_provider === 'zapi') {
      if (!formData.whatsapp_number || !formData.zapi_instance_id || !formData.zapi_token) {
        alert('Para usar Z-API, preencha o número, Instance ID e Token.');
        return;
      }
    }

    setSaving(true);
    try {
      const token = getToken();

      // Monta settings para atualizar
      const settings: Record<string, unknown> = {
        niche: formData.niche,
        whatsapp_provider: formData.whatsapp_provider,
        whatsapp_number: formData.whatsapp_number || null,
      };

      // Adiciona config do provider selecionado
      if (formData.whatsapp_provider === '360dialog') {
        settings.dialog360_api_key = formData.dialog360_api_key;
        settings.webhook_verify_token = formData.webhook_verify_token || 'velaris_webhook_token';
        // Limpa Z-API
        settings.zapi_instance_id = null;
        settings.zapi_token = null;
      } else if (formData.whatsapp_provider === 'zapi') {
        settings.zapi_instance_id = formData.zapi_instance_id;
        settings.zapi_token = formData.zapi_token;
        // Limpa 360dialog
        settings.dialog360_api_key = null;
        settings.webhook_verify_token = null;
      } else {
        // Limpa tudo
        settings.dialog360_api_key = null;
        settings.webhook_verify_token = null;
        settings.zapi_instance_id = null;
        settings.zapi_token = null;
      }

      const updatePayload = {
        name: formData.name,
        plan: formData.plan,
        settings: settings,
      };

      const response = await fetch(`${API_URL}/admin/tenants/${editingTenantId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatePayload),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => null);
        alert(error?.detail || 'Erro ao atualizar cliente');
        setSaving(false);
        return;
      }

      // Atualiza também o canal WhatsApp
      await updateWhatsAppChannel(editingTenantId, formData);

      alert('Cliente atualizado com sucesso!');
      closeModal();
      fetchTenants();
    } catch (err) {
      console.error('Erro ao atualizar cliente:', err);
      alert('Erro ao atualizar cliente');
    } finally {
      setSaving(false);
    }
  }

  async function updateWhatsAppChannel(tenantId: number, data: TenantFormState) {
    try {
      const token = getToken();

      // Monta config do canal baseado no provider
      let channelConfig: Record<string, unknown> = {};

      if (data.whatsapp_provider === '360dialog') {
        channelConfig = {
          provider: '360dialog',
          phone_number: data.whatsapp_number,
          api_key: data.dialog360_api_key,
          webhook_verify_token: data.webhook_verify_token || 'velaris_webhook_token',
        };
      } else if (data.whatsapp_provider === 'zapi') {
        channelConfig = {
          provider: 'zapi',
          phone_number: data.whatsapp_number,
          instance_id: data.zapi_instance_id,
          token: data.zapi_token,
        };
      }

      // Atualiza canal via endpoint específico (se existir) ou via settings
      await fetch(`${API_URL}/admin/tenants/${tenantId}/channel`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ config: channelConfig }),
      });
    } catch (err) {
      console.error('Erro ao atualizar canal:', err);
      // Não bloqueia o fluxo principal
    }
  }

  async function toggleTenant(tenant: Tenant) {
    const action = tenant.active ? 'desativar' : 'ativar';
    if (!confirm(`Tem certeza que deseja ${action} "${tenant.name}"?`)) {
      return;
    }

    try {
      const token = getToken();
      await fetch(`${API_URL}/admin/tenants/${tenant.id}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ active: !tenant.active }),
      });
      fetchTenants();
    } catch (err) {
      console.error('Erro ao atualizar cliente:', err);
    }
  }

  function generateSlug(name: string) {
    return name
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
  }

  function generatePassword() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
    let password = '';
    for (let i = 0; i < 10; i++) {
      password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setFormData((prev) => ({ ...prev, admin_password: password }));
    setShowPassword(true);
  }

  // Função helper para obter cor do plano dinamicamente
  function getPlanColor(planSlug: string): string {
    const defaultColors: Record<string, string> = {
      essencial: 'bg-gray-100 text-gray-700',
      starter: 'bg-gray-100 text-gray-700',
      professional: 'bg-blue-100 text-blue-700',
      enterprise: 'bg-purple-100 text-purple-700',
    };
    return defaultColors[planSlug] || 'bg-gray-100 text-gray-700';
  }

  // Função helper para obter label do plano dinamicamente
  function getPlanLabel(planSlug: string): string {
    const plan = plans.find(p => p.slug === planSlug);
    return plan?.name || planSlug.charAt(0).toUpperCase() + planSlug.slice(1);
  }

  function getWebhookUrl(): string {
    if (formData.whatsapp_provider === 'zapi') {
      return 'https://hopeful-purpose-production-3a2b.up.railway.app/api/zapi/receive';
    }
    return 'https://hopeful-purpose-production-3a2b.up.railway.app/api/v1/webhook/360dialog';
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
          <p className="text-gray-600">Gerencie os clientes da plataforma e a integração com a IA.</p>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5" />
          Novo Cliente
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar por nome ou slug..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetchTenants()}
          className="w-full pl-10 pr-4 py-3 bg-white border border-gray-200 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
        />
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-600">Cliente</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-600">Plano</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-600">Leads</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-600">Usuários</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-600">Status</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-600">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                  Carregando...
                </td>
              </tr>
            ) : tenants.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                  Nenhum cliente encontrado
                </td>
              </tr>
            ) : (
              tenants.map((tenant) => (
                <tr key={tenant.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                        <Building2 className="w-5 h-5 text-purple-600" />
                      </div>
                      <div>
                        <p className="text-gray-900 font-medium">{tenant.name}</p>
                        <p className="text-gray-500 text-sm">{tenant.slug}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${getPlanColor(tenant.plan)}`}
                    >
                      {getPlanLabel(tenant.plan)}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 text-gray-600">
                      <Users className="w-4 h-4" />
                      {tenant.leads_count}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 text-gray-600">
                      <MessageSquare className="w-4 h-4" />
                      {tenant.users_count}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {tenant.active ? (
                      <span className="flex items-center gap-1 text-green-600">
                        <Check className="w-4 h-4" />
                        Ativo
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-red-500">
                        <X className="w-4 h-4" />
                        Inativo
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => openEditModal(tenant)}
                        className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Editar cliente"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => router.push(`/dashboard/clients/${tenant.id}`)}
                        className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                        title="Ver detalhes"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => router.push(`/dashboard/settings?target_tenant_id=${tenant.id}`)}
                        className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                        title="Configurar IA"
                      >
                        <Bot className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => router.push(`/dashboard/simulator?target_tenant_id=${tenant.id}`)}
                        className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Simular IA (Venda Live)"
                      >
                        <Sparkles className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => toggleTenant(tenant)}
                        className={`px-3 py-1 rounded text-sm font-medium transition-colors ${tenant.active
                          ? 'bg-red-50 text-red-600 hover:bg-red-100'
                          : 'bg-green-50 text-green-600 hover:bg-green-100'
                          }`}
                      >
                        {tenant.active ? 'Desativar' : 'Ativar'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal Criar/Editar Cliente */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold text-gray-900 mb-6">
              {isEditing ? 'Editar Cliente' : 'Novo Cliente'}
            </h2>

            {/* Dados da Empresa */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                Dados da Empresa
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nome da Empresa *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => {
                      const name = e.target.value;
                      setFormData((prev) => ({
                        ...prev,
                        name,
                        slug: isEditing ? prev.slug : generateSlug(name),
                      }));
                    }}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="Ex: Imobiliária Silva"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Slug (URL) *
                  </label>
                  <input
                    type="text"
                    value={formData.slug}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, slug: e.target.value }))
                    }
                    disabled={isEditing}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:bg-gray-100 disabled:text-gray-500"
                    placeholder="imobiliaria-silva"
                  />
                  {isEditing && (
                    <p className="text-xs text-gray-500 mt-1">O slug não pode ser alterado após criação.</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nicho *
                  </label>
                  <select
                    value={formData.niche}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, niche: e.target.value }))
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="">Selecione um nicho</option>
                    {niches.map((n) => (
                      <option key={n.id} value={n.slug}>
                        {n.icon ? `${n.icon} ${n.name}` : n.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Plano de Assinatura
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {plans.length === 0 ? (
                      <div className="col-span-3 text-center py-8 text-gray-500">
                        Carregando planos...
                      </div>
                    ) : (
                      plans.map((plan) => {
                        const isSelected = formData.plan === plan.slug;
                        const isFeatured = plan.is_featured;

                        // Define cores por slug
                        const colors = {
                          essencial: { border: 'border-gray-200', borderActive: 'border-gray-500', bg: 'bg-gray-50', check: 'text-gray-600' },
                          professional: { border: 'border-blue-200', borderActive: 'border-blue-500', bg: 'bg-blue-50', check: 'text-blue-600' },
                          enterprise: { border: 'border-purple-200', borderActive: 'border-purple-500', bg: 'bg-purple-50', check: 'text-purple-600' },
                        }[plan.slug] || { border: 'border-gray-200', borderActive: 'border-gray-500', bg: 'bg-gray-50', check: 'text-gray-600' };

                        const formatLimit = (value: number) => {
                          if (value === -1) return '∞';
                          return value.toLocaleString('pt-BR');
                        };

                        return (
                          <button
                            key={plan.id}
                            type="button"
                            onClick={() => setFormData((prev) => ({ ...prev, plan: plan.slug }))}
                            className={`relative p-4 rounded-xl border-2 text-left transition-all ${
                              isSelected
                                ? `${colors.borderActive} ${colors.bg} shadow-md`
                                : `${colors.border} hover:border-gray-300`
                            }`}
                          >
                            {isFeatured && (
                              <div className="absolute -top-2 -right-2 bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full font-semibold">
                                POPULAR
                              </div>
                            )}
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="font-semibold text-gray-900">{plan.name}</h4>
                              {isSelected && (
                                <Check className={`w-5 h-5 ${colors.check}`} />
                              )}
                            </div>
                            <p className="text-2xl font-bold text-gray-900 mb-1">
                              {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(plan.price_monthly)}
                            </p>
                            <p className="text-xs text-gray-500 mb-3">/mês</p>
                            <div className="space-y-1 text-xs text-gray-600">
                              <div className="flex items-center gap-1">
                                <Check className="w-3 h-3 text-green-500" />
                                <span>{formatLimit(plan.limits.leads_per_month)} leads/mês</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <Check className="w-3 h-3 text-green-500" />
                                <span>{formatLimit(plan.limits.sellers)} corretores</span>
                              </div>
                              {plan.features.appointment_booking ? (
                                <div className="flex items-center gap-1">
                                  <Check className="w-3 h-3 text-green-500" />
                                  <span>
                                    {plan.features.appointment_mode === 'automatic' ? 'Agendamento automático' : 'Agendamento assistido'}
                                  </span>
                                </div>
                              ) : (
                                <div className="flex items-center gap-1">
                                  <X className="w-3 h-3 text-gray-400" />
                                  <span>Sem agendamento</span>
                                </div>
                              )}
                              {plan.features.humanized_voice && (
                                <div className="flex items-center gap-1">
                                  <Check className="w-3 h-3 text-green-500" />
                                  <span>Voz humanizada</span>
                                </div>
                              )}
                            </div>
                          </button>
                        );
                      })
                    )}
                  </div>

                  {/* Info do plano selecionado */}
                  {plans.length > 0 && formData.plan && (
                    <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <p className="text-sm text-blue-800">
                        {(() => {
                          const selectedPlan = plans.find(p => p.slug === formData.plan);
                          if (!selectedPlan) return null;
                          return (
                            <>
                              <strong>{selectedPlan.name}:</strong> {selectedPlan.description}
                            </>
                          );
                        })()}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Dados do Administrador - Só mostra ao criar */}
            {!isEditing && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                  <User className="w-4 h-4" />
                  Administrador do Cliente
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Nome do Gestor *
                    </label>
                    <input
                      type="text"
                      value={formData.admin_name}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, admin_name: e.target.value }))
                      }
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="Ex: João Silva"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email de Acesso *
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <input
                        type="email"
                        value={formData.admin_email}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, admin_email: e.target.value }))
                        }
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                        placeholder="gestor@empresa.com"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Senha de Acesso *
                    </label>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <input
                          type={showPassword ? 'text' : 'password'}
                          value={formData.admin_password}
                          onChange={(e) =>
                            setFormData((prev) => ({
                              ...prev,
                              admin_password: e.target.value,
                            }))
                          }
                          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                          placeholder="Mínimo 6 caracteres"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={generatePassword}
                        className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm whitespace-nowrap"
                      >
                        Gerar
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowPassword((prev) => !prev)}
                        className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
                      >
                        {showPassword ? 'Ocultar' : 'Ver'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Integração WhatsApp */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                <Smartphone className="w-4 h-4" />
                Integração WhatsApp
              </h3>

              {/* Seletor de Provider */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Provedor de WhatsApp
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setFormData((prev) => ({ ...prev, whatsapp_provider: 'none' }))}
                    className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${formData.whatsapp_provider === 'none'
                      ? 'border-purple-500 bg-purple-50 text-purple-700'
                      : 'border-gray-300 text-gray-700 hover:border-gray-400'
                      }`}
                  >
                    Nenhum
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormData((prev) => ({ ...prev, whatsapp_provider: '360dialog' }))}
                    className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${formData.whatsapp_provider === '360dialog'
                      ? 'border-purple-500 bg-purple-50 text-purple-700'
                      : 'border-gray-300 text-gray-700 hover:border-gray-400'
                      }`}
                  >
                    360dialog
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormData((prev) => ({ ...prev, whatsapp_provider: 'zapi' }))}
                    className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${formData.whatsapp_provider === 'zapi'
                      ? 'border-green-500 bg-green-50 text-green-700'
                      : 'border-gray-300 text-gray-700 hover:border-gray-400'
                      }`}
                  >
                    Z-API
                  </button>
                </div>
              </div>

              {/* Campos comuns (quando provider != none) */}
              {formData.whatsapp_provider !== 'none' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Número do WhatsApp (Business) *
                    </label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <input
                        type="text"
                        value={formData.whatsapp_number}
                        onChange={(e) =>
                          setFormData((prev) => ({
                            ...prev,
                            whatsapp_number: e.target.value,
                          }))
                        }
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                        placeholder="Ex: 5511999998888 (somente dígitos)"
                      />
                    </div>
                  </div>

                  {/* Campos 360dialog */}
                  {formData.whatsapp_provider === '360dialog' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          360dialog API Key *
                        </label>
                        <div className="relative">
                          <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                          <input
                            type="text"
                            value={formData.dialog360_api_key}
                            onChange={(e) =>
                              setFormData((prev) => ({
                                ...prev,
                                dialog360_api_key: e.target.value,
                              }))
                            }
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                            placeholder="Chave de API do 360dialog"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Webhook Verify Token (opcional)
                        </label>
                        <input
                          type="text"
                          value={formData.webhook_verify_token}
                          onChange={(e) =>
                            setFormData((prev) => ({
                              ...prev,
                              webhook_verify_token: e.target.value,
                            }))
                          }
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                          placeholder="velaris_webhook_token (padrão)"
                        />
                      </div>
                    </>
                  )}

                  {/* Campos Z-API */}
                  {formData.whatsapp_provider === 'zapi' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Z-API Instance ID *
                        </label>
                        <div className="relative">
                          <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                          <input
                            type="text"
                            value={formData.zapi_instance_id}
                            onChange={(e) =>
                              setFormData((prev) => ({
                                ...prev,
                                zapi_instance_id: e.target.value,
                              }))
                            }
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                            placeholder="ID da instância Z-API"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Z-API Token *
                        </label>
                        <div className="relative">
                          <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                          <input
                            type="text"
                            value={formData.zapi_token}
                            onChange={(e) =>
                              setFormData((prev) => ({
                                ...prev,
                                zapi_token: e.target.value,
                              }))
                            }
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                            placeholder="Token da instância Z-API"
                          />
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Info box */}
            {formData.whatsapp_provider !== 'none' && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <p className="text-sm text-blue-700">
                  <strong>Webhook URL:</strong> Configure no painel do {formData.whatsapp_provider === 'zapi' ? 'Z-API' : '360dialog'}:
                </p>
                <code className="block bg-blue-100 px-2 py-1 rounded text-xs mt-2 break-all">
                  {getWebhookUrl()}
                </code>
                {formData.whatsapp_provider === 'zapi' && (
                  <p className="text-xs text-blue-600 mt-2">
                    💡 No Z-API, configure também os webhooks de status, connect e disconnect.
                  </p>
                )}
              </div>
            )}

            {!isEditing && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
                <p className="text-sm text-gray-700">
                  <strong>Após criar:</strong> o cliente poderá acessar o sistema com o email e
                  senha definidos acima.
                </p>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={closeModal}
                className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleSubmit}
                disabled={saving}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
              >
                {saving ? 'Salvando...' : isEditing ? 'Salvar Alterações' : 'Criar Cliente'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}