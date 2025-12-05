'use client';

import type { ReactNode } from 'react';
import { LayoutList, LayoutPanelLeft, LineChart } from 'lucide-react';

export type ViewMode = 'table' | 'kanban' | 'insights';

interface LeadsViewSwitchProps {
  value: ViewMode;
  onChange: (value: ViewMode) => void;
}

interface ViewOption {
  value: ViewMode;
  label: string;
  icon: ReactNode;
}

export function LeadsViewSwitch({ value, onChange }: LeadsViewSwitchProps) {
  const options: ViewOption[] = [
    {
      value: 'table',
      label: 'Tabela',
      icon: <LayoutList className="w-4 h-4" />,
    },
    {
      value: 'kanban',
      label: 'Kanban',
      icon: <LayoutPanelLeft className="w-4 h-4" />,
    },
    {
      value: 'insights',
      label: 'Insights',
      icon: <LineChart className="w-4 h-4" />,
    },
  ];

  return (
    <div className="flex items-center gap-2 bg-white p-1 rounded-lg border">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`
            flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition
            ${
              value === opt.value
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            }
          `}
        >
          {opt.icon}
          {opt.label}
        </button>
      ))}
    </div>
  );
}
