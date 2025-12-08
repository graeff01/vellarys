'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader } from '@/components/ui/card';
import {
  getEmpreendimentos,
  getEmpreendimento,
  createEmpreendimento,
  updateEmpreendimento,
  deleteEmpreendimento,
  toggleEmpreendimentoStatus,
  Empreendimento,
  EmpreendimentoCreate,
} from '@/lib/api';
import { 
  Plus, X, Info, Home, Edit2, Trash2, Eye, EyeOff, 
  MapPin, DollarSign, Building, Save, ArrowLeft
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
          <span key={i} className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm">
            {tag}
            <button type="button" onClick={() => removeTag(i)} className="hover:bg-blue-200 rounded-full p-0.5">
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
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      />
    </div>
  );
}

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================

interface EmpreendimentosTabProps {
  sellers: Array<{ id: number; name: string }>;
}

export default function EmpreendimentosTab({ sellers }: EmpreendimentosTabProps) {
  const [empreendimentos, setEmpreendimentos] = useState<Empreendimento[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);

  // Form state
  const [formData, setFormData] = useState<EmpreendimentoCreate>({
    nome: '',
    status: 'lancamento',
    gatilhos: [],
    prioridade: 0,
    tipologias: [],
    itens_lazer: [],
    diferenciais: [],
    perguntas_qualificacao: [],
    aceita_financiamento: true,
    aceita_fgts: true,
    aceita_permuta: false,
    aceita_consorcio: false,
    notificar_gestor: false,
  });

  useEffect(() => {
    loadEmpreendimentos();
  }, []);

  const loadEmpreendimentos = async () => {
    try {
      setLoading(true);
      const response = await getEmpreendimentos();
      setEmpreendimentos(response.empreendimentos || []);
    } catch (error) {
      console.error('Erro ao carregar empreendimentos:', error);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      nome: '',
      status: 'lancamento',
      gatilhos: [],
      prioridade: 0,
      tipologias: [],
      itens_lazer: [],
      diferenciais: [],
      perguntas_qualificacao: [],
      aceita_financiamento: true,
      aceita_fgts: true,
      aceita_permuta: false,
      aceita_consorcio: false,
      notificar_gestor: false,
    });
    setEditingId(null);
    setShowForm(false);
  };

  const handleEdit = async (id: number) => {
    try {
      const emp = await getEmpreendimento(id);
      setFormData({
        nome: emp.nome || '',
        status: emp.status || 'lancamento',
        url_landing_page: emp.url_landing_page,
        gatilhos: emp.gatilhos || [],
        prioridade: emp.prioridade || 0,
        endereco: emp.endereco,
        bairro: emp.bairro,
        cidade: emp.cidade,
        estado: emp.estado,
        cep: emp.cep,
        descricao_localizacao: emp.descricao_localizacao,
        descricao: emp.descricao,
        tipologias: emp.tipologias || [],
        metragem_minima: emp.metragem_minima,
        metragem_maxima: emp.metragem_maxima,
        torres: emp.torres,
        andares: emp.andares,
        total_unidades: emp.total_unidades,
        vagas_minima: emp.vagas_minima,
        vagas_maxima: emp.vagas_maxima,
        previsao_entrega: emp.previsao_entrega,
        preco_minimo: emp.preco_minimo,
        preco_maximo: emp.preco_maximo,
        aceita_financiamento: emp.aceita_financiamento ?? true,
        aceita_fgts: emp.aceita_fgts ?? true,
        aceita_permuta: emp.aceita_permuta ?? false,
        aceita_consorcio: emp.aceita_consorcio ?? false,
        condicoes_especiais: emp.condicoes_especiais,
        itens_lazer: emp.itens_lazer || [],
        diferenciais: emp.diferenciais || [],
        perguntas_qualificacao: emp.perguntas_qualificacao || [],
        instrucoes_ia: emp.instrucoes_ia,
        vendedor_id: emp.vendedor_id,
        metodo_distribuicao: emp.metodo_distribuicao,
        notificar_gestor: emp.notificar_gestor ?? false,
        whatsapp_notificacao: emp.whatsapp_notificacao,
      });
      setEditingId(id);
      setShowForm(true);
    } catch (error) {
      console.error('Erro ao carregar empreendimento:', error);
      alert('Erro ao carregar empreendimento');
    }
  };

  const handleSave = async () => {
    if (!formData.nome?.trim()) {
      alert('Nome é obrigatório');
      return;
    }
    if (!formData.gatilhos || formData.gatilhos.length === 0) {
      alert('Adicione pelo menos um gatilho de detecção');
      return;
    }

    setSaving(true);
    try {
      if (editingId) {
        await updateEmpreendimento(editingId, formData);
      } else {
        await createEmpreendimento(formData);
      }
      await loadEmpreendimentos();
      resetForm();
    } catch (error) {
      console.error('Erro ao salvar:', error);
      alert('Erro ao salvar empreendimento');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Tem certeza que deseja excluir este empreendimento? Esta ação não pode ser desfeita.')) {
      return;
    }

    setDeleting(id);
    try {
      await deleteEmpreendimento(id);
      await loadEmpreendimentos();
    } catch (error) {
      console.error('Erro ao excluir:', error);
      alert('Erro ao excluir empreendimento');
    } finally {
      setDeleting(null);
    }
  };

  const handleToggleStatus = async (id: number) => {
    try {
      await toggleEmpreendimentoStatus(id);
      await loadEmpreendimentos();
    } catch (error) {
      console.error('Erro ao alterar status:', error);
    }
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      lancamento: '🚀 Lançamento',
      em_obras: '🏗️ Em Obras',
      pronto_para_morar: '🏠 Pronto',
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

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Form view
  if (showForm) {
    return (
      <div className="space-y-6">
        {/* Header do formulário */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={resetForm}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                {editingId ? 'Editar Empreendimento' : 'Novo Empreendimento'}
              </h2>
              <p className="text-sm text-gray-500">
                Preencha as informações do empreendimento
              </p>
            </div>
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saving ? 'Salvando...' : 'Salvar'}
          </button>
        </div>

        {/* Seção 1: Informações Básicas */}
        <Card>
          <CardHeader title="Informações Básicas" subtitle="Dados principais do empreendimento" />
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nome do Empreendimento *
                </label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Ex: Essence Residence"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Status
                </label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="lancamento">🚀 Lançamento</option>
                  <option value="em_obras">🏗️ Em Obras</option>
                  <option value="pronto_para_morar">🏠 Pronto para Morar</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                URL da Landing Page
              </label>
              <input
                type="url"
                value={formData.url_landing_page || ''}
                onChange={(e) => setFormData({ ...formData, url_landing_page: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="https://..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Descrição
              </label>
              <textarea
                value={formData.descricao || ''}
                onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="Descrição do empreendimento para a IA usar nas conversas..."
              />
            </div>
          </div>
        </Card>

        {/* Seção 2: Gatilhos */}
        <Card>
          <CardHeader 
            title="Gatilhos de Detecção *" 
            subtitle="Palavras-chave que ativam este empreendimento automaticamente" 
          />
          <div className="space-y-4">
            <TagInput
              tags={formData.gatilhos || []}
              onChange={(tags) => setFormData({ ...formData, gatilhos: tags })}
              placeholder="Ex: essence, portal de investimento, essence residence..."
            />
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <div className="flex gap-3">
                <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-amber-800">
                  <p className="font-medium mb-1">Como funciona:</p>
                  <p>Quando um lead mencionar qualquer um desses termos, a IA automaticamente:</p>
                  <ul className="list-disc list-inside mt-1 text-amber-700">
                    <li>Carrega as informações deste empreendimento</li>
                    <li>Faz as perguntas de qualificação específicas</li>
                    <li>Direciona para o vendedor configurado (se houver)</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* Seção 3: Localização */}
        <Card>
          <CardHeader title="Localização" subtitle="Endereço e região do empreendimento" />
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Endereço</label>
                <input
                  type="text"
                  value={formData.endereco || ''}
                  onChange={(e) => setFormData({ ...formData, endereco: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Av. Principal, 1000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Bairro</label>
                <input
                  type="text"
                  value={formData.bairro || ''}
                  onChange={(e) => setFormData({ ...formData, bairro: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Centro"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Cidade</label>
                <input
                  type="text"
                  value={formData.cidade || ''}
                  onChange={(e) => setFormData({ ...formData, cidade: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Porto Alegre"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Estado</label>
                <input
                  type="text"
                  value={formData.estado || ''}
                  onChange={(e) => setFormData({ ...formData, estado: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="RS"
                  maxLength={2}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">CEP</label>
                <input
                  type="text"
                  value={formData.cep || ''}
                  onChange={(e) => setFormData({ ...formData, cep: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="00000-000"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Descrição da Localização
              </label>
              <textarea
                value={formData.descricao_localizacao || ''}
                onChange={(e) => setFormData({ ...formData, descricao_localizacao: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                rows={2}
                placeholder="Ex: Localizado próximo ao Shopping Iguatemi, com fácil acesso à BR-116..."
              />
            </div>
          </div>
        </Card>

        {/* Seção 4: Características */}
        <Card>
          <CardHeader title="Características" subtitle="Tipologias e estrutura do empreendimento" />
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tipologias Disponíveis
              </label>
              <TagInput
                tags={formData.tipologias || []}
                onChange={(tags) => setFormData({ ...formData, tipologias: tags })}
                placeholder="Ex: 2 dormitórios, 3 dormitórios, Cobertura..."
              />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Metragem Mín. (m²)</label>
                <input
                  type="number"
                  value={formData.metragem_minima || ''}
                  onChange={(e) => setFormData({ ...formData, metragem_minima: parseInt(e.target.value) || undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="45"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Metragem Máx. (m²)</label>
                <input
                  type="number"
                  value={formData.metragem_maxima || ''}
                  onChange={(e) => setFormData({ ...formData, metragem_maxima: parseInt(e.target.value) || undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="120"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Vagas Mín.</label>
                <input
                  type="number"
                  value={formData.vagas_minima || ''}
                  onChange={(e) => setFormData({ ...formData, vagas_minima: parseInt(e.target.value) || undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Vagas Máx.</label>
                <input
                  type="number"
                  value={formData.vagas_maxima || ''}
                  onChange={(e) => setFormData({ ...formData, vagas_maxima: parseInt(e.target.value) || undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="3"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Torres</label>
                <input
                  type="number"
                  value={formData.torres || ''}
                  onChange={(e) => setFormData({ ...formData, torres: parseInt(e.target.value) || undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Andares</label>
                <input
                  type="number"
                  value={formData.andares || ''}
                  onChange={(e) => setFormData({ ...formData, andares: parseInt(e.target.value) || undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Total Unidades</label>
                <input
                  type="number"
                  value={formData.total_unidades || ''}
                  onChange={(e) => setFormData({ ...formData, total_unidades: parseInt(e.target.value) || undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Previsão Entrega</label>
                <input
                  type="text"
                  value={formData.previsao_entrega || ''}
                  onChange={(e) => setFormData({ ...formData, previsao_entrega: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Dez/2026"
                />
              </div>
            </div>
          </div>
        </Card>

        {/* Seção 5: Valores */}
        <Card>
          <CardHeader title="Valores e Condições" subtitle="Preços e formas de pagamento aceitas" />
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Preço Mínimo (R$)</label>
                <input
                  type="number"
                  value={formData.preco_minimo || ''}
                  onChange={(e) => setFormData({ ...formData, preco_minimo: parseFloat(e.target.value) || undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="350000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Preço Máximo (R$)</label>
                <input
                  type="number"
                  value={formData.preco_maximo || ''}
                  onChange={(e) => setFormData({ ...formData, preco_maximo: parseFloat(e.target.value) || undefined })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="850000"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <label className="flex items-center gap-2 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={formData.aceita_financiamento}
                  onChange={(e) => setFormData({ ...formData, aceita_financiamento: e.target.checked })}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <span className="text-sm">Financiamento</span>
              </label>
              <label className="flex items-center gap-2 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={formData.aceita_fgts}
                  onChange={(e) => setFormData({ ...formData, aceita_fgts: e.target.checked })}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <span className="text-sm">FGTS</span>
              </label>
              <label className="flex items-center gap-2 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={formData.aceita_permuta}
                  onChange={(e) => setFormData({ ...formData, aceita_permuta: e.target.checked })}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <span className="text-sm">Permuta</span>
              </label>
              <label className="flex items-center gap-2 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={formData.aceita_consorcio}
                  onChange={(e) => setFormData({ ...formData, aceita_consorcio: e.target.checked })}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <span className="text-sm">Consórcio</span>
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Condições Especiais</label>
              <textarea
                value={formData.condicoes_especiais || ''}
                onChange={(e) => setFormData({ ...formData, condicoes_especiais: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                rows={2}
                placeholder="Ex: Entrada em 60x, desconto para pagamento à vista..."
              />
            </div>
          </div>
        </Card>

        {/* Seção 6: Lazer e Diferenciais */}
        <Card>
          <CardHeader title="Lazer e Diferenciais" subtitle="Áreas de lazer e características especiais" />
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Itens de Lazer</label>
              <TagInput
                tags={formData.itens_lazer || []}
                onChange={(tags) => setFormData({ ...formData, itens_lazer: tags })}
                placeholder="Ex: Piscina, Academia, Salão de festas, Playground..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Diferenciais</label>
              <TagInput
                tags={formData.diferenciais || []}
                onChange={(tags) => setFormData({ ...formData, diferenciais: tags })}
                placeholder="Ex: Vista para o Guaíba, Infraestrutura para ar-condicionado..."
              />
            </div>
          </div>
        </Card>

        {/* Seção 7: Qualificação */}
        <Card>
          <CardHeader 
            title="Qualificação Específica" 
            subtitle="Perguntas e instruções especiais para este empreendimento" 
          />
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Perguntas de Qualificação
              </label>
              <TagInput
                tags={formData.perguntas_qualificacao || []}
                onChange={(tags) => setFormData({ ...formData, perguntas_qualificacao: tags })}
                placeholder="Ex: Você busca para morar ou investir?, Qual sua faixa de investimento?..."
              />
              <p className="text-xs text-gray-500 mt-1">
                A IA vai fazer essas perguntas quando detectar interesse neste empreendimento
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Instruções Especiais para IA
              </label>
              <textarea
                value={formData.instrucoes_ia || ''}
                onChange={(e) => setFormData({ ...formData, instrucoes_ia: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="Ex: Destacar a vista para o Guaíba como principal diferencial. Mencionar que é o último lançamento na região..."
              />
            </div>
          </div>
        </Card>

        {/* Seção 8: Destino dos Leads */}
        <Card>
          <CardHeader 
            title="Destino dos Leads" 
            subtitle="Para quem enviar os leads deste empreendimento" 
          />
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Vendedor Responsável
              </label>
              <select
                value={formData.vendedor_id || ''}
                onChange={(e) => setFormData({ ...formData, vendedor_id: e.target.value ? parseInt(e.target.value) : undefined })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Usar distribuição padrão (rodízio)</option>
                {sellers.map((seller) => (
                  <option key={seller.id} value={seller.id}>
                    {seller.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Se não selecionar, o lead seguirá a distribuição configurada nas configurações gerais
              </p>
            </div>
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <p className="font-medium text-gray-900">Notificar Gestor Imediatamente</p>
                <p className="text-sm text-gray-500">Enviar alerta quando detectar interesse neste empreendimento</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.notificar_gestor}
                  onChange={(e) => setFormData({ ...formData, notificar_gestor: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
            {formData.notificar_gestor && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  WhatsApp para Notificação
                </label>
                <input
                  type="text"
                  value={formData.whatsapp_notificacao || ''}
                  onChange={(e) => setFormData({ ...formData, whatsapp_notificacao: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="5551999999999"
                />
              </div>
            )}
          </div>
        </Card>

        {/* Botões de ação */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <button
            onClick={resetForm}
            className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saving ? 'Salvando...' : (editingId ? 'Atualizar' : 'Criar Empreendimento')}
          </button>
        </div>
      </div>
    );
  }

  // Lista view
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Empreendimentos</h2>
          <p className="text-sm text-gray-500">
            Cadastre empreendimentos para a IA identificar automaticamente
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          Novo Empreendimento
        </button>
      </div>

      {/* Info box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex gap-3">
          <Home className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">Como funciona:</p>
            <p>
              Cadastre seus empreendimentos com gatilhos (palavras-chave). Quando um lead mencionar 
              esses termos, a IA automaticamente carrega as informações específicas e faz as 
              perguntas de qualificação configuradas.
            </p>
          </div>
        </div>
      </div>

      {/* Lista */}
      {empreendimentos.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <Building className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Nenhum empreendimento cadastrado
          </h3>
          <p className="text-gray-500 mb-4">
            Cadastre seu primeiro empreendimento para a IA começar a identificar automaticamente.
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            Cadastrar Empreendimento
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {empreendimentos.map((emp) => (
            <div
              key={emp.id}
              className={`bg-white border rounded-lg p-4 ${!emp.ativo ? 'opacity-60' : ''}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">{emp.nome}</h3>
                    <span className="text-sm px-2 py-0.5 bg-gray-100 rounded">
                      {getStatusLabel(emp.status)}
                    </span>
                    {!emp.ativo && (
                      <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded">
                        Inativo
                      </span>
                    )}
                  </div>

                  {/* Localização */}
                  {(emp.bairro || emp.cidade) && (
                    <div className="flex items-center gap-1 text-sm text-gray-500 mb-2">
                      <MapPin className="w-4 h-4" />
                      {[emp.bairro, emp.cidade, emp.estado].filter(Boolean).join(', ')}
                    </div>
                  )}

                  {/* Preço */}
                  {(emp.preco_minimo || emp.preco_maximo) && (
                    <div className="flex items-center gap-1 text-sm text-gray-500 mb-2">
                      <DollarSign className="w-4 h-4" />
                      {emp.preco_minimo && emp.preco_maximo
                        ? `${formatPrice(emp.preco_minimo)} a ${formatPrice(emp.preco_maximo)}`
                        : formatPrice(emp.preco_minimo || emp.preco_maximo)}
                    </div>
                  )}

                  {/* Gatilhos */}
                  <div className="flex flex-wrap gap-1 mt-3">
                    {emp.gatilhos?.slice(0, 5).map((g, i) => (
                      <span key={i} className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded">
                        {g}
                      </span>
                    ))}
                    {emp.gatilhos?.length > 5 && (
                      <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                        +{emp.gatilhos.length - 5}
                      </span>
                    )}
                  </div>

                  {/* Métricas */}
                  <div className="flex gap-4 mt-3 text-sm text-gray-500">
                    <span>{emp.total_leads || 0} leads</span>
                    <span>{emp.leads_qualificados || 0} qualificados</span>
                    {emp.vendedor_nome && (
                      <span className="text-blue-600">→ {emp.vendedor_nome}</span>
                    )}
                  </div>
                </div>

                {/* Ações */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleToggleStatus(emp.id)}
                    className="p-2 hover:bg-gray-100 rounded-lg"
                    title={emp.ativo ? 'Desativar' : 'Ativar'}
                  >
                    {emp.ativo ? (
                      <Eye className="w-4 h-4 text-green-600" />
                    ) : (
                      <EyeOff className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                  <button
                    onClick={() => handleEdit(emp.id)}
                    className="p-2 hover:bg-gray-100 rounded-lg"
                    title="Editar"
                  >
                    <Edit2 className="w-4 h-4 text-gray-600" />
                  </button>
                  <button
                    onClick={() => handleDelete(emp.id)}
                    disabled={deleting === emp.id}
                    className="p-2 hover:bg-red-50 rounded-lg"
                    title="Excluir"
                  >
                    {deleting === emp.id ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600"></div>
                    ) : (
                      <Trash2 className="w-4 h-4 text-red-600" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}