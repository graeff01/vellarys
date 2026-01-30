'use client';

import { useEffect, useState } from 'react';
import {
  Flame,
  TrendingUp,
  Users,
  DollarSign,
  BarChart3,
  Upload,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw
} from 'lucide-react';

// =============================================================================
// TYPES
// =============================================================================

interface PhoenixMetrics {
  total_reactivated: number;
  pending_approval: number;
  response_rate: number;
  total_potential_commission: number;
  contacted_count: number;
}

interface PhoenixLead {
  id: number;
  name: string | null;
  phone: string | null;
  phoenix_status: string | null;
  phoenix_attempts: number;
  phoenix_interest_score: number;
  phoenix_potential_commission: number | null;
  phoenix_ai_analysis: string | null;
  last_phoenix_at: string | null;
  last_activity_at: string | null;
  days_inactive: number;
  original_seller_name: string | null;
}

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================

export default function PhoenixEnginePage() {
  const [metrics, setMetrics] = useState<PhoenixMetrics | null>(null);
  const [leads, setLeads] = useState<PhoenixLead[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>('reactivated'); // pending, reactivated, approved
  const [loading, setLoading] = useState(true);
  const [uploadingCSV, setUploadingCSV] = useState(false);

  useEffect(() => {
    loadMetrics();
    loadLeads();
  }, [filterStatus]);

  const loadMetrics = async () => {
    try {
      const res = await fetch('/api/v1/phoenix/metrics', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
      });
      const data = await res.json();
      setMetrics(data);
    } catch (error) {
      console.error('Erro ao carregar métricas:', error);
    }
  };

  const loadLeads = async () => {
    setLoading(true);
    try {
      const url = filterStatus ? `/api/v1/phoenix/leads?status=${filterStatus}` : '/api/v1/phoenix/leads';
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
      });
      const data = await res.json();
      setLeads(data);
    } catch (error) {
      console.error('Erro ao carregar leads:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (leadId: number, approved: boolean) => {
    try {
      const res = await fetch(`/api/v1/phoenix/approve/${leadId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ approved, notify_seller: true }),
      });

      if (res.ok) {
        alert(approved ? 'Lead aprovado!' : 'Lead rejeitado!');
        loadLeads();
        loadMetrics();
      }
    } catch (error) {
      console.error('Erro ao aprovar:', error);
    }
  };

  const handleCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingCSV(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/v1/phoenix/csv-upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: formData,
      });

      const result = await res.json();

      if (result.success) {
        alert(`${result.added} leads adicionados à fila Phoenix!`);
        loadMetrics();
      } else {
        alert('Erro ao processar CSV');
      }
    } catch (error) {
      console.error('Erro no upload:', error);
    } finally {
      setUploadingCSV(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Flame className="w-8 h-8 text-orange-500" />
          <h1 className="text-3xl font-bold text-gray-900">Phoenix Engine</h1>
        </div>
        <p className="text-gray-600">
          Sistema de Reativação Inteligente de Leads Inativos
        </p>
      </div>

      {/* Métricas */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className="w-5 h-5 text-green-600" />
            <span className="text-sm text-gray-600 font-medium">Reativados</span>
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {metrics?.total_reactivated || 0}
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <div className="flex items-center gap-3 mb-2">
            <Clock className="w-5 h-5 text-yellow-600" />
            <span className="text-sm text-gray-600 font-medium">Aguardando Aprovação</span>
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {metrics?.pending_approval || 0}
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <div className="flex items-center gap-3 mb-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            <span className="text-sm text-gray-600 font-medium">Taxa de Resposta</span>
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {metrics?.response_rate.toFixed(1) || 0}%
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <div className="flex items-center gap-3 mb-2">
            <DollarSign className="w-5 h-5 text-purple-600" />
            <span className="text-sm text-gray-600 font-medium">Comissão Potencial</span>
          </div>
          <p className="text-3xl font-bold text-gray-900">
            R$ {metrics?.total_potential_commission.toFixed(0) || 0}
          </p>
        </div>
      </div>

      {/* Upload CSV */}
      <div className="bg-white rounded-xl shadow-sm p-6 mb-8 border border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-gray-900 mb-1">Reativação em Massa</h3>
            <p className="text-sm text-gray-600">
              Upload de CSV com lista de leads para reativar (formato: phone,name,note)
            </p>
          </div>
          <label className="cursor-pointer">
            <input
              type="file"
              accept=".csv"
              onChange={handleCSVUpload}
              className="hidden"
              disabled={uploadingCSV}
            />
            <div className="flex items-center gap-2 bg-orange-600 text-white px-6 py-3 rounded-lg hover:bg-orange-700 transition-colors">
              {uploadingCSV ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  <span>Processando...</span>
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  <span>Upload CSV</span>
                </>
              )}
            </div>
          </label>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl shadow-sm p-4 mb-6 border border-gray-200">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">Filtrar por:</span>
          <div className="flex gap-2">
            <button
              onClick={() => setFilterStatus('reactivated')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterStatus === 'reactivated'
                  ? 'bg-orange-100 text-orange-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Aguardando Aprovação
            </button>
            <button
              onClick={() => setFilterStatus('approved')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterStatus === 'approved'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Aprovados
            </button>
            <button
              onClick={() => setFilterStatus('rejected')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterStatus === 'rejected'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Rejeitados
            </button>
          </div>
        </div>
      </div>

      {/* Lista de Leads */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-bold text-gray-900">
            Leads Reativados ({leads.length})
          </h3>
        </div>

        {loading ? (
          <div className="p-12 text-center">
            <RefreshCw className="w-8 h-8 text-gray-400 animate-spin mx-auto mb-3" />
            <p className="text-gray-500">Carregando leads...</p>
          </div>
        ) : leads.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">Nenhum lead encontrado</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {leads.map((lead) => (
              <div key={lead.id} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="text-lg font-bold text-gray-900">
                        {lead.name || 'Sem nome'}
                      </h4>
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                        lead.phoenix_interest_score >= 70
                          ? 'bg-red-100 text-red-700'
                          : lead.phoenix_interest_score >= 40
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        Score: {lead.phoenix_interest_score}%
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                      <div>
                        <span className="text-gray-500">Telefone:</span>{' '}
                        <span className="text-gray-900 font-medium">{lead.phone}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Inativo há:</span>{' '}
                        <span className="text-gray-900 font-medium">{lead.days_inactive} dias</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Comissão Potencial:</span>{' '}
                        <span className="text-gray-900 font-medium">
                          R$ {lead.phoenix_potential_commission?.toFixed(0) || 0}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">Vendedor Original:</span>{' '}
                        <span className="text-gray-900 font-medium">
                          {lead.original_seller_name || 'N/A'}
                        </span>
                      </div>
                    </div>

                    {lead.phoenix_ai_analysis && (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-900">
                        <span className="font-medium">Análise da IA:</span> {lead.phoenix_ai_analysis}
                      </div>
                    )}
                  </div>

                  {/* Ações */}
                  {lead.phoenix_status === 'reactivated' && (
                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => handleApprove(lead.id, true)}
                        className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
                      >
                        <CheckCircle className="w-4 h-4" />
                        <span>Aprovar</span>
                      </button>
                      <button
                        onClick={() => handleApprove(lead.id, false)}
                        className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
                      >
                        <XCircle className="w-4 h-4" />
                        <span>Rejeitar</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
