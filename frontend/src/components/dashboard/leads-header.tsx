'use client';

import { Users, Flame, Snowflake } from 'lucide-react';

interface LeadsHeaderProps {
  total: number;
  hot: number;
  warm: number;
  cold: number;
}

export function LeadsHeader({ total, hot, warm, cold }: LeadsHeaderProps) {
  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
          Leads
        </h1>
        <p className="text-gray-500 text-sm">
          Panorama em tempo real dos leads que entram pela IA Vellarys.
        </p>
      </div>

      <div className="flex flex-wrap gap-3 text-sm">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-50 border border-gray-200">
          <Users className="w-4 h-4 text-gray-500" />
          <span className="font-medium text-gray-800">{total}</span>
          <span className="text-gray-500 text-xs">leads</span>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-orange-50 border border-orange-100">
          <Flame className="w-4 h-4 text-orange-500" />
          <span className="text-xs text-gray-500 uppercase tracking-wide">
            QUENTE
          </span>
          <span className="font-semibold text-gray-800">{hot}</span>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-50 border border-blue-100">
          <Snowflake className="w-4 h-4 text-blue-500" />
          <span className="text-xs text-gray-500 uppercase tracking-wide">
            FRIO
          </span>
          <span className="font-semibold text-gray-800">{cold}</span>
        </div>
      </div>
    </div>
  );
}
