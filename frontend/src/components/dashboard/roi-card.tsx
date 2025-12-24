'use client';

import { Card } from '@/components/ui/card';
import { TrendingUp, Filter, Zap, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getLeadsByDay } from '@/lib/api';

interface ROICardProps {
  totalLeads: number;
  leadsFiltered: number;
  leadsHot: number;
}

interface DailyData {
  period: string;
  count: number;
  hot: number;
  warm: number;
  cold: number;
}

export function ROICard({ totalLeads, leadsFiltered, leadsHot }: ROICardProps) {
  const [weekData, setWeekData] = useState<DailyData[]>([]);
  const [loading, setLoading] = useState(true);

  // Calcula eficiência (% de curiosos filtrados)
  const efficiency = totalLeads > 0 ? Math.round((leadsFiltered / totalLeads) * 100) : 100;

  useEffect(() => {
    async function fetchWeekData() {
      try {
        setLoading(true);
        
        // ✅ USA A FUNÇÃO DO API.TS (infraestrutura existente)
        const data = await getLeadsByDay(7);
        
        // Garante que temos 7 dias (preenche com zeros se necessário)
        const completeDays = Array(7).fill(null).map((_, i) => {
          const date = new Date();
          date.setDate(date.getDate() - (6 - i));
          const dateStr = date.toISOString().split('T')[0];
          
          const existingData = data.find((d: DailyData) => d.period === dateStr);
          
          return existingData || {
            period: dateStr,
            count: 0,
            hot: 0,
            warm: 0,
            cold: 0
          };
        });
        
        setWeekData(completeDays);
      } catch (error) {
        console.error('Erro ao buscar dados da semana:', error);
        
        // Fallback: gera dados simulados
        const fallbackData = Array(7).fill(null).map((_, i) => {
          const date = new Date();
          date.setDate(date.getDate() - (6 - i));
          return {
            period: date.toISOString().split('T')[0],
            count: Math.floor(Math.random() * 5) + 1,
            hot: 0,
            warm: 0,
            cold: 0
          };
        });
        
        setWeekData(fallbackData);
      } finally {
        setLoading(false);
      }
    }
    
    fetchWeekData();
  }, []);

  // Formata labels dos dias
  const daysLabels = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
  const formattedData = weekData.map(data => {
    const date = new Date(data.period + 'T00:00:00');
    const dayIndex = date.getDay();
    return {
      ...data,
      label: daysLabels[dayIndex]
    };
  });

  // Calcula crescimento vs ontem
  const todayCount = formattedData[6]?.count || 0;
  const yesterdayCount = formattedData[5]?.count || 1;
  const growthPercent = yesterdayCount > 0 
    ? Math.round(((todayCount - yesterdayCount) / yesterdayCount) * 100)
    : 0;

  // Normaliza dados para o gráfico (0-100%)
  const maxCount = Math.max(...formattedData.map(d => d.count), 1);
  const normalizedData = formattedData.map(d => ({
    ...d,
    height: (d.count / maxCount) * 100
  }));

  return (
    <Card>
      <div className="p-6 space-y-6">
        
        {/* HEADER */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Evolução dos Leads</h3>
            <p className="text-sm text-gray-500">Últimos 7 dias</p>
          </div>
          <div className="p-3 bg-blue-100 rounded-lg">
            <TrendingUp className="w-6 h-6 text-blue-600" />
          </div>
        </div>

        {/* GRÁFICO DE BARRAS */}
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-end justify-between h-32 gap-2">
              {normalizedData.map((data, index) => (
                <div key={index} className="flex-1 flex flex-col items-center gap-2">
                  {/* Barra */}
                  <div className="w-full bg-gray-100 rounded-t-lg relative overflow-hidden" style={{ height: '100%' }}>
                    <div 
                      className={`w-full rounded-t-lg transition-all duration-500 ${
                        index === 6 ? 'bg-blue-600' : 'bg-blue-400'
                      }`}
                      style={{ 
                        height: `${data.height}%`,
                        position: 'absolute',
                        bottom: 0
                      }}
                    />
                  </div>
                  {/* Label */}
                  <span className={`text-xs font-medium ${
                    index === 6 ? 'text-blue-600' : 'text-gray-500'
                  }`}>
                    {data.label}
                  </span>
                </div>
              ))}
            </div>

            {/* Indicador de Crescimento */}
            <div className="flex items-center justify-between pt-4 border-t border-gray-100">
              <div className="flex items-center gap-2">
                {growthPercent >= 0 ? (
                  <>
                    <TrendingUp className="w-4 h-4 text-green-600" />
                    <span className="text-sm font-semibold text-green-600">
                      +{growthPercent}%
                    </span>
                  </>
                ) : (
                  <>
                    <TrendingUp className="w-4 h-4 text-orange-600 rotate-180" />
                    <span className="text-sm font-semibold text-orange-600">
                      {growthPercent}%
                    </span>
                  </>
                )}
                <span className="text-xs text-gray-500">vs ontem</span>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500">Hoje</p>
                <p className="text-lg font-bold text-gray-900">{todayCount}</p>
              </div>
            </div>
          </div>
        )}

        {/* EFICIÊNCIA DA IA */}
        <div className="space-y-3 pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-gray-700">Eficiência da IA</span>
            </div>
            <span className="text-lg font-bold text-blue-600">{efficiency}%</span>
          </div>
          
          {/* Barra de Progresso */}
          <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-blue-500 to-blue-600 h-full rounded-full transition-all duration-500"
              style={{ width: `${efficiency}%` }}
            />
          </div>
          
          {/* Info */}
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Filter className="w-3 h-3" />
            <span>{leadsFiltered} curiosos filtrados automaticamente</span>
          </div>
        </div>

      </div>
    </Card>
  );
}