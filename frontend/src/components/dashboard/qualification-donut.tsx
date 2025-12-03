'use client';

import { Card } from '@/components/ui/card';

interface QualificationDonutProps {
  data: Record<string, number>;
}

export function QualificationDonut({ data }: QualificationDonutProps) {
  const hot = data?.hot || data?.quente || 0;
  const warm = data?.warm || data?.morno || 0;
  const cold = data?.cold || data?.frio || 0;
  const total = hot + warm + cold;

  // Calcula porcentagens
  const hotPercent = total > 0 ? (hot / total) * 100 : 0;
  const warmPercent = total > 0 ? (warm / total) * 100 : 0;
  const coldPercent = total > 0 ? (cold / total) * 100 : 0;

  // Calcula os ângulos para o SVG
  const hotAngle = (hotPercent / 100) * 360;
  const warmAngle = (warmPercent / 100) * 360;
  const coldAngle = (coldPercent / 100) * 360;

  // Função para criar arco do SVG
  const createArc = (startAngle: number, endAngle: number, color: string) => {
    if (endAngle - startAngle === 0) return null;
    
    const radius = 80;
    const innerRadius = 50;
    const centerX = 100;
    const centerY = 100;
    
    const startRad = (startAngle - 90) * (Math.PI / 180);
    const endRad = (endAngle - 90) * (Math.PI / 180);
    
    const x1 = centerX + radius * Math.cos(startRad);
    const y1 = centerY + radius * Math.sin(startRad);
    const x2 = centerX + radius * Math.cos(endRad);
    const y2 = centerY + radius * Math.sin(endRad);
    
    const x3 = centerX + innerRadius * Math.cos(endRad);
    const y3 = centerY + innerRadius * Math.sin(endRad);
    const x4 = centerX + innerRadius * Math.cos(startRad);
    const y4 = centerY + innerRadius * Math.sin(startRad);
    
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;
    
    const d = `
      M ${x1} ${y1}
      A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}
      L ${x3} ${y3}
      A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${x4} ${y4}
      Z
    `;
    
    return <path d={d} fill={color} className="transition-all duration-500 hover:opacity-80" />;
  };

  const items = [
    { label: 'Quentes', value: hot, percent: hotPercent, color: '#EF4444', bgColor: 'bg-red-500' },
    { label: 'Mornos', value: warm, percent: warmPercent, color: '#F59E0B', bgColor: 'bg-yellow-500' },
    { label: 'Frios', value: cold, percent: coldPercent, color: '#3B82F6', bgColor: 'bg-blue-500' },
  ];

  let currentAngle = 0;

  return (
    <div className="flex flex-col items-center">
      {/* Donut Chart */}
      <div className="relative">
        <svg width="200" height="200" viewBox="0 0 200 200">
          {total === 0 ? (
            // Círculo vazio quando não há dados
            <circle
              cx="100"
              cy="100"
              r="65"
              fill="none"
              stroke="#E5E7EB"
              strokeWidth="30"
            />
          ) : (
            <>
              {items.map((item, index) => {
                const arc = createArc(currentAngle, currentAngle + (item.percent / 100) * 360, item.color);
                currentAngle += (item.percent / 100) * 360;
                return <g key={index}>{arc}</g>;
              })}
            </>
          )}
        </svg>
        
        {/* Centro do donut */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-gray-900">{total}</span>
          <span className="text-sm text-gray-500">leads</span>
        </div>
      </div>

      {/* Legenda */}
      <div className="mt-6 w-full space-y-3">
        {items.map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${item.bgColor}`} />
              <span className="text-sm text-gray-600">{item.label}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-gray-900">{item.value}</span>
              <span className="text-xs text-gray-400">({Math.round(item.percent)}%)</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}