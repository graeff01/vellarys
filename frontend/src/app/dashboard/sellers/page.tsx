'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Users, Plus, Phone, Mail, MapPin, Target, 
  TrendingUp, ToggleLeft, ToggleRight, Pencil, 
  Trash2, X, Star
} from 'lucide-react';
import { 
  getSellers, createSeller, updateSeller, deleteSeller,
  toggleSellerAvailability, getSellerStats, getSpecialtiesConfig,
  Seller, SellerStats
} from '@/lib/sellers';

export default function SellersPage() {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [stats, setStats] = useState<SellerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingSeller, setEditingSeller] = useState<Seller | null>(null);
  const [saving, setSaving] = useState(false);

  // Especialidades dinâmicas do nicho
  const [specialtyOptions, setSpecialtyOptions] = useState<Array<{value: string, label: string}>>([]);
  const [allowCustomSpecialty, setAllowCustomSpecialty] = useState(true);

  // Form state
  const [formName, setFormName] = useState('');
  const [formWhatsapp, setFormWhatsapp] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formCities, setFormCities] = useState<string[]>([]);
  const [formSpecialties, setFormSpecialties] = useState<string[]>([]);
  const [formMaxLeads, setFormMaxLeads] = useState(0);
  const [formPriority, setFormPriority] = useState(5);
  const [newCity, setNewCity] = useState('');
  const [newSpecialty, setNewSpecialty] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [sellersRes, statsRes, specialtiesRes] = await Promise.all([
        getSellers(),
        getSellerStats(),
        getSpecialtiesConfig(),
      ]);
      setSellers(sellersRes.sellers);
      setStats(statsRes);
      setSpecialtyOptions(specialtiesRes.specialties);
      setAllowCustomSpecialty(specialtiesRes.allow_custom);
    } catch (error) {
      console.error('Erro ao carregar vendedores:', error);
    } finally {
      setLoading(false);
    }
  }

  function openNewModal() {
    setEditingSeller(null);
    setFormName('');
    setFormWhatsapp('');
    setFormEmail('');
    setFormCities([]);
    setFormSpecialties([]);
    setFormMaxLeads(0);
    setFormPriority(5);
    setShowModal(true);
  }

  function openEditModal(seller: Seller) {
    setEditingSeller(seller);
    setFormName(seller.name);
    setFormWhatsapp(seller.whatsapp);
    setFormEmail(seller.email || '');
    setFormCities(seller.cities || []);
    setFormSpecialties(seller.specialties || []);
    setFormMaxLeads(seller.max_leads_per_day);
    setFormPriority(seller.priority);
    setShowModal(true);
  }

  async function handleSave() {
    if (!formName || !formWhatsapp) {
      alert('Nome e WhatsApp são obrigatórios');
      return;
    }

    setSaving(true);
    try {
      if (editingSeller) {
        await updateSeller(editingSeller.id, {
          name: formName,
          whatsapp: formWhatsapp,
          email: formEmail || undefined,
          cities: formCities,
          specialties: formSpecialties,
          max_leads_per_day: formMaxLeads,
          priority: formPriority,
        });
      } else {
        await createSeller({
          name: formName,
          whatsapp: formWhatsapp,
          email: formEmail || undefined,
          cities: formCities,
          specialties: formSpecialties,
          max_leads_per_day: formMaxLeads,
          priority: formPriority,
        });
      }
      setShowModal(false);
      loadData();
    } catch (error: any) {
      alert(error.message || 'Erro ao salvar vendedor');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(seller: Seller) {
    if (!confirm(`Remover ${seller.name}? Os leads atribuídos a ele ficarão sem vendedor.`)) {
      return;
    }

    try {
      await deleteSeller(seller.id);
      loadData();
    } catch (error: any) {
      alert(error.message || 'Erro ao remover vendedor');
    }
  }

  async function handleToggleAvailability(seller: Seller) {
    try {
      await toggleSellerAvailability(seller.id);
      loadData();
    } catch (error: any) {
      alert(error.message || 'Erro ao alterar disponibilidade');
    }
  }

  function addCity() {
    if (newCity.trim() && !formCities.includes(newCity.trim())) {
      setFormCities([...formCities, newCity.trim()]);
      setNewCity('');
    }
  }

  function removeCity(city: string) {
    setFormCities(formCities.filter(c => c !== city));
  }

  function toggleSpecialty(specialty: string) {
    if (formSpecialties.includes(specialty)) {
      setFormSpecialties(formSpecialties.filter(s => s !== specialty));
    } else {
      setFormSpecialties([...formSpecialties, specialty]);
    }
  }

  function addCustomSpecialty() {
    if (newSpecialty.trim() && !formSpecialties.includes(newSpecialty.trim().toLowerCase())) {
      setFormSpecialties([...formSpecialties, newSpecialty.trim().toLowerCase()]);
      setNewSpecialty('');
    }
  }

  // Função para obter o label de uma especialidade
  function getSpecialtyLabel(value: string): string {
    const found = specialtyOptions.find(s => s.value === value);
    return found ? found.label : value.charAt(0).toUpperCase() + value.slice(1);
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Equipe de Vendas</h1>
          <p className="text-gray-500 text-sm sm:text-base">Gerencie seus vendedores e a distribuição de leads</p>
        </div>
        <button
          onClick={openNewModal}
          className="flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 w-full sm:w-auto"
        >
          <Plus className="w-5 h-5" />
          Novo Vendedor
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <Card>
            <div className="flex items-center gap-3 sm:gap-4">
              <div className="p-2 sm:p-3 bg-blue-100 rounded-lg">
                <Users className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-500">Total</p>
                <p className="text-xl sm:text-2xl font-bold">{stats.total_sellers}</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3 sm:gap-4">
              <div className="p-2 sm:p-3 bg-green-100 rounded-lg">
                <ToggleRight className="w-5 h-5 sm:w-6 sm:h-6 text-green-600" />
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-500">Disponíveis</p>
                <p className="text-xl sm:text-2xl font-bold">{stats.available_sellers}</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3 sm:gap-4">
              <div className="p-2 sm:p-3 bg-purple-100 rounded-lg">
                <Target className="w-5 h-5 sm:w-6 sm:h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-500">Distribuídos</p>
                <p className="text-xl sm:text-2xl font-bold">{stats.total_leads_distributed}</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3 sm:gap-4">
              <div className="p-2 sm:p-3 bg-orange-100 rounded-lg">
                <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6 text-orange-600" />
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-500">Conversão</p>
                <p className="text-xl sm:text-2xl font-bold">{stats.avg_conversion_rate}%</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Lista de Vendedores */}
      <Card>
        <CardHeader title="Vendedores" subtitle="Clique em um vendedor para editar" />

        {sellers.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>Nenhum vendedor cadastrado</p>
            <p className="text-sm">Clique em "Novo Vendedor" para começar</p>
          </div>
        ) : (
          <div className="divide-y">
            {sellers.map((seller) => (
              <div
                key={seller.id}
                className="p-4 hover:bg-gray-50 transition-colors"
              >
                {/* Mobile Layout */}
                <div className="block lg:hidden space-y-3">
                  {/* Header com Avatar e Nome */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm ${
                        seller.available && seller.active ? 'bg-green-500' : 'bg-gray-400'
                      }`}>
                        {seller.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-gray-900">{seller.name}</span>
                          {!seller.active && <Badge variant="default">Inativo</Badge>}
                          {seller.on_vacation && <Badge variant="warm">Férias</Badge>}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <Star className={`w-4 h-4 ${seller.priority >= 7 ? 'text-yellow-500 fill-yellow-500' : 'text-gray-300'}`} />
                      <span className="text-sm text-gray-500">{seller.priority}</span>
                    </div>
                  </div>

                  {/* Contato */}
                  <div className="space-y-1 text-sm text-gray-500">
                    <div className="flex items-center gap-2">
                      <Phone className="w-4 h-4" />
                      <span>{seller.whatsapp}</span>
                    </div>
                    {seller.email && (
                      <div className="flex items-center gap-2">
                        <Mail className="w-4 h-4" />
                        <span className="truncate">{seller.email}</span>
                      </div>
                    )}
                  </div>

                  {/* Especialidades */}
                  {seller.specialties && seller.specialties.length > 0 && (
                    <div className="flex gap-1 flex-wrap">
                      {seller.specialties.map(spec => (
                        <span key={spec} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                          {getSpecialtyLabel(spec)}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Cidades */}
                  {seller.cities && seller.cities.length > 0 && (
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <MapPin className="w-3 h-3" />
                      <span>{seller.cities.join(', ')}</span>
                    </div>
                  )}

                  {/* Métricas e Ações */}
                  <div className="flex items-center justify-between pt-3 border-t">
                    <div className="text-sm">
                      <span className="font-medium text-gray-900">{seller.total_leads}</span>
                      <span className="text-gray-500"> leads • </span>
                      <span className="text-gray-500">{seller.conversion_rate}% conversão</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleToggleAvailability(seller)}
                        className={`p-2 rounded-lg transition-colors ${
                          seller.available
                            ? 'bg-green-100 text-green-600'
                            : 'bg-gray-100 text-gray-400'
                        }`}
                      >
                        {seller.available ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />}
                      </button>
                      <button
                        onClick={() => openEditModal(seller)}
                        className="p-2 bg-gray-100 rounded-lg text-gray-600"
                      >
                        <Pencil className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleDelete(seller)}
                        className="p-2 bg-red-50 rounded-lg text-red-600"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Desktop Layout */}
                <div className="hidden lg:flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {/* Avatar */}
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center text-white font-bold ${
                      seller.available && seller.active ? 'bg-green-500' : 'bg-gray-400'
                    }`}>
                      {seller.name.charAt(0).toUpperCase()}
                    </div>

                    {/* Info */}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{seller.name}</span>
                        {!seller.active && (
                          <Badge variant="default">Inativo</Badge>
                        )}
                        {seller.on_vacation && (
                          <Badge variant="warm">Férias</Badge>
                        )}
                        {seller.active && !seller.available && !seller.on_vacation && (
                          <Badge variant="default">Indisponível</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
                        <span className="flex items-center gap-1">
                          <Phone className="w-3 h-3" />
                          {seller.whatsapp}
                        </span>
                        {seller.email && (
                          <span className="flex items-center gap-1">
                            <Mail className="w-3 h-3" />
                            {seller.email}
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {seller.cities && seller.cities.length > 0 && (
                          <div className="flex items-center gap-1">
                            <MapPin className="w-3 h-3 text-gray-400" />
                            <span className="text-xs text-gray-500">
                              {seller.cities.join(', ')}
                            </span>
                          </div>
                        )}
                        {seller.specialties && seller.specialties.length > 0 && (
                          <div className="flex gap-1 flex-wrap">
                            {seller.specialties.map(spec => (
                              <span key={spec} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                                {getSpecialtyLabel(spec)}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Métricas e Ações */}
                  <div className="flex items-center gap-6">
                    {/* Métricas */}
                    <div className="text-right">
                      <div className="text-sm">
                        <span className="font-medium text-gray-900">{seller.total_leads}</span>
                        <span className="text-gray-500"> leads</span>
                      </div>
                      <div className="text-xs text-gray-500">
                        {seller.conversion_rate}% conversão
                      </div>
                    </div>

                    {/* Prioridade */}
                    <div className="flex items-center gap-1" title={`Prioridade: ${seller.priority}`}>
                      <Star className={`w-4 h-4 ${seller.priority >= 7 ? 'text-yellow-500 fill-yellow-500' : 'text-gray-300'}`} />
                      <span className="text-sm text-gray-500">{seller.priority}</span>
                    </div>

                    {/* Ações */}
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleToggleAvailability(seller)}
                        className={`p-2 rounded-lg transition-colors ${
                          seller.available
                            ? 'bg-green-100 text-green-600 hover:bg-green-200'
                            : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
                        }`}
                        title={seller.available ? 'Marcar como indisponível' : 'Marcar como disponível'}
                      >
                        {seller.available ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />}
                      </button>
                      <button
                        onClick={() => openEditModal(seller)}
                        className="p-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-gray-600"
                        title="Editar"
                      >
                        <Pencil className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleDelete(seller)}
                        className="p-2 bg-red-50 rounded-lg hover:bg-red-100 text-red-600"
                        title="Remover"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Modal de Criar/Editar */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
          <div className="bg-white rounded-t-xl sm:rounded-xl shadow-xl w-full sm:max-w-lg max-h-[90vh] overflow-y-auto">
            {/* Header do Modal */}
            <div className="flex items-center justify-between p-4 sm:p-6 border-b sticky top-0 bg-white z-10">
              <h2 className="text-lg sm:text-xl font-bold text-gray-900">
                {editingSeller ? 'Editar Vendedor' : 'Novo Vendedor'}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Form */}
            <div className="p-4 sm:p-6 space-y-4">
              {/* Nome */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome *
                </label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Nome do vendedor"
                />
              </div>

              {/* WhatsApp */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  WhatsApp *
                </label>
                <input
                  type="text"
                  value={formWhatsapp}
                  onChange={(e) => setFormWhatsapp(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="5511999999999"
                />
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={formEmail}
                  onChange={(e) => setFormEmail(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="vendedor@empresa.com"
                />
              </div>

              {/* Cidades */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Cidades que atende
                </label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {formCities.map((city) => (
                    <span
                      key={city}
                      className="flex items-center gap-1 bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm"
                    >
                      {city}
                      <button onClick={() => removeCity(city)}>
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newCity}
                    onChange={(e) => setNewCity(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addCity())}
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="Adicionar cidade"
                  />
                  <button
                    type="button"
                    onClick={addCity}
                    className="px-4 py-3 bg-gray-100 rounded-lg hover:bg-gray-200"
                  >
                    <Plus className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Especialidades */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Especialidades
                </label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {specialtyOptions.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => toggleSpecialty(opt.value)}
                      className={`px-3 py-2 rounded-full text-sm transition-colors ${
                        formSpecialties.includes(opt.value)
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>

                {/* Especialidades customizadas selecionadas */}
                {formSpecialties.filter(s => !specialtyOptions.find(o => o.value === s)).map(custom => (
                  <span
                    key={custom}
                    className="inline-flex items-center gap-1 bg-purple-100 text-purple-700 px-3 py-1 rounded-full text-sm mr-2 mb-2"
                  >
                    {custom}
                    <button onClick={() => toggleSpecialty(custom)}>
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}

                {/* Adicionar especialidade customizada */}
                {allowCustomSpecialty && (
                  <div className="flex gap-2 mt-2">
                    <input
                      type="text"
                      value={newSpecialty}
                      onChange={(e) => setNewSpecialty(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addCustomSpecialty())}
                      className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                      placeholder="Adicionar especialidade customizada"
                    />
                    <button
                      type="button"
                      onClick={addCustomSpecialty}
                      className="px-4 py-3 bg-gray-100 rounded-lg hover:bg-gray-200"
                    >
                      <Plus className="w-5 h-5" />
                    </button>
                  </div>
                )}
              </div>

              {/* Limite de leads */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Limite de leads por dia (0 = sem limite)
                </label>
                <input
                  type="number"
                  value={formMaxLeads}
                  onChange={(e) => setFormMaxLeads(parseInt(e.target.value) || 0)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  min={0}
                />
              </div>

              {/* Prioridade */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Prioridade (1-10)
                </label>
                <input
                  type="range"
                  value={formPriority}
                  onChange={(e) => setFormPriority(parseInt(e.target.value))}
                  className="w-full"
                  min={1}
                  max={10}
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Baixa</span>
                  <span className="font-medium">{formPriority}</span>
                  <span>Alta</span>
                </div>
              </div>
            </div>

            {/* Footer do Modal */}
            <div className="flex items-center justify-end gap-3 p-4 sm:p-6 border-t bg-gray-50 sticky bottom-0">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}