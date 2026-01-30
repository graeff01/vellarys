'use client';

import { Flame, Info } from 'lucide-react';

interface PhoenixEngineSettings {
  enabled: boolean;
  inactivity_days: number;
  max_attempts: number;
  interval_days: number;
  require_manager_approval: boolean;
  min_interest_score_for_hot: number;
  respect_business_hours: boolean;
  allowed_hours: {
    start: string;
    end: string;
  };
}

interface PhoenixEngineSettingsProps {
  settings: PhoenixEngineSettings;
  onChange: (settings: PhoenixEngineSettings) => void;
}

export default function PhoenixEngineSettingsComponent({
  settings,
  onChange,
}: PhoenixEngineSettingsProps) {
  const updateSettings = (updates: Partial<PhoenixEngineSettings>) => {
    onChange({ ...settings, ...updates });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <Flame className="w-6 h-6 text-orange-500" />
          <h3 className="text-xl font-bold text-gray-900">Phoenix Engine</h3>
        </div>
        <p className="text-sm text-gray-600">
          Sistema inteligente de reativação de leads inativos (45+ dias)
        </p>
      </div>

      {/* Info Box */}
      <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 flex items-start gap-3">
        <Info className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-orange-900">
          <p className="font-medium mb-1">Como funciona?</p>
          <ul className="space-y-1 list-disc list-inside">
            <li>Identifica leads inativos automaticamente</li>
            <li>IA analisa histórico e compara com estoque atual</li>
            <li>Gera mensagens ultra-personalizadas</li>
            <li>Calcula score de intenção de compra (0-100)</li>
            <li>Requer sua aprovação antes de notificar o vendedor</li>
          </ul>
        </div>
      </div>

      {/* Enable/Disable */}
      <div className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg">
        <div>
          <p className="font-medium text-gray-900">Ativar Phoenix Engine</p>
          <p className="text-sm text-gray-600">
            Reativação automática de leads inativos
          </p>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={settings.enabled}
            onChange={(e) => updateSettings({ enabled: e.target.checked })}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-orange-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange-600"></div>
        </label>
      </div>

      {settings.enabled && (
        <>
          {/* Configurações de Inatividade */}
          <div className="space-y-4 p-4 bg-white border border-gray-200 rounded-lg">
            <h4 className="font-medium text-gray-900">Critérios de Inatividade</h4>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Dias de inatividade para reativar
              </label>
              <input
                type="number"
                min={30}
                max={180}
                value={settings.inactivity_days}
                onChange={(e) =>
                  updateSettings({ inactivity_days: parseInt(e.target.value) })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Leads sem interação há mais de {settings.inactivity_days} dias serão contatados
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Máximo de tentativas
                </label>
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={settings.max_attempts}
                  onChange={(e) =>
                    updateSettings({ max_attempts: parseInt(e.target.value) })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Intervalo entre tentativas (dias)
                </label>
                <input
                  type="number"
                  min={7}
                  max={60}
                  value={settings.interval_days}
                  onChange={(e) =>
                    updateSettings({ interval_days: parseInt(e.target.value) })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
                />
              </div>
            </div>
          </div>

          {/* Configurações de Score */}
          <div className="space-y-4 p-4 bg-white border border-gray-200 rounded-lg">
            <h4 className="font-medium text-gray-900">Score de Interesse</h4>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Score mínimo para marcar como "Urgente"
              </label>
              <input
                type="range"
                min={0}
                max={100}
                value={settings.min_interest_score_for_hot}
                onChange={(e) =>
                  updateSettings({
                    min_interest_score_for_hot: parseInt(e.target.value),
                  })
                }
                className="w-full"
              />
              <div className="flex justify-between text-sm text-gray-600 mt-1">
                <span>0</span>
                <span className="font-medium text-orange-600">
                  {settings.min_interest_score_for_hot}%
                </span>
                <span>100</span>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Leads com score acima de {settings.min_interest_score_for_hot}% serão
                priorizados
              </p>
            </div>
          </div>

          {/* Aprovação */}
          <div className="space-y-4 p-4 bg-white border border-gray-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">Requer aprovação do gestor</p>
                <p className="text-sm text-gray-600">
                  Vendedor original só é notificado após sua aprovação
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.require_manager_approval}
                  onChange={(e) =>
                    updateSettings({ require_manager_approval: e.target.checked })
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-orange-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange-600"></div>
              </label>
            </div>
          </div>

          {/* Horário */}
          <div className="space-y-4 p-4 bg-white border border-gray-200 rounded-lg">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="font-medium text-gray-900">Respeitar horário comercial</p>
                <p className="text-sm text-gray-600">
                  Mensagens só serão enviadas no horário definido
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.respect_business_hours}
                  onChange={(e) =>
                    updateSettings({ respect_business_hours: e.target.checked })
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-orange-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange-600"></div>
              </label>
            </div>

            {settings.respect_business_hours && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Início
                  </label>
                  <input
                    type="time"
                    value={settings.allowed_hours.start}
                    onChange={(e) =>
                      updateSettings({
                        allowed_hours: {
                          ...settings.allowed_hours,
                          start: e.target.value,
                        },
                      })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Fim
                  </label>
                  <input
                    type="time"
                    value={settings.allowed_hours.end}
                    onChange={(e) =>
                      updateSettings({
                        allowed_hours: {
                          ...settings.allowed_hours,
                          end: e.target.value,
                        },
                      })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
                  />
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
