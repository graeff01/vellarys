'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Loader2, Building2, User, DollarSign, FileText, X, Search, Check } from 'lucide-react';
import { getToken } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';
import { Card } from '@/components/ui/card';

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/v1$/, '');

interface CreateOpportunityModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface Lead {
  id: number;
  name: string;
  phone: string;
}

interface Seller {
  id: number;
  name: string;
}

interface Product {
  id: number;
  name: string;
  slug?: string;
  attributes?: {
    codigo?: string;
    tipo?: string;
    regiao?: string;
    preco?: number;
    quartos?: number;
    banheiros?: number;
    vagas?: number;
    metragem?: number;
    descricao?: string;
  };
  description?: string;
}

export function CreateOpportunityModal({ open, onClose, onSuccess }: CreateOpportunityModalProps) {
  const [loading, setLoading] = useState(false);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loadingData, setLoadingData] = useState(true);
  const [showPropertySelector, setShowPropertySelector] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [searching, setSearching] = useState(false);

  const [formData, setFormData] = useState({
    lead_id: '',
    seller_id: '',
    title: '',
    value: '',
    notes: '',
    product_id: '',
    product_name: '',
    product_data: null as any,
  });

  const { toast } = useToast();

  useEffect(() => {
    if (open) {
      loadInitialData();
      resetForm();
    }
  }, [open]);

  function resetForm() {
    setFormData({
      lead_id: '',
      seller_id: '',
      title: '',
      value: '',
      notes: '',
      product_id: '',
      product_name: '',
      product_data: null,
    });
    setSearchTerm('');
  }

  async function loadInitialData() {
    try {
      setLoadingData(true);
      const token = getToken();

      const [leadsRes, sellersRes, productsRes] = await Promise.all([
        fetch(`${API_URL}/v1/leads?limit=100`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/v1/sellers`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/v1/products?limit=200`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
      ]);

      if (leadsRes.ok && sellersRes.ok && productsRes.ok) {
        const leadsData = await leadsRes.json();
        const sellersData = await sellersRes.json();
        const productsData = await productsRes.json();

        setLeads(leadsData.items || []);
        setSellers(sellersData.sellers || []);
        setProducts(productsData || []);
      }
    } catch (error) {
      console.error('Erro carregando dados:', error);
      toast({
        variant: 'destructive',
        title: 'Erro ao carregar dados',
        description: 'Não foi possível carregar leads, vendedores e produtos'
      });
    } finally {
      setLoadingData(false);
    }
  }

  const filteredProducts = products.filter(p => {
    const code = p.attributes?.codigo || '';
    const name = p.name || '';
    return code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      name.toLowerCase().includes(searchTerm.toLowerCase());
  });

  useEffect(() => {
    if (showPropertySelector && searchTerm.length >= 3) {
      const delayDebounceFn = setTimeout(() => {
        searchProducts(searchTerm);
      }, 600);
      return () => clearTimeout(delayDebounceFn);
    }
  }, [searchTerm, showPropertySelector]);

  async function searchProducts(query: string) {
    try {
      setSearching(true);
      const token = getToken();
      const res = await fetch(`${API_URL}/v1/products?search=${encodeURIComponent(query)}&limit=15`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setProducts(prev => {
          const newItems = data.filter((p: any) =>
            !prev.some(old => (old.id > 0 && old.id === p.id) || (old.slug === p.slug))
          );
          return [...prev, ...newItems];
        });
      }
    } catch (err) {
      console.error("Erro na busca remota:", err);
    } finally {
      setSearching(false);
    }
  }

  function handleSelectProperty(product: Product) {
    const pData = {
      codigo: product.attributes?.codigo,
      tipo: product.attributes?.tipo,
      regiao: product.attributes?.regiao,
      preco: product.attributes?.preco,
      quartos: product.attributes?.quartos,
      banheiros: product.attributes?.banheiros,
      vagas: product.attributes?.vagas,
      metragem: product.attributes?.metragem,
      descricao: product.description || product.attributes?.descricao,
    };

    setFormData(prev => ({
      ...prev,
      product_id: product.id.toString(),
      product_name: product.name,
      product_data: pData,
      title: prev.title || product.name, // Auto preenche o título se estiver vazio
      value: product.attributes?.preco ? (product.attributes.preco / 100).toString() : prev.value
    }));
    setShowPropertySelector(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const errors = [];
    if (!formData.lead_id) errors.push('Lead');
    if (!formData.title.trim()) errors.push('Título');

    if (errors.length > 0) {
      toast({
        variant: 'destructive',
        title: 'Campos obrigatórios',
        description: `Preencha: ${errors.join(', ')}`
      });
      return;
    }

    try {
      setLoading(true);
      const token = getToken();

      const valueInCents = formData.value ? Math.round(parseFloat(formData.value) * 100) : 0;

      const payload = {
        lead_id: parseInt(formData.lead_id),
        seller_id: formData.seller_id ? parseInt(formData.seller_id) : null,
        title: formData.title,
        value: valueInCents,
        notes: formData.notes || null,
        product_id: formData.product_id ? parseInt(formData.product_id) : null,
        product_name: formData.product_name || null,
        product_data: formData.product_data,
      };

      const response = await fetch(`${API_URL}/v1/opportunities`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Erro ao criar oportunidade');
      }

      toast({
        title: 'Oportunidade criada!',
        description: 'A nova oportunidade foi registrada com sucesso.'
      });

      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('Erro ao criar oportunidade:', error);
      toast({
        variant: 'destructive',
        title: 'Erro ao criar',
        description: error.message || 'Houve um erro no servidor. Tente novamente.'
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl p-0 overflow-hidden border-none shadow-2xl rounded-3xl">
        <DialogHeader className="px-8 py-6 bg-white border-b border-gray-100 flex flex-row items-center justify-between space-y-0 text-left">
          <div className="flex-1">
            <DialogTitle className="text-xl font-black text-gray-900 flex items-center gap-2">
              <Plus className="w-5 h-5 text-blue-600" />
              Nova Oportunidade
            </DialogTitle>
            <DialogDescription className="text-xs font-medium text-gray-400 mt-0.5">
              Converta seu lead em uma nova negociação.
            </DialogDescription>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors order-last">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </DialogHeader>

        {loadingData ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <Loader2 className="w-10 h-10 animate-spin text-blue-600" />
            <p className="text-gray-400 text-sm font-medium">Sincronizando dados...</p>
          </div>
        ) : showPropertySelector ? (
          <div className="flex flex-col h-[500px] bg-white">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-gray-900">Selecionar Imóvel do Site</h3>
                <Button variant="ghost" size="sm" onClick={() => setShowPropertySelector(false)}>Voltar</Button>
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Buscar por código ou região..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 h-11 bg-gray-50 border-none rounded-xl"
                  autoFocus
                />
                {searching && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  </div>
                )}
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {products.length === 0 && !searching ? ( // Use products directly, and check searching state
                <div className="text-center py-10 text-gray-400">Nenhum imóvel encontrado.</div>
              ) : (
                filteredProducts.map(p => (
                  <button
                    key={p.id}
                    onClick={() => handleSelectProperty(p)}
                    className="w-full text-left p-4 hover:bg-blue-50 border border-transparent hover:border-blue-100 rounded-2xl transition-all flex items-center justify-between group"
                  >
                    <div>
                      <p className="font-bold text-gray-900 text-sm group-hover:text-blue-700">{p.name}</p>
                      {p.attributes?.codigo && (
                        <p className="text-xs text-blue-500 font-bold mt-0.5">CÓDIGO: {p.attributes.codigo}</p>
                      )}
                    </div>
                    <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-blue-500" />
                  </button>
                ))
              )}
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-8 space-y-6 bg-white">
            <div className="grid grid-cols-1 gap-6">

              {/* Lead & Título */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="lead_id" className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
                    <User className="w-3 h-3" /> Lead Responsável *
                  </Label>
                  <select
                    id="lead_id"
                    value={formData.lead_id}
                    onChange={(e) => setFormData(prev => ({ ...prev, lead_id: e.target.value }))}
                    className="w-full h-11 px-4 bg-gray-50 border border-transparent rounded-xl focus:bg-white focus:border-blue-500 transition-all font-bold text-sm text-gray-700 outline-none"
                    required
                  >
                    <option value="">Selecione...</option>
                    {leads.map(lead => (
                      <option key={lead.id} value={lead.id.toString()}>
                        {lead.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="title" className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
                    <FileText className="w-3 h-3" /> Título da Negociação *
                  </Label>
                  <Input
                    id="title"
                    value={formData.title}
                    onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                    placeholder="Ex: Apartamento Centro"
                    className="h-11 px-4 bg-gray-50 border-transparent rounded-xl focus:bg-white focus:border-blue-500 font-bold transition-all text-sm"
                    required
                  />
                </div>
              </div>

              {/* Botão de Atalho para Selecionar Imóvel */}
              <div className="bg-blue-50/50 border border-dashed border-blue-200 rounded-3xl p-5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-blue-100 flex items-center justify-center">
                    <Building2 className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-xs font-black text-blue-600 uppercase tracking-widest">Imóvel de Referência</p>
                    <p className="text-sm font-bold text-gray-600">
                      {formData.product_name ? `${formData.product_name} (${formData.product_data?.codigo || 'S/Ref'})` : "Clique para selecionar do site"}
                    </p>
                  </div>
                </div>
                <Button
                  type="button"
                  onClick={() => setShowPropertySelector(true)}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl"
                  size="sm"
                >
                  Selecionar Imóvel
                </Button>
              </div>

              {/* Vendedor & Valor */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="seller_id" className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
                    <User className="w-3 h-3" /> Corretor Atribuído
                  </Label>
                  <select
                    id="seller_id"
                    value={formData.seller_id}
                    onChange={(e) => setFormData(prev => ({ ...prev, seller_id: e.target.value }))}
                    className="w-full h-11 px-4 bg-gray-50 border border-transparent rounded-xl focus:bg-white focus:border-blue-500 transition-all font-bold text-sm text-gray-700 outline-none"
                  >
                    <option value="">Opcional (Sem corretor)</option>
                    {sellers.map(seller => (
                      <option key={seller.id} value={seller.id.toString()}>
                        {seller.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="value" className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
                    <DollarSign className="w-3 h-3" /> Valor Estimado (BRL)
                  </Label>
                  <div className="relative">
                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-bold text-xs">R$</span>
                    <Input
                      id="value"
                      type="number"
                      step="0.01"
                      value={formData.value}
                      onChange={(e) => setFormData(prev => ({ ...prev, value: e.target.value }))}
                      className="h-11 pl-10 pr-4 bg-gray-50 border-transparent rounded-xl focus:bg-white focus:border-blue-500 font-bold transition-all text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Notas */}
              <div className="space-y-2">
                <Label htmlFor="notes" className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Observações Internas</Label>
                <Textarea
                  id="notes"
                  value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  placeholder="Notas relevantes para o fechamento..."
                  className="min-h-[60px] max-h-[120px] px-4 py-3 bg-gray-50 border-transparent rounded-xl focus:bg-white focus:border-blue-500 font-medium transition-all text-sm"
                />
              </div>
            </div>

            <div className="flex gap-4 pt-4 border-t border-gray-50">
              <Button
                type="button"
                variant="ghost"
                onClick={onClose}
                className="flex-1 h-12 rounded-xl text-gray-400 font-bold hover:text-gray-600 hover:bg-gray-100 transition-all font-sans"
                disabled={loading}
              >
                Descartar
              </Button>
              <Button
                type="submit"
                className="flex-[2] h-12 bg-blue-600 hover:bg-blue-700 text-white font-black rounded-xl shadow-lg shadow-blue-100 transition-all active:scale-95 disabled:opacity-50"
                disabled={loading}
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  "Salvar Oportunidade"
                )}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

function ChevronRight({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="m9 18 6-6-6-6" /></svg>
  );
}
