'use client';

/**
 * DASHBOARD CUSTOMIZER
 * =====================
 *
 * Modal para personalizar o dashboard.
 * Permite ativar/desativar widgets e reorganizar.
 */

import { useState, useEffect } from 'react';
import {
  X,
  Settings,
  Check,
  RotateCcw,
  Save,
  GripVertical,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  WIDGET_REGISTRY,
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  getWidgetsByCategory,
  SIZE_LABELS,
  WidgetSize,
} from './widget-registry';
import { WidgetConfig, updateDashboardConfig, resetDashboardConfig } from '@/lib/api';

interface DashboardCustomizerProps {
  isOpen: boolean;
  onClose: () => void;
  widgets: WidgetConfig[];
  onSave: (widgets: WidgetConfig[]) => void;
}

export function DashboardCustomizer({ isOpen, onClose, widgets, onSave }: DashboardCustomizerProps) {
  const [localWidgets, setLocalWidgets] = useState<WidgetConfig[]>([]);
  const [saving, setSaving] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    alertas: true,
    metricas: true,
    vendas: true,
    sistema: true,
  });

  // Sincroniza com props quando abre
  useEffect(() => {
    if (isOpen) {
      setLocalWidgets([...widgets]);
    }
  }, [isOpen, widgets]);

  // Toggle widget enabled
  const toggleWidget = (widgetId: string) => {
    setLocalWidgets(prev =>
      prev.map(w =>
        w.id === widgetId ? { ...w, enabled: !w.enabled } : w
      )
    );
  };

  // Muda tamanho do widget
  const changeSize = (widgetId: string, newSize: WidgetSize) => {
    setLocalWidgets(prev =>
      prev.map(w =>
        w.id === widgetId ? { ...w, size: newSize } : w
      )
    );
  };

  // Move widget para cima
  const moveUp = (widgetId: string) => {
    setLocalWidgets(prev => {
      const index = prev.findIndex(w => w.id === widgetId);
      if (index <= 0) return prev;

      const newWidgets = [...prev];
      [newWidgets[index - 1], newWidgets[index]] = [newWidgets[index], newWidgets[index - 1]];

      // Atualiza positions
      return newWidgets.map((w, i) => ({ ...w, position: i }));
    });
  };

  // Move widget para baixo
  const moveDown = (widgetId: string) => {
    setLocalWidgets(prev => {
      const index = prev.findIndex(w => w.id === widgetId);
      if (index < 0 || index >= prev.length - 1) return prev;

      const newWidgets = [...prev];
      [newWidgets[index], newWidgets[index + 1]] = [newWidgets[index + 1], newWidgets[index]];

      // Atualiza positions
      return newWidgets.map((w, i) => ({ ...w, position: i }));
    });
  };

  // Salvar configuração
  const handleSave = async () => {
    try {
      setSaving(true);
      await updateDashboardConfig(localWidgets);
      onSave(localWidgets);
      onClose();
    } catch (err) {
      console.error('Erro salvando configuração:', err);
    } finally {
      setSaving(false);
    }
  };

  // Resetar para padrão
  const handleReset = async () => {
    if (!confirm('Restaurar dashboard para o padrão? Suas customizações serão perdidas.')) {
      return;
    }

    try {
      setSaving(true);
      const response = await resetDashboardConfig();
      setLocalWidgets(response.widgets);
      onSave(response.widgets);
    } catch (err) {
      console.error('Erro resetando:', err);
    } finally {
      setSaving(false);
    }
  };

  // Toggle categoria expandida
  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => ({
      ...prev,
      [category]: !prev[category],
    }));
  };

  // Agrupa widgets por categoria
  const widgetsByCategory = getWidgetsByCategory();

  // Verifica se widget está na lista local
  const getLocalWidget = (widgetId: string) => {
    return localWidgets.find(w => w.id === widgetId);
  };

  // Widgets ativos ordenados por posição
  const activeWidgets = localWidgets
    .filter(w => w.enabled)
    .sort((a, b) => a.position - b.position);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="absolute right-0 top-0 h-full w-full max-w-2xl bg-white shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center">
              <Settings className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <h2 className="text-lg font-extrabold text-slate-900">Personalizar Dashboard</h2>
              <p className="text-xs text-slate-500">Escolha os widgets e organize como preferir</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-200 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Widgets Ativos */}
          <div className="p-6 border-b border-slate-200 bg-slate-50/50">
            <h3 className="text-sm font-extrabold text-slate-700 uppercase tracking-wider mb-3 flex items-center gap-2">
              <GripVertical className="w-4 h-4" />
              Ordem de Exibição ({activeWidgets.length} ativos)
            </h3>

            {activeWidgets.length > 0 ? (
              <div className="space-y-2">
                {activeWidgets.map((widget, index) => {
                  const meta = WIDGET_REGISTRY[widget.type];
                  if (!meta) return null;

                  const Icon = meta.icon;

                  return (
                    <div
                      key={widget.id}
                      className="flex items-center gap-3 p-3 bg-white rounded-xl border border-slate-200 shadow-sm"
                    >
                      <div className="flex flex-col gap-0.5">
                        <button
                          onClick={() => moveUp(widget.id)}
                          disabled={index === 0}
                          className="p-0.5 hover:bg-slate-100 rounded disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          <ChevronUp className="w-4 h-4 text-slate-400" />
                        </button>
                        <button
                          onClick={() => moveDown(widget.id)}
                          disabled={index === activeWidgets.length - 1}
                          className="p-0.5 hover:bg-slate-100 rounded disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        </button>
                      </div>

                      <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center">
                        <Icon className="w-4 h-4 text-slate-600" />
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-bold text-slate-800 truncate">{meta.name}</p>
                        <p className="text-xs text-slate-400">{SIZE_LABELS[widget.size as WidgetSize]}</p>
                      </div>

                      <select
                        value={widget.size}
                        onChange={(e) => changeSize(widget.id, e.target.value as WidgetSize)}
                        className="text-xs border border-slate-200 rounded-lg px-2 py-1 bg-white"
                      >
                        {meta.allowedSizes.map(size => (
                          <option key={size} value={size}>{SIZE_LABELS[size]}</option>
                        ))}
                      </select>

                      <button
                        onClick={() => toggleWidget(widget.id)}
                        className="p-1.5 text-rose-500 hover:bg-rose-50 rounded-lg"
                        title="Remover"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-slate-500 text-center py-4">
                Nenhum widget ativo. Selecione abaixo.
              </p>
            )}
          </div>

          {/* Catálogo de Widgets */}
          <div className="p-6">
            <h3 className="text-sm font-extrabold text-slate-700 uppercase tracking-wider mb-4">
              Widgets Disponíveis
            </h3>

            <div className="space-y-4">
              {CATEGORY_ORDER.map(category => {
                const categoryWidgets = widgetsByCategory[category] || [];
                if (categoryWidgets.length === 0) return null;

                const isExpanded = expandedCategories[category];

                return (
                  <div key={category} className="border border-slate-200 rounded-xl overflow-hidden">
                    <button
                      onClick={() => toggleCategory(category)}
                      className="w-full px-4 py-3 bg-slate-50 flex items-center justify-between hover:bg-slate-100 transition-colors"
                    >
                      <span className="text-sm font-bold text-slate-700">
                        {CATEGORY_LABELS[category]}
                      </span>
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                      )}
                    </button>

                    {isExpanded && (
                      <div className="p-3 space-y-2">
                        {categoryWidgets.map(widgetMeta => {
                          const localWidget = getLocalWidget(widgetMeta.id);
                          const isEnabled = localWidget?.enabled ?? false;
                          const Icon = widgetMeta.icon;

                          return (
                            <div
                              key={widgetMeta.id}
                              className={`flex items-center gap-3 p-3 rounded-xl border transition-all cursor-pointer ${
                                isEnabled
                                  ? 'border-indigo-200 bg-indigo-50'
                                  : 'border-slate-100 bg-white hover:border-slate-200'
                              }`}
                              onClick={() => {
                                // Se não existe no local, adiciona
                                if (!localWidget) {
                                  setLocalWidgets(prev => [
                                    ...prev,
                                    {
                                      id: widgetMeta.id,
                                      type: widgetMeta.id,
                                      enabled: true,
                                      position: prev.length,
                                      size: widgetMeta.defaultSize,
                                    },
                                  ]);
                                } else {
                                  toggleWidget(widgetMeta.id);
                                }
                              }}
                            >
                              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                                isEnabled ? 'bg-indigo-100' : 'bg-slate-100'
                              }`}>
                                <Icon className={`w-5 h-5 ${isEnabled ? 'text-indigo-600' : 'text-slate-500'}`} />
                              </div>

                              <div className="flex-1 min-w-0">
                                <p className={`text-sm font-bold ${isEnabled ? 'text-indigo-900' : 'text-slate-800'}`}>
                                  {widgetMeta.name}
                                </p>
                                <p className="text-xs text-slate-500 truncate">{widgetMeta.description}</p>
                              </div>

                              <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                                isEnabled ? 'bg-indigo-600' : 'bg-slate-200'
                              }`}>
                                {isEnabled && <Check className="w-4 h-4 text-white" />}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <button
            onClick={handleReset}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-xl font-bold text-sm transition-colors disabled:opacity-50"
          >
            <RotateCcw className="w-4 h-4" />
            Restaurar Padrão
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-xl font-bold text-sm transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-6 py-2 bg-indigo-600 text-white rounded-xl font-bold text-sm hover:bg-indigo-700 transition-colors disabled:opacity-50 shadow-lg shadow-indigo-200"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
