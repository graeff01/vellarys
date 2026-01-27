'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { getToken } from '@/lib/auth';
import { X, Loader2 } from 'lucide-react';

interface Lead {
  id: number;
  name: string;
  phone: string;
}

interface Seller {
  id: number;
  name: string;
}

interface AppointmentModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  defaultDate?: Date;
}

export function AppointmentModal({ open, onClose, onSuccess, defaultDate }: AppointmentModalProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  const [formData, setFormData] = useState({
    lead_id: '',
    seller_id: '',
    title: '',
    description: '',
    appointment_type: 'visit',
    scheduled_at: defaultDate ? formatDateTime(defaultDate) : '',
    duration_minutes: 60,
    location: '',
  });

  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [open]);

  useEffect(() => {
    if (defaultDate) {
      setFormData(prev => ({
        ...prev,
        scheduled_at: formatDateTime(defaultDate)
      }));
    }
  }, [defaultDate]);

  function formatDateTime(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  }

  async function loadData() {
    try {
      setLoadingData(true);
      const token = getToken();
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://hopeful-purpose-production-3a2b.up.railway.app/api/v1';

      // Buscar leads
      const leadsResponse = await fetch(`${apiUrl}/leads?limit=500`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (leadsResponse.ok) {
        const leadsData = await leadsResponse.json();
        console.log('📋 Leads data recebido:', leadsData);

        // API de leads retorna {items: [...], total: 10}
        if (leadsData.items && Array.isArray(leadsData.items)) {
          setLeads(leadsData.items);
          console.log('✅ Carregados', leadsData.items.length, 'leads');
        } else if (Array.isArray(leadsData)) {
          setLeads(leadsData);
          console.log('✅ Carregados', leadsData.length, 'leads');
        } else {
          console.warn('⚠️ Formato inesperado de leads:', leadsData);
          setLeads([]);
        }
      }

      // Buscar sellers
      const sellersResponse = await fetch(`${apiUrl}/sellers?limit=100`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (sellersResponse.ok) {
        const sellersData = await sellersResponse.json();
        console.log('👥 Sellers data recebido:', sellersData);

        // API de sellers retorna {sellers: [...], total: 10}
        if (sellersData.sellers && Array.isArray(sellersData.sellers)) {
          setSellers(sellersData.sellers);
          console.log('✅ Carregados', sellersData.sellers.length, 'vendedores');
        } else if (Array.isArray(sellersData)) {
          setSellers(sellersData);
          console.log('✅ Carregados', sellersData.length, 'vendedores');
        } else {
          console.warn('⚠️ Formato inesperado de sellers:', sellersData);
          setSellers([]);
        }
      }
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
    } finally {
      setLoadingData(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!formData.lead_id || !formData.seller_id || !formData.title || !formData.scheduled_at) {
      toast({
        variant: 'destructive',
        title: 'Campos obrigatórios',
        description: 'Preencha todos os campos obrigatórios'
      });
      return;
    }

    try {
      setLoading(true);
      const token = getToken();
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://hopeful-purpose-production-3a2b.up.railway.app/api/v1';

      const payload = {
        ...formData,
        lead_id: parseInt(formData.lead_id),
        seller_id: parseInt(formData.seller_id),
        scheduled_at: new Date(formData.scheduled_at).toISOString(),
      };

      console.log('📅 Criando agendamento:', payload);

      const response = await fetch(`${apiUrl}/appointments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Erro ao criar agendamento');
      }

      toast({
        title: 'Agendamento criado!',
        description: 'O agendamento foi criado com sucesso'
      });

      onSuccess();
      onClose();
      resetForm();
    } catch (err: any) {
      console.error('Erro ao criar agendamento:', err);
      toast({
        variant: 'destructive',
        title: 'Erro ao criar agendamento',
        description: err.message || 'Tente novamente'
      });
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setFormData({
      lead_id: '',
      seller_id: '',
      title: '',
      description: '',
      appointment_type: 'visit',
      scheduled_at: defaultDate ? formatDateTime(defaultDate) : '',
      duration_minutes: 60,
      location: '',
    });
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Novo Agendamento</DialogTitle>
        </DialogHeader>

        {loadingData ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Lead */}
            <div>
              <Label htmlFor="lead_id">Lead *</Label>
              <select
                id="lead_id"
                value={formData.lead_id}
                onChange={(e) => setFormData({ ...formData, lead_id: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">Selecione um lead</option>
                {leads.map(lead => (
                  <option key={lead.id} value={lead.id}>
                    {lead.name} - {lead.phone}
                  </option>
                ))}
              </select>
            </div>

            {/* Seller */}
            <div>
              <Label htmlFor="seller_id">Vendedor *</Label>
              <select
                id="seller_id"
                value={formData.seller_id}
                onChange={(e) => setFormData({ ...formData, seller_id: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">Selecione um vendedor</option>
                {sellers.map(seller => (
                  <option key={seller.id} value={seller.id}>
                    {seller.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Título */}
            <div>
              <Label htmlFor="title">Título *</Label>
              <input
                id="title"
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Ex: Visita ao imóvel"
                required
              />
            </div>

            {/* Tipo */}
            <div>
              <Label htmlFor="appointment_type">Tipo</Label>
              <select
                id="appointment_type"
                value={formData.appointment_type}
                onChange={(e) => setFormData({ ...formData, appointment_type: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="visit">Visita</option>
                <option value="call">Ligação</option>
                <option value="meeting">Reunião</option>
                <option value="demo">Demonstração</option>
                <option value="videocall">Videochamada</option>
              </select>
            </div>

            {/* Data e Hora */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="scheduled_at">Data e Hora *</Label>
                <input
                  id="scheduled_at"
                  type="datetime-local"
                  value={formData.scheduled_at}
                  onChange={(e) => setFormData({ ...formData, scheduled_at: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <Label htmlFor="duration_minutes">Duração (min)</Label>
                <input
                  id="duration_minutes"
                  type="number"
                  value={formData.duration_minutes}
                  onChange={(e) => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="15"
                  step="15"
                />
              </div>
            </div>

            {/* Localização */}
            <div>
              <Label htmlFor="location">Localização</Label>
              <input
                id="location"
                type="text"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Ex: Rua ABC, 123 - Centro"
              />
            </div>

            {/* Descrição */}
            <div>
              <Label htmlFor="description">Observações</Label>
              <textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="Detalhes adicionais sobre o agendamento"
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
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    Criando...
                  </>
                ) : (
                  'Criar Agendamento'
                )}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
