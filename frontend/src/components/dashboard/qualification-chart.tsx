'use client';

interface QualificationChartProps {
  data: Record<string, number>;
}

export function QualificationChart({ data }: QualificationChartProps) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  
  // Suporta tanto valores novos (português) quanto antigos (inglês)
  const items = [
    { 
      key: 'quente', 
      label: 'Quentes', 
      color: 'bg-red-500', 
      value: (data.quente || 0) + (data.hot || 0) 
    },
    { 
      key: 'morno', 
      label: 'Mornos', 
      color: 'bg-yellow-500', 
      value: (data.morno || 0) + (data.warm || 0) 
    },
    { 
      key: 'frio', 
      label: 'Frios', 
      color: 'bg-blue-500', 
      value: (data.frio || 0) + (data.cold || 0) 
    },
  ];

  return (
    <div className="space-y-4">
      {items.map((item) => (
        <div key={item.key}>
          <div className="flex justify-between mb-1">
            <span className="text-sm font-medium text-gray-700">{item.label}</span>
            <span className="text-sm text-gray-500">{item.value} ({Math.round((item.value / total) * 100)}%)</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className={`${item.color} h-2 rounded-full transition-all`} style={{ width: `${(item.value / total) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}