'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader } from '@/components/ui/card';
import {
  getProducts,
  getProduct,
  createProduct,
  updateProduct,
  deleteProduct,
  toggleProductStatus,
  Product,
  ProductCreate,
} from '@/lib/api';
import {
  Plus, X, Info, Home, Edit2, Trash2, Eye, EyeOff,
  MapPin, DollarSign, Building, Save, ArrowLeft, Package,
  Layers, MessageSquare, Zap
} from 'lucide-react';

// =============================================================================
// COMPONENTES AUXILIARES
// =============================================================================

interface TagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  maxTags?: number;
}

function TagInput({ tags, onChange, placeholder = "Digite e pressione Enter", maxTags = 20 }: TagInputProps) {
  const [inputValue, setInputValue] = useState('');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      e.preventDefault();
      if (tags.length < maxTags && !tags.includes(inputValue.trim())) {
        onChange([...tags, inputValue.trim()]);
        setInputValue('');
      }
    }
  };

  const removeTag = (index: number) => {
    onChange(tags.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {tags.map((tag, i) => (
          <span key={i} className="inline-flex items-center gap-1 bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full text-sm">
            {tag}
            <button type="button" onClick={() => removeTag(i)} className="hover:bg-indigo-200 rounded-full p-0.5">
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
      </div>
      <input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all font-outfit"
      />
    </div>
  );
}

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================

interface ProductsTabProps {
  sellers: Array<{ id: number; name: string }>;
}

export default function ProductsTab({ sellers }: ProductsTabProps) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);

  // Form state
  const [formData, setFormData] = useState<ProductCreate>({
    name: '',
    status: 'active',
    triggers: [],
    priority: 0,
    qualification_questions: [],
    notify_manager: false,
    attributes: {},
  });

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const response = await getProducts();
      setProducts(response.products || []);
    } catch (error) {
      console.error('Erro ao carregar produtos:', error);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      status: 'active',
      triggers: [],
      priority: 0,
      qualification_questions: [],
      notify_manager: false,
      attributes: {},
    });
    setEditingId(null);
    setShowForm(false);
  };

  const handleEdit = async (id: number) => {
    try {
      const prod = await getProduct(id);
      setFormData({
        name: prod.name || '',
        status: prod.status || 'active',
        url_landing_page: prod.url_landing_page,
        triggers: prod.triggers || [],
        priority: prod.priority || 0,
        description: prod.description || '',
        ai_instructions: prod.ai_instructions || '',
        qualification_questions: prod.qualification_questions || [],
        seller_id: prod.seller_id,
        distribution_method: prod.distribution_method,
        notify_manager: prod.notify_manager ?? false,
        attributes: prod.attributes || {},
      });
      setEditingId(id);
      setShowForm(true);
    } catch (error) {
      console.error('Erro ao carregar produto:', error);
      alert('Erro ao carregar produto');
    }
  };

  const handleSave = async () => {
    if (!formData.name?.trim()) {
      alert('Nome é obrigatório');
      return;
    }
    if (!formData.triggers || formData.triggers.length === 0) {
      alert('Adicione pelo menos um gatilho de detecção');
      return;
    }

    setSaving(true);
    try {
      if (editingId) {
        await updateProduct(editingId, formData);
      } else {
        await createProduct(formData);
      }
      await loadProducts();
      resetForm();
    } catch (error) {
      console.error('Erro ao salvar:', error);
      alert('Erro ao salvar produto');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Tem certeza que deseja excluir este produto? Esta ação não pode ser desfeita.')) {
      return;
    }

    setDeleting(id);
    try {
      await deleteProduct(id);
      await loadProducts();
    } catch (error) {
      console.error('Erro ao excluir:', error);
      alert('Erro ao excluir produto');
    } finally {
      setDeleting(null);
    }
  };

  const handleToggleStatus = async (id: number) => {
    try {
      await toggleProductStatus(id);
      await loadProducts();
    } catch (error) {
      console.error('Erro ao alterar status:', error);
    }
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      active: '✅ Ativo',
      inactive: '❌ Inativo',
      archived: '📦 Arquivado',
      launch: '🚀 Lançamento',
    };
    return labels[status] || status;
  };

  const formatPrice = (value?: number) => {
    if (!value) return '-';
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Helper para atributos dinâmicos
  const setAttribute = (key: string, value: any) => {
    setFormData({
      ...formData,
      attributes: {
        ...formData.attributes,
        [key]: value
      }
    });
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  // Form view
  if (showForm) {
    return (
      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
        {/* Header do formulário */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={resetForm}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h2 className="text-2xl font-outfit font-bold text-gray-900">
                {editingId ? 'Editar Produto' : 'Novo Produto'}
              </h2>
              <p className="text-sm text-gray-500">
                Configure os detalhes e gatilhos de detecção da IA
              </p>
            </div>
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 bg-indigo-600 text-white px-6 py-2.5 rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-sm hover:shadow-md"
          >
            {saving ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saving ? 'Salvando...' : 'Salvar Alterações'}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Seção 1: Informações Básicas */}
            <Card className="overflow-hidden border-none shadow-sm ring-1 ring-gray-200">
              <div className="bg-gradient-to-r from-indigo-500 to-purple-600 h-1" />
              <CardHeader title="Informações Básicas" subtitle="Dados principais do produto ou serviço" />
              <div className="p-6 pt-0 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-gray-700">
                      Nome do Produto *
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all outline-none"
                      placeholder="Ex: Consultoria Premium"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-gray-700">
                      Status
                    </label>
                    <select
                      value={formData.status}
                      onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                      className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all outline-none appearance-none"
                    >
                      <option value="active">✅ Ativo</option>
                      <option value="launch">🚀 Lançamento</option>
                      <option value="inactive">❌ Inativo</option>
                    </select>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-700">
                    Descrição para a IA
                  </label>
                  <textarea
                    value={formData.description || ''}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all outline-none"
                    rows={4}
                    placeholder="Descreva seu produto para que a IA possa explicá-lo aos leads..."
                  />
                </div>
              </div>
            </Card>

            {/* Seção 2: Gatilhos e AI */}
            <Card className="border-none shadow-sm ring-1 ring-gray-200">
              <CardHeader
                title="Inteligência de Detecção"
                subtitle="Configure como a IA deve identificar e agir"
              />
              <div className="p-6 pt-0 space-y-6">
                <div className="space-y-3">
                  <label className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                    <Zap className="w-4 h-4 text-amber-500" />
                    Gatilhos de Detecção *
                  </label>
                  <TagInput
                    tags={formData.triggers || []}
                    onChange={(tags) => setFormData({ ...formData, triggers: tags })}
                    placeholder="Termos que ativam este produto (ex: premium, vip, consultoria)..."
                  />
                </div>

                <div className="space-y-3">
                  <label className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                    <MessageSquare className="w-4 h-4 text-indigo-500" />
                    Perguntas de Qualificação
                  </label>
                  <TagInput
                    tags={formData.qualification_questions || []}
                    onChange={(tags) => setFormData({ ...formData, qualification_questions: tags })}
                    placeholder="Perguntas que a IA deve fazer (ex: Qual seu orçamento?, Qual seu prazo?)..."
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-700">
                    Instruções Diretas à IA
                  </label>
                  <textarea
                    value={formData.ai_instructions || ''}
                    onChange={(e) => setFormData({ ...formData, ai_instructions: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all outline-none"
                    rows={3}
                    placeholder="Ex: Sempre oferecer um desconto adicional se o lead parecer indeciso..."
                  />
                </div>
              </div>
            </Card>

            {/* Seção 3: Atributos Dinâmicos - DEMONSTRAÇÃO DE FLEXIBILIDADE */}
            <Card className="border-none shadow-sm ring-1 ring-gray-200">
              <CardHeader
                title="Atributos Específicos"
                subtitle="Campos customizados que a IA usará no contexto"
              />
              <div className="p-6 pt-0">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-gray-700">Localização/Região</label>
                    <input
                      type="text"
                      value={formData.attributes?.location || ''}
                      onChange={(e) => setAttribute('location', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg"
                      placeholder="Ex: São Paulo, SP"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-gray-700">Preço Estimativo</label>
                    <input
                      type="text"
                      value={formData.attributes?.price_display || ''}
                      onChange={(e) => setAttribute('price_display', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg"
                      placeholder="Ex: A partir de R$ 5.000,00"
                    />
                  </div>
                </div>
                <div className="mt-4 p-4 bg-indigo-50 rounded-xl border border-indigo-100">
                  <p className="text-xs text-indigo-700 leading-relaxed font-outfit">
                    🚀 <strong>Velaris Multi-Niche:</strong> Estes atributos são armazenados em um campo flexível (JSONB).
                    A IA os detecta automaticamente e os usa para responder aos leads, não importa qual seja o seu negócio.
                  </p>
                </div>
              </div>
            </Card>
          </div>

          <div className="space-y-6">
            {/* Destino dos Leads */}
            <Card className="border-none shadow-sm ring-1 ring-gray-200">
              <CardHeader title="Atribuição" subtitle="Fluxo de encaminhamento" />
              <div className="p-6 pt-0 space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-700">Vendedor Responsável</label>
                  <select
                    value={formData.seller_id || ''}
                    onChange={(e) => setFormData({ ...formData, seller_id: e.target.value ? parseInt(e.target.value) : undefined })}
                    className="w-full px-4 py-2 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Distribuição Padrão</option>
                    {sellers.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-100">
                  <div className="space-y-0.5">
                    <p className="text-sm font-bold text-gray-900">Notificar Gestor</p>
                    <p className="text-xs text-gray-500">Alerta imedidato no WhatsApp</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.notify_manager}
                      onChange={(e) => setFormData({ ...formData, notify_manager: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>
              </div>
            </Card>

            {/* Landing Page */}
            <Card className="border-none shadow-sm ring-1 ring-gray-200">
              <CardHeader title="Link Direto" subtitle="Página de vendas" />
              <div className="p-6 pt-0">
                <input
                  type="url"
                  value={formData.url_landing_page || ''}
                  onChange={(e) => setFormData({ ...formData, url_landing_page: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg text-sm"
                  placeholder="https://suapagina.com.br"
                />
              </div>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  // Lista view
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-3xl font-outfit font-bold text-gray-900">Produtos & Serviços</h2>
          <p className="text-sm text-gray-500 flex items-center gap-2">
            <Package className="w-4 h-4" />
            Gerencie o que a sua IA deve oferecer aos leads
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-indigo-700 transition-all shadow-indigo-200 shadow-lg hover:shadow-indigo-300 hover:-translate-y-0.5"
        >
          <Plus className="w-5 h-5" />
          Novo Produto
        </button>
      </div>

      {/* Lista */}
      {products.length === 0 ? (
        <div className="text-center py-20 bg-white border border-dashed border-gray-300 rounded-3xl">
          <Package className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 font-outfit">Sua vitrine está vazia</h3>
          <p className="text-gray-500 max-w-xs mx-auto mt-2">
            Adicione seu primeiro produto para que o Velaris comece a trabalhar por você.
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="mt-6 inline-flex items-center gap-2 text-indigo-600 font-bold hover:text-indigo-700"
          >
            Começar agora <Zap className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {products.map((prod) => (
            <div
              key={prod.id}
              className={`group bg-white border border-gray-200 rounded-3xl p-6 transition-all hover:shadow-xl hover:ring-1 hover:ring-indigo-100 ${!prod.active ? 'opacity-60 grayscale' : ''}`}
            >
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-indigo-50 text-indigo-600 rounded-2xl group-hover:bg-indigo-600 group-hover:text-white transition-all">
                  <Package className="w-6 h-6" />
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleEdit(prod.id)}
                    className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                  >
                    <Edit2 className="w-4 h-4 text-gray-500" />
                  </button>
                  <button
                    onClick={() => handleToggleStatus(prod.id)}
                    className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                  >
                    {prod.active ? (
                      <Eye className="w-4 h-4 text-green-500" />
                    ) : (
                      <EyeOff className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                  <button
                    onClick={() => handleDelete(prod.id)}
                    disabled={deleting === prod.id}
                    className="p-2 hover:bg-red-50 rounded-full transition-colors"
                  >
                    {deleting === prod.id ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600"></div>
                    ) : (
                      <Trash2 className="w-4 h-4 text-red-400" />
                    )}
                  </button>
                </div>
              </div>

              <div className="space-y-1 mb-4">
                <h3 className="text-lg font-bold text-gray-900 group-hover:text-indigo-600 transition-colors">
                  {prod.name}
                </h3>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full uppercase tracking-wider">
                    {prod.status}
                  </span>
                  {prod.attributes?.location && (
                    <span className="text-xs text-gray-500 flex items-center gap-1">
                      <MapPin className="w-3 h-3" /> {prod.attributes.location}
                    </span>
                  )}
                </div>
              </div>

              <p className="text-sm text-gray-500 line-clamp-2 mb-6 h-10">
                {prod.description || 'Sem descrição definida.'}
              </p>

              <div className="flex flex-wrap gap-1.5 mb-6">
                {prod.triggers?.slice(0, 3).map((g, i) => (
                  <span key={i} className="text-[10px] font-bold px-2 py-1 bg-indigo-50 text-indigo-600 rounded-lg uppercase">
                    {g}
                  </span>
                ))}
                {prod.triggers?.length > 3 && (
                  <span className="text-[10px] font-bold px-2 py-1 bg-gray-50 text-gray-400 rounded-lg">
                    +{prod.triggers.length - 3}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-50">
                <div className="flex flex-col">
                  <span className="text-[10px] text-gray-400 font-bold uppercase tracking-tighter">Leads</span>
                  <span className="text-sm font-bold text-gray-900">{prod.total_leads || 0}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] text-gray-400 font-bold uppercase tracking-tighter">Qualificados</span>
                  <span className="text-sm font-bold text-indigo-600">
                    {Math.round(((prod.qualified_leads || 0) / (prod.total_leads || 1)) * 100)}%
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}