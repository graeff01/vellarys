'use client';

import { Card } from '@/components/ui/card';
import { LineChart, Target, Clock4 } from 'lucide-react';

interface Lead {
  id: number;
  qualification: string;
  status: string;
  created_at: string;
}

interface LeadsInsightsProps {
  leads: Lead[];
}

export function LeadsInsights({ leads }: LeadsInsightsProps) {
  const total = leads.length;

  const hot = leads.filter((l) =>
    ['hot', 'quente'].includes(l.qualification)
  ).length;
  const warm = leads.filter((l) =>
    ['warm', 'morno'].includes(l.qualification)
  ).length;
  const cold = leads.filter((l) =>
    ['cold', 'frio'].includes(l.qualification)
  ).length;

  const converted = leads.filter((l) =>
    ['converted', 'closed'].includes(l.status)
  ).length;

  const inProgress = leads.filter((l) =>
    ['in_progress', 'em_atendimento', 'qualified', 'qualificado'].includes(
      l.status
    )
  ).length;

  const lost = leads.filter((l) =>
    ['lost', 'perdido'].includes(l.status)
  ).length;

  const conversionRate = total > 0 ? (converted / total) * 100 : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <LineChart className="w-5 h-5 text-blue-500" />
          Insights de desempenho
        </h2>
        <p className="text-xs text-gray-400">
          Visão analítica baseada nos leads listados
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="p-4 space-y-1">
          <p className="text-xs text-gray-500 uppercase tracking-wide">
            Taxa de conversão
          </p>
          <p className="text-2xl font-semibold text-gray-900">
            {conversionRate.toFixed(1)}%
          </p>
          <p className="text-xs text-gray-400">
            {converted} leads convertidos de {total}
          </p>
        </Card>

        <Card className="p-4 space-y-1">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              Funil atual
            </p>
            <Target className="w-4 h-4 text-purple-500" />
          </div>
          <p className="text-sm text-gray-700">
            {inProgress} em atendimento • {lost} perdidos
          </p>
          <p className="text-xs text-gray-400">
            Calibre o atendimento para reduzir perdas no funil.
          </p>
        </Card>

        <Card className="p-4 space-y-1">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              Temperatura
            </p>
            <Clock4 className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-sm text-gray-700">
            {hot} quente • {warm} morno • {cold} frio
          </p>
          <p className="text-xs text-gray-400">
            Leads quentes devem ser priorizados pelos vendedores.
          </p>
        </Card>
      </div>
    </div>
  );
}
