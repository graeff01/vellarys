'use client';

import { Card } from '@/components/ui/card';
import { Clock, DollarSign, TrendingUp, Zap } from 'lucide-react';

interface ROICardProps {
  totalLeads: number;
  leadsFiltered: number; // leads frios (curiosos)
  leadsHot: number;
}

export function ROICard({ totalLeads, leadsFiltered, leadsHot }: ROICardProps) {
  // Estimativas baseadas em médias de mercado
  const MINUTES_PER_LEAD = 8; // Tempo médio que um humano gastaria por lead
  const HOURLY_COST = 25; // Custo médio hora de um atendente (R$)
  
  // Cálculos
  const minutesSaved = totalLeads * MINUTES_PER_LEAD;
  const hoursSaved = Math.round(minutesSaved / 60 * 10) / 10;
  const moneySaved = Math.round((minutesSaved / 60) * HOURLY_COST);
  
  // Eficiência: % de leads que a IA resolveu sozinha (frios + em andamento)
  const aiEfficiency = totalLeads > 0 
    ? Math.round(((totalLeads - leadsHot) / totalLeads) * 100)
    : 0;

  return (
    <Card className="bg-gradient-to-br from-blue-600 to-blue-800 text-white">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold opacity-90">Economia com a IA</h3>
        <div className="p-2 bg-white/20 rounded-lg">
          <Zap className="w-5 h-5" />
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white/10 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-4 h-4 opacity-70" />
            <span className="text-sm opacity-70">Tempo Economizado</span>
          </div>
          <p className="text-2xl font-bold">
            {hoursSaved > 0 ? `${hoursSaved}h` : '0h'}
          </p>
          <p className="text-xs opacity-60 mt-1">
            {totalLeads} leads × {MINUTES_PER_LEAD}min cada
          </p>
        </div>
        
        <div className="bg-white/10 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-1">
            <DollarSign className="w-4 h-4 opacity-70" />
            <span className="text-sm opacity-70">Valor Economizado</span>
          </div>
          <p className="text-2xl font-bold">
            R$ {moneySaved.toLocaleString('pt-BR')}
          </p>
          <p className="text-xs opacity-60 mt-1">
            Base: R$ {HOURLY_COST}/hora atendente
          </p>
        </div>
      </div>
      
      <div className="mt-4 pt-4 border-t border-white/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 opacity-70" />
            <span className="text-sm opacity-70">Eficiência da IA</span>
          </div>
          <span className="text-xl font-bold">{aiEfficiency}%</span>
        </div>
        <div className="mt-2 bg-white/20 rounded-full h-2">
          <div 
            className="bg-green-400 h-2 rounded-full transition-all duration-500"
            style={{ width: `${aiEfficiency}%` }}
          />
        </div>
        <p className="text-xs opacity-60 mt-2">
          {leadsFiltered} curiosos filtrados automaticamente
        </p>
      </div>
    </Card>
  );
}