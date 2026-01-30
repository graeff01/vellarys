'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Loader2, Building2, User, DollarSign, FileText, X } from 'lucide-react';
import { getToken } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';

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

export function CreateOpportunityModal({ open, onClose, onSuccess }: CreateOpportunityModalProps) {
  const [loading, setLoading] = useState(false);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  const [formData, setFormData] = useState({
    lead_id: '',
    seller_id: '',
    title: '',
    value: '',
    notes: '',
    product_name: '',
  });

  const { toast } = useToast();

  useEffect(() => {
    if (open) {
      loadLeadsAndSellers();
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
      product_name: '',
    });
  }

  async function loadLeadsAndSellers() {
    try {
      setLoadingData(true);
      const token = getToken();

      const [leadsRes, sellersRes] = await Promise.all([
        fetch(`${API_URL}/v1/leads?limit=100`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/v1/sellers`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
      ]);

      if (leadsRes.ok && sellersRes.ok) {
        const leadsData = await leadsRes.json();
        const sellersData = await sellersRes.json();

        setLeads(leadsData.items || []);
        setSellers(sellersData.sellers || []);
      }
    } catch (error) {
      console.error('Erro carregando dados:', error);
      toast({
        variant: 'destructive',
        title: 'Erro ao carregar dados',
        description: 'Não foi possível carregar leads e vendedores'
      });
    } finally {
      setLoadingData(false);
    }
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
        product_name: formData.product_name || null,
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
      <DialogContent className="max-w-xl p-0 overflow-hidden border-none shadow-2xl rounded-3xl">
        <DialogHeader className="px-8 py-6 bg-white border-b border-gray-100 flex flex-row items-center justify-between space-y-0">
          <div>
            <DialogTitle className="text-xl font-black text-gray-900 flex items-center gap-2">
              <Plus className="w-5 h-5 text-blue-600" />
              Nova Oportunidade
            </DialogTitle>
            <DialogDescription className="text-xs font-medium text-gray-400 mt-0.5">
              Preencha os dados básicos para converter este lead.
            </DialogDescription>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </DialogHeader>

        {loadingData ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <Loader2 className="w-10 h-10 animate-spin text-blue-600" />
            <p className="text-gray-400 text-sm font-medium">Sincronizando dados...</p>
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

              {/* Produto/Imóvel & Vendedor */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="product_name" className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
                    <Building2 className="w-3 h-3" /> Imóvel/Referência
                  </Label>
                  <Input
                    id="product_name"
                    value={formData.product_name}
                    onChange={(e) => setFormData(prev => ({ ...prev, product_name: e.target.value }))}
                    placeholder="Ref: 123456"
                    className="h-11 px-4 bg-gray-50 border-transparent rounded-xl focus:bg-white focus:border-blue-500 font-bold transition-all text-sm"
                  />
                </div>

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
              </div>

              {/* Valor & Observações */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-2 col-span-1">
                  <Label htmlFor="value" className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
                    <DollarSign className="w-3 h-3" /> Valor (BRL)
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

                <div className="space-y-2 col-span-2">
                  <Label htmlFor="notes" className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Observações Internas</Label>
                  <Textarea
                    id="notes"
                    value={formData.notes}
                    onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                    placeholder="Notas relevantes para o fechamento..."
                    className="min-h-[44px] max-h-[120px] px-4 py-3 bg-gray-50 border-transparent rounded-xl focus:bg-white focus:border-blue-500 font-medium transition-all text-sm"
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-4 pt-4 border-t border-gray-50">
              <Button
                type="button"
                variant="ghost"
                onClick={onClose}
                className="flex-1 h-12 rounded-xl text-gray-400 font-bold hover:text-gray-600 hover:bg-gray-100 transition-all"
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
