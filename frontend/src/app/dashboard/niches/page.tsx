'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Layers, 
  Plus, 
  Check,
  X,
  ChevronDown,
  ChevronUp,
  Edit,
  Trash2
} from 'lucide-react';
import { getToken, getUser } from '@/lib/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Niche {
  id: number;
  slug: string;
  name: string;
  description: string;
  icon: string;
  active: boolean;
  is_default: boolean;
  required_fields: string[];
  optional_fields: string[];
  prompt_template: string;
  created_at: string;
}

export default function NichesPage() {
  const router = useRouter();
  const [niches, setNiches] = useState<Niche[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newNiche, setNewNiche] = useState({
    name: '',
    slug: '',
    description: '',
    icon: '🏢',
    prompt_template: '',
    required_fields: '',
    optional_fields: '',
  });

  useEffect(() => {
    const user = getUser();
    if (user?.role !== 'superadmin') {
      router.push('/dashboard');
      return;
    }
    fetchNiches();
  }, [router]);

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
    } finally {
        setLoading(false);  // ✅ ADICIONAR ISSO
    }
    }

  async function toggleNiche(niche: Niche) {
    if (niche.is_default && niche.active) {
      alert('Não é possível desativar o nicho padrão');
      return;
    }

    const action = niche.active ? 'desativar' : 'ativar';
    if (!confirm(`Tem certeza que deseja ${action} "${niche.name}"?`)) {
      return;
    }

    try {
      const token = getToken();
      await fetch(`${API_URL}/admin/niches/${niche.id}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ active: !niche.active }),
      });
      fetchNiches();
    } catch (err) {
      console.error('Erro ao atualizar nicho:', err);
    }
  }

  async function createNiche() {
    if (!newNiche.name || !newNiche.slug) {
      alert('Preencha nome e slug');
      return;
    }

    setCreating(true);
    try {
      const token = getToken();
      
      const payload = {
        ...newNiche,
        required_fields: newNiche.required_fields.split(',').map(s => s.trim()).filter(Boolean),
        optional_fields: newNiche.optional_fields.split(',').map(s => s.trim()).filter(Boolean),
        prompt_template: newNiche.prompt_template || `Você é um assistente virtual especializado em ${newNiche.name}. Seja cordial e colete as informações necessárias.`,
      };

      const response = await fetch(`${API_URL}/admin/niches`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        setShowModal(false);
        setNewNiche({
          name: '',
          slug: '',
          description: '',
          icon: '🏢',
          prompt_template: '',
          required_fields: '',
          optional_fields: '',
        });
        fetchNiches();
      } else {
        const error = await response.json();
        alert(error.detail || 'Erro ao criar nicho');
      }
    } catch (err) {
      console.error('Erro ao criar nicho:', err);
      alert('Erro ao criar nicho');
    } finally {
      setCreating(false);
    }
  }

  function generateSlug(name: string) {
    return name
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/(^_|_$)/g, '');
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Nichos</h1>
          <p className="text-gray-600">Configure os nichos de atendimento disponíveis</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5" />
          Novo Nicho
        </button>
      </div>

      {/* Niches Grid */}
      <div className="grid gap-4">
        {loading ? (
          <div className="text-center text-gray-500 py-8">Carregando...</div>
        ) : niches.length === 0 ? (
          <div className="text-center text-gray-500 py-8">Nenhum nicho cadastrado</div>
        ) : (
          niches.map((niche) => (
            <div
              key={niche.id}
              className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden"
            >
              {/* Header do Card */}
              <div 
                className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
                onClick={() => setExpandedId(expandedId === niche.id ? null : niche.id)}
              >
                <div className="flex items-center gap-4">
                  <span className="text-3xl">{niche.icon || '🏢'}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold text-gray-900">{niche.name}</h3>
                      {niche.is_default && (
                        <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full font-medium">
                          Padrão
                        </span>
                      )}
                    </div>
                    <p className="text-gray-500 text-sm">{niche.slug}</p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {niche.active ? (
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
                  {expandedId === niche.id ? (
                    <ChevronUp className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  )}
                </div>
              </div>

              {/* Conteúdo Expandido */}
              {expandedId === niche.id && (
                <div className="px-4 pb-4 border-t border-gray-100 pt-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-gray-500 text-sm mb-1">Descrição</p>
                      <p className="text-gray-900">{niche.description || 'Sem descrição'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-sm mb-1">Campos Obrigatórios</p>
                      <div className="flex flex-wrap gap-2">
                        {niche.required_fields?.length > 0 ? (
                          niche.required_fields.map((field) => (
                            <span key={field} className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-lg">
                              {field}
                            </span>
                          ))
                        ) : (
                          <span className="text-gray-400 text-sm">Nenhum</span>
                        )}
                      </div>
                    </div>
                    <div>
                      <p className="text-gray-500 text-sm mb-1">Campos Opcionais</p>
                      <div className="flex flex-wrap gap-2">
                        {niche.optional_fields?.length > 0 ? (
                          niche.optional_fields.map((field) => (
                            <span key={field} className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-lg">
                              {field}
                            </span>
                          ))
                        ) : (
                          <span className="text-gray-400 text-sm">Nenhum</span>
                        )}
                      </div>
                    </div>
                    <div>
                      <p className="text-gray-500 text-sm mb-1">Criado em</p>
                      <p className="text-gray-900">
                        {niche.created_at ? new Date(niche.created_at).toLocaleDateString('pt-BR') : '-'}
                      </p>
                    </div>
                  </div>

                  {/* Prompt Template */}
                  {niche.prompt_template && (
                    <div className="mt-4">
                      <p className="text-gray-500 text-sm mb-1">Prompt da IA</p>
                      <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 max-h-32 overflow-y-auto">
                        {niche.prompt_template}
                      </div>
                    </div>
                  )}

                  {/* Ações */}
                  <div className="flex gap-3 mt-4 pt-4 border-t border-gray-100">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleNiche(niche);
                      }}
                      disabled={niche.is_default && niche.active}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        niche.active
                          ? 'bg-red-50 text-red-600 hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed'
                          : 'bg-green-50 text-green-600 hover:bg-green-100'
                      }`}
                    >
                      {niche.active ? 'Desativar' : 'Ativar'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Modal Novo Nicho */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Novo Nicho</h2>

            <div className="space-y-4">
              <div className="grid grid-cols-4 gap-4">
                <div className="col-span-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Ícone</label>
                  <input
                    type="text"
                    value={newNiche.icon}
                    onChange={(e) => setNewNiche({ ...newNiche, icon: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-center text-2xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                    maxLength={2}
                  />
                </div>
                <div className="col-span-3">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
                  <input
                    type="text"
                    value={newNiche.name}
                    onChange={(e) => {
                      setNewNiche({
                        ...newNiche,
                        name: e.target.value,
                        slug: generateSlug(e.target.value),
                      });
                    }}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="Ex: Loja de Roupas"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Slug</label>
                <input
                  type="text"
                  value={newNiche.slug}
                  onChange={(e) => setNewNiche({ ...newNiche, slug: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="loja_roupas"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
                <input
                  type="text"
                  value={newNiche.description}
                  onChange={(e) => setNewNiche({ ...newNiche, description: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Breve descrição do nicho"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Campos Obrigatórios (separados por vírgula)
                </label>
                <input
                  type="text"
                  value={newNiche.required_fields}
                  onChange={(e) => setNewNiche({ ...newNiche, required_fields: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="name, phone, interest"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Campos Opcionais (separados por vírgula)
                </label>
                <input
                  type="text"
                  value={newNiche.optional_fields}
                  onChange={(e) => setNewNiche({ ...newNiche, optional_fields: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="budget, size, color"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Prompt Template (opcional)
                </label>
                <textarea
                  value={newNiche.prompt_template}
                  onChange={(e) => setNewNiche({ ...newNiche, prompt_template: e.target.value })}
                  rows={4}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Instruções para a IA..."
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={createNiche}
                disabled={creating}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
              >
                {creating ? 'Criando...' : 'Criar Nicho'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}