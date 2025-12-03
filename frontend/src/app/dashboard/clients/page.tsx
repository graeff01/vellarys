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
  User
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

export default function ClientsPage() {
  const router = useRouter();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [niches, setNiches] = useState<Niche[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  
  const [newTenant, setNewTenant] = useState({
    name: '',
    slug: '',
    plan: 'starter',
    niche: '',
    admin_name: '',
    admin_email: '',
    admin_password: '',
  });

  useEffect(() => {
    const user = getUser();
    if (user?.role !== 'superadmin') {
      router.push('/dashboard');
      return;
    }
    fetchTenants();
    fetchNiches();
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
    const response = await fetch(`${API_URL}/admin/niches?active_only=true`, {  // ✅ URL correta
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (response.ok) {
      const data = await response.json();
      setNiches(data.niches);  // ✅ Extrair o array
    }
  } catch (err) {
    console.error('Erro ao carregar nichos:', err);
  }
}

  async function createTenant() {
    // Validações
    if (!newTenant.name || !newTenant.slug) {
      alert('Preencha o nome e slug da empresa');
      return;
    }
    if (!newTenant.niche) {
      alert('Selecione um nicho');
      return;
    }
    if (!newTenant.admin_name || !newTenant.admin_email || !newTenant.admin_password) {
      alert('Preencha os dados do administrador do cliente');
      return;
    }
    if (newTenant.admin_password.length < 6) {
      alert('A senha deve ter pelo menos 6 caracteres');
      return;
    }

    setCreating(true);
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/admin/tenants`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newTenant),
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Cliente criado com sucesso!\n\nEmail de acesso: ${result.user.email}`);
        setShowModal(false);
        setNewTenant({
          name: '',
          slug: '',
          plan: 'starter',
          niche: '',
          admin_name: '',
          admin_email: '',
          admin_password: '',
        });
        fetchTenants();
      } else {
        const error = await response.json();
        alert(error.detail || 'Erro ao criar cliente');
      }
    } catch (err) {
      console.error('Erro ao criar cliente:', err);
      alert('Erro ao criar cliente');
    } finally {
      setCreating(false);
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
    setNewTenant({ ...newTenant, admin_password: password });
    setShowPassword(true);
  }

  const planColors: Record<string, string> = {
    starter: 'bg-gray-100 text-gray-700',
    professional: 'bg-blue-100 text-blue-700',
    enterprise: 'bg-purple-100 text-purple-700',
  };

  const planLabels: Record<string, string> = {
    starter: 'Starter',
    professional: 'Professional',
    enterprise: 'Enterprise',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
          <p className="text-gray-600">Gerencie os clientes da plataforma</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
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
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${planColors[tenant.plan] || 'bg-gray-100 text-gray-700'}`}>
                      {planLabels[tenant.plan] || tenant.plan}
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
                        onClick={() => router.push(`/dashboard/clients/${tenant.id}`)}
                        className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                        title="Ver detalhes"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => toggleTenant(tenant)}
                        className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                          tenant.active 
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

      {/* Modal Novo Cliente */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Novo Cliente</h2>
            
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
                    value={newTenant.name}
                    onChange={(e) => {
                      setNewTenant({
                        ...newTenant,
                        name: e.target.value,
                        slug: generateSlug(e.target.value),
                      });
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
                    value={newTenant.slug}
                    onChange={(e) => setNewTenant({ ...newTenant, slug: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="imobiliaria-silva"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Plano
                    </label>
                    <select
                      value={newTenant.plan}
                      onChange={(e) => setNewTenant({ ...newTenant, plan: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="starter">Starter</option>
                      <option value="professional">Professional</option>
                      <option value="enterprise">Enterprise</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Nicho *
                    </label>
                    <select
                      value={newTenant.niche}
                      onChange={(e) => setNewTenant({ ...newTenant, niche: e.target.value })}
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
                </div>
              </div>
            </div>

            {/* Dados do Administrador */}
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
                    value={newTenant.admin_name}
                    onChange={(e) => setNewTenant({ ...newTenant, admin_name: e.target.value })}
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
                      value={newTenant.admin_email}
                      onChange={(e) => setNewTenant({ ...newTenant, admin_email: e.target.value })}
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
                        value={newTenant.admin_password}
                        onChange={(e) => setNewTenant({ ...newTenant, admin_password: e.target.value })}
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
                      onClick={() => setShowPassword(!showPassword)}
                      className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
                    >
                      {showPassword ? 'Ocultar' : 'Ver'}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Info box */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <p className="text-sm text-blue-700">
                <strong>Após criar:</strong> O cliente poderá acessar o sistema usando o email e senha definidos acima.
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={createTenant}
                disabled={creating}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
              >
                {creating ? 'Criando...' : 'Criar Cliente'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}