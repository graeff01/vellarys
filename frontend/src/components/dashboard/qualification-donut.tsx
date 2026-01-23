'use client';

import React from 'react';

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

  // Função para criar arco do SVG
  const createArc = (startAngle: number, endAngle: number, color: string) => {
    if (endAngle - startAngle === 0) return null;

    const radius = 85;
    const innerRadius = 60;
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

    return <path d={d} fill={color} className="transition-all duration-700 hover:brightness-110 cursor-pointer" />;
  };

  const items = [
    { label: 'Quentes', value: hot, percent: hotPercent, color: '#e11d48', bgColor: 'bg-rose-600' }, // Rose 600
    { label: 'Mornos', value: warm, percent: warmPercent, color: '#f59e0b', bgColor: 'bg-amber-500' }, // Amber 500
    { label: 'Frios', value: cold, percent: coldPercent, color: '#3b82f6', bgColor: 'bg-blue-500' },   // Blue 500
  ];

  let currentAngle = 0;

  return (
    <div className="flex flex-col items-center h-full overflow-hidden">
      {/* Donut Chart - totalmente responsivo */}
      <div className="relative group flex-1 w-full flex items-center justify-center min-h-0">
        <svg viewBox="0 0 200 200" className="drop-shadow-sm w-full h-full max-w-[200px] max-h-[200px]">
          {total === 0 ? (
            <circle
              cx="100"
              cy="100"
              r="72.5"
              fill="none"
              stroke="#f1f5f9"
              strokeWidth="25"
            />
          ) : (
            <>
              {items.map((item, index) => {
                const angleSize = (item.percent / 100) * 360;
                const arc = createArc(currentAngle, currentAngle + angleSize, item.color);
                currentAngle += angleSize;
                return <g key={index}>{arc}</g>;
              })}
            </>
          )}
        </svg>

        {/* Centro do donut */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-4xl font-extrabold text-slate-900 leading-none">{total}</span>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Total Leads</span>
        </div>
      </div>

      {/* Legenda Estilizada - compacta */}
      <div className="w-full space-y-1 px-1 shrink-0 mt-2">
        {items.map((item) => (
          <div key={item.label} className="flex items-center justify-between p-1 rounded hover:bg-slate-50 transition-all">
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${item.bgColor} shrink-0`} />
              <span className="text-[10px] font-bold text-slate-600">{item.label}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-extrabold text-slate-900">{item.value}</span>
              <span className="text-[8px] font-bold text-slate-400">{Math.round(item.percent)}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}