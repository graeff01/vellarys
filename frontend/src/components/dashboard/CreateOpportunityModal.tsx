'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Loader2, Building2, User, DollarSign, FileText } from 'lucide-react';
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

    console.log('📝 [CREATE OPP] Form data:', formData);

    // Validação detalhada
    const errors = [];
    if (!formData.lead_id || formData.lead_id === '') {
      errors.push('Lead');
    }
    if (!formData.title || formData.title.trim() === '') {
      errors.push('Título');
    }

    if (errors.length > 0) {
      toast({
        variant: 'destructive',
        title: 'Campos obrigatórios faltando',
        description: `Preencha: ${errors.join(', ')}`
      });
      return;
    }

    try {
      setLoading(true);
      const token = getToken();

      // Converter valor de reais para centavos
      const valueInCents = formData.value ? Math.round(parseFloat(formData.value) * 100) : 0;

      const payload = {
        lead_id: parseInt(formData.lead_id),
        seller_id: formData.seller_id ? parseInt(formData.seller_id) : null,
        title: formData.title,
        value: valueInCents,
        notes: formData.notes || null,
        product_name: formData.product_name || null,
      };

      console.log('📤 [CREATE OPP] Enviando payload:', payload);

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
        description: 'A oportunidade foi criada com sucesso'
      });

      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('Erro ao criar oportunidade:', error);
      toast({
        variant: 'destructive',
        title: 'Erro ao criar',
        description: error.message || 'Tente novamente'
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-2xl flex items-center gap-2">
            <Plus className="w-6 h-6 text-blue-600" />
            Nova Oportunidade
          </DialogTitle>
        </DialogHeader>

        {loadingData ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 mt-4">
            {/* Lead */}
            <div>
              <Label htmlFor="lead_id" className="flex items-center gap-2 mb-2">
                <User className="w-4 h-4 text-blue-600" />
                Lead *
              </Label>
              <select
                id="lead_id"
                value={formData.lead_id}
                onChange={(e) => {
                  console.log('🔵 [SELECT LEAD] Selecionado:', e.target.value);
                  setFormData(prev => ({ ...prev, lead_id: e.target.value }));
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              >
                <option value="">Selecione um lead</option>
                {leads.map(lead => (
                  <option key={lead.id} value={lead.id.toString()}>
                    {lead.name} - {lead.phone}
                  </option>
                ))}
              </select>
            </div>

            {/* Título */}
            <div>
              <Label htmlFor="title" className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-blue-600" />
                Título *
              </Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => {
                  console.log('📝 [INPUT TITLE] Digitado:', e.target.value);
                  setFormData(prev => ({ ...prev, title: e.target.value }));
                }}
                placeholder="Ex: Casa 3 Quartos em Porto Alegre"
                required
              />
            </div>

            {/* Produto/Imóvel */}
            <div>
              <Label htmlFor="product_name" className="flex items-center gap-2 mb-2">
                <Building2 className="w-4 h-4 text-blue-600" />
                Produto/Imóvel
              </Label>
              <Input
                id="product_name"
                value={formData.product_name}
                onChange={(e) => setFormData(prev => ({ ...prev, product_name: e.target.value }))}
                placeholder="Ex: Código 722585"
              />
            </div>

            {/* Vendedor */}
            <div>
              <Label htmlFor="seller_id" className="flex items-center gap-2 mb-2">
                <User className="w-4 h-4 text-blue-600" />
                Vendedor
              </Label>
              <select
                id="seller_id"
                value={formData.seller_id}
                onChange={(e) => setFormData(prev => ({ ...prev, seller_id: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Nenhum</option>
                {sellers.map(seller => (
                  <option key={seller.id} value={seller.id.toString()}>
                    {seller.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Valor */}
            <div>
              <Label htmlFor="value" className="flex items-center gap-2 mb-2">
                <DollarSign className="w-4 h-4 text-blue-600" />
                Valor (R$)
              </Label>
              <Input
                id="value"
                type="number"
                step="0.01"
                min="0"
                value={formData.value}
                onChange={(e) => setFormData(prev => ({ ...prev, value: e.target.value }))}
                placeholder="Ex: 450000.00"
              />
            </div>

            {/* Notas */}
            <div>
              <Label htmlFor="notes">Observações</Label>
              <Textarea
                id="notes"
                value={formData.notes}
                onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Informações adicionais sobre a oportunidade..."
                rows={3}
              />
            </div>

            {/* Botões */}
            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                className="flex-1"
                disabled={loading}
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                className="flex-1"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Criando...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-2" />
                    Criar Oportunidade
                  </>
                )}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
