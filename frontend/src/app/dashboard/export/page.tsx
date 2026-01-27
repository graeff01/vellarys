'use client';

import { useState } from 'react';
import { FileSpreadsheet, FileText, FileDown, Calendar, Loader2, CheckCircle } from 'lucide-react';
import { getToken } from '@/lib/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

type ExportFormat = 'excel' | 'csv' | 'pdf';
type Period = 'week' | 'month' | 'quarter' | 'year' | 'all';

const periods: { value: Period; label: string }[] = [
  { value: 'week', label: 'Última semana' },
  { value: 'month', label: 'Último mês' },
  { value: 'quarter', label: 'Último trimestre' },
  { value: 'year', label: 'Último ano' },
  { value: 'all', label: 'Todo o período' },
];

const formats: { value: ExportFormat; label: string; description: string; icon: typeof FileSpreadsheet }[] = [
  {
    value: 'excel',
    label: 'Excel',
    description: 'Planilha com abas de Resumo e Leads, formatação profissional',
    icon: FileSpreadsheet
  },
  {
    value: 'csv',
    label: 'CSV',
    description: 'Formato simples para importar em outros sistemas',
    icon: FileText
  },
  {
    value: 'pdf',
    label: 'PDF',
    description: 'Relatório visual para apresentações e reuniões',
    icon: FileDown
  },
];

export default function ExportPage() {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('excel');
  const [selectedPeriod, setSelectedPeriod] = useState<Period>('month');
  const [includeMetrics, setIncludeMetrics] = useState(true);
  const [includeLeads, setIncludeLeads] = useState(true);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleExport() {
    setLoading(true);
    setSuccess(false);

    try {
      const token = getToken();
      const params = new URLSearchParams({
        period: selectedPeriod,
        include_metrics: includeMetrics.toString(),
        include_leads: includeLeads.toString(),
      });

      const response = await fetch(`${API_URL}/export/${selectedFormat}?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Erro ao exportar');
      }

      // Pega o nome do arquivo do header ou usa um padrão
      const contentDisposition = response.headers.get('content-disposition');
      let filename = `relatorio_vellarys.${selectedFormat === 'excel' ? 'xlsx' : selectedFormat}`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=(.+)/);
        if (match) {
          filename = match[1];
        }
      }

      // Baixa o arquivo
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (error) {
      console.error('Erro ao exportar:', error);
      alert('Erro ao exportar. Tente novamente.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Relatórios</h1>
        <p className="text-gray-600">Exporte seus dados de leads e métricas</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Coluna 1: Formato */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <FileDown className="w-5 h-5 text-blue-600" />
            Formato
          </h2>
          <div className="space-y-3">
            {formats.map((format) => (
              <label
                key={format.value}
                className={`flex items-start gap-3 p-4 rounded-lg border-2 cursor-pointer transition-all ${selectedFormat === format.value
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                  }`}
              >
                <input
                  type="radio"
                  name="format"
                  value={format.value}
                  checked={selectedFormat === format.value}
                  onChange={(e) => setSelectedFormat(e.target.value as ExportFormat)}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <format.icon className={`w-5 h-5 ${selectedFormat === format.value ? 'text-blue-600' : 'text-gray-400'}`} />
                    <span className="font-medium text-gray-900">{format.label}</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">{format.description}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Coluna 2: Período */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-blue-600" />
            Período
          </h2>
          <div className="space-y-2">
            {periods.map((period) => (
              <label
                key={period.value}
                className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${selectedPeriod === period.value
                    ? 'bg-blue-50 text-blue-700'
                    : 'hover:bg-gray-50 text-gray-700'
                  }`}
              >
                <input
                  type="radio"
                  name="period"
                  value={period.value}
                  checked={selectedPeriod === period.value}
                  onChange={(e) => setSelectedPeriod(e.target.value as Period)}
                />
                <span>{period.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Coluna 3: Opções */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Opções</h2>

          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={includeMetrics}
                onChange={(e) => setIncludeMetrics(e.target.checked)}
                className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div>
                <span className="font-medium text-gray-900">Incluir métricas</span>
                <p className="text-sm text-gray-500">Resumo com totais e estatísticas</p>
              </div>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={includeLeads}
                onChange={(e) => setIncludeLeads(e.target.checked)}
                className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div>
                <span className="font-medium text-gray-900">Incluir lista de leads</span>
                <p className="text-sm text-gray-500">Dados completos de cada lead</p>
              </div>
            </label>
          </div>

          {/* Botão de exportar */}
          <div className="mt-8">
            <button
              onClick={handleExport}
              disabled={loading || (!includeMetrics && !includeLeads)}
              className={`w-full py-4 px-6 rounded-xl font-semibold text-white transition-all flex items-center justify-center gap-2 ${loading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : success
                    ? 'bg-green-500'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Gerando...
                </>
              ) : success ? (
                <>
                  <CheckCircle className="w-5 h-5" />
                  Baixado!
                </>
              ) : (
                <>
                  <FileDown className="w-5 h-5" />
                  Exportar {formats.find(f => f.value === selectedFormat)?.label}
                </>
              )}
            </button>

            {!includeMetrics && !includeLeads && (
              <p className="text-sm text-red-500 mt-2 text-center">
                Selecione ao menos uma opção para exportar
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-green-50 rounded-xl p-4 border border-green-200">
          <div className="flex items-center gap-3">
            <FileSpreadsheet className="w-8 h-8 text-green-600" />
            <div>
              <h3 className="font-semibold text-green-900">Excel</h3>
              <p className="text-sm text-green-700">Ideal para análises e filtros avançados</p>
            </div>
          </div>
        </div>

        <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
          <div className="flex items-center gap-3">
            <FileText className="w-8 h-8 text-blue-600" />
            <div>
              <h3 className="font-semibold text-blue-900">CSV</h3>
              <p className="text-sm text-blue-700">Perfeito para importar em CRMs</p>
            </div>
          </div>
        </div>

        <div className="bg-red-50 rounded-xl p-4 border border-red-200">
          <div className="flex items-center gap-3">
            <FileDown className="w-8 h-8 text-red-600" />
            <div>
              <h3 className="font-semibold text-red-900">PDF</h3>
              <p className="text-sm text-red-700">Ótimo para apresentar ao cliente</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}