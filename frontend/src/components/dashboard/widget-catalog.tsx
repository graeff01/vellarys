'use client';

/**
 * WIDGET CATALOG
 * ===============
 *
 * Modal visual para adicionar novos widgets ao dashboard.
 * Interface inspirada no Monday.com com preview e categorias.
 */

import { useState, useMemo } from 'react';
import {
  X,
  Search,
  Plus,
  Check,
  Sparkles,
} from 'lucide-react';
import {
  WIDGET_REGISTRY,
  CATEGORY_LABELS,
  CATEGORY_COLORS,
  CATEGORY_ORDER,
  getWidgetsByCategory,
  WidgetMeta,
  WidgetCategory,
} from './widget-registry';

// =============================================
// TIPOS
// =============================================

interface WidgetCatalogProps {
  isOpen: boolean;
  onClose: () => void;
  onAddWidget: (widgetId: string) => void;
  existingWidgetTypes: string[];
}

// =============================================
// WIDGET CARD
// =============================================

interface WidgetCardProps {
  widget: WidgetMeta;
  isAdded: boolean;
  onAdd: () => void;
}

function WidgetCard({ widget, isAdded, onAdd }: WidgetCardProps) {
  const Icon = widget.icon;
  const colors = CATEGORY_COLORS[widget.category];

  return (
    <div
      className={`
        relative group rounded-2xl border-2 overflow-hidden transition-all duration-200
        ${isAdded
          ? 'border-emerald-300 bg-emerald-50/50'
          : 'border-slate-200 bg-white hover:border-indigo-300 hover:shadow-lg hover:-translate-y-1'}
      `}
    >
      {/* Preview Background */}
      <div className={`h-24 ${widget.previewBg || 'bg-gradient-to-br from-slate-400 to-slate-600'} relative`}>
        {/* Icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          <Icon className="w-10 h-10 text-white/90" />
        </div>

        {/* Grid Pattern Overlay */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(to right, white 1px, transparent 1px),
              linear-gradient(to bottom, white 1px, transparent 1px)
            `,
            backgroundSize: '20px 20px',
          }}
        />

        {/* Badge Adicionado */}
        {isAdded && (
          <div className="absolute top-2 right-2 bg-emerald-500 text-white px-2 py-0.5 rounded-full text-[10px] font-bold flex items-center gap-1">
            <Check className="w-3 h-3" />
            Adicionado
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-3">
        {/* Category Badge */}
        <div className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider mb-2 ${colors.bg} ${colors.text}`}>
          {widget.category}
        </div>

        {/* Title */}
        <h3 className="font-bold text-slate-900 text-sm mb-1 line-clamp-1">
          {widget.name}
        </h3>

        {/* Description */}
        <p className="text-xs text-slate-500 line-clamp-2 mb-3">
          {widget.description}
        </p>

        {/* Size Info */}
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono text-slate-400">
            {widget.grid.w}x{widget.grid.h} cols
          </span>

          {/* Add Button */}
          <button
            onClick={onAdd}
            disabled={isAdded}
            className={`
              flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-all
              ${isAdded
                ? 'bg-emerald-100 text-emerald-600 cursor-not-allowed'
                : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg hover:shadow-xl'}
            `}
          >
            {isAdded ? (
              <>
                <Check className="w-3.5 h-3.5" />
                <span>Adicionado</span>
              </>
            ) : (
              <>
                <Plus className="w-3.5 h-3.5" />
                <span>Adicionar</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================
// COMPONENTE PRINCIPAL
// =============================================

export function WidgetCatalog({ isOpen, onClose, onAddWidget, existingWidgetTypes }: WidgetCatalogProps) {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<WidgetCategory | 'all'>('all');

  // Widgets por categoria
  const widgetsByCategory = useMemo(() => getWidgetsByCategory(), []);

  // Filtra widgets
  const filteredWidgets = useMemo(() => {
    let widgets = Object.values(WIDGET_REGISTRY);

    // Filtra por categoria
    if (selectedCategory !== 'all') {
      widgets = widgets.filter(w => w.category === selectedCategory);
    }

    // Filtra por busca
    if (search) {
      const searchLower = search.toLowerCase();
      widgets = widgets.filter(w =>
        w.name.toLowerCase().includes(searchLower) ||
        w.description.toLowerCase().includes(searchLower)
      );
    }

    return widgets;
  }, [search, selectedCategory]);

  // Conta widgets por categoria
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = { all: Object.keys(WIDGET_REGISTRY).length };
    Object.values(WIDGET_REGISTRY).forEach(w => {
      counts[w.category] = (counts[w.category] || 0) + 1;
    });
    return counts;
  }, []);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-indigo-50 to-purple-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-extrabold text-slate-900">Catálogo de Widgets</h2>
              <p className="text-sm text-slate-500">Escolha os widgets para seu dashboard</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center
                       hover:bg-slate-50 hover:border-slate-300 transition-all"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {/* Search & Filters */}
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar widgets..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-white border border-slate-200 rounded-xl
                         text-sm font-medium text-slate-900 placeholder:text-slate-400
                         focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300"
            />
          </div>

          {/* Category Tabs */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <button
              onClick={() => setSelectedCategory('all')}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold whitespace-nowrap transition-all
                ${selectedCategory === 'all'
                  ? 'bg-indigo-600 text-white shadow-lg'
                  : 'bg-white text-slate-600 border border-slate-200 hover:border-slate-300'}
              `}
            >
              Todos
              <span className={`px-1.5 py-0.5 rounded-md text-xs ${selectedCategory === 'all' ? 'bg-indigo-500' : 'bg-slate-100'}`}>
                {categoryCounts.all}
              </span>
            </button>

            {CATEGORY_ORDER.map(category => {
              const colors = CATEGORY_COLORS[category];
              const isSelected = selectedCategory === category;

              return (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  className={`
                    flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold whitespace-nowrap transition-all
                    ${isSelected
                      ? `${colors.bg} ${colors.text} border ${colors.border}`
                      : 'bg-white text-slate-600 border border-slate-200 hover:border-slate-300'}
                  `}
                >
                  {CATEGORY_LABELS[category]}
                  <span className={`px-1.5 py-0.5 rounded-md text-xs ${isSelected ? 'bg-white/50' : 'bg-slate-100'}`}>
                    {categoryCounts[category] || 0}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Widget Grid */}
        <div className="flex-1 overflow-y-auto p-6">
          {filteredWidgets.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Search className="w-12 h-12 text-slate-300 mb-4" />
              <h3 className="text-lg font-bold text-slate-700 mb-2">Nenhum widget encontrado</h3>
              <p className="text-sm text-slate-500">Tente buscar com outros termos</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredWidgets.map(widget => (
                <WidgetCard
                  key={widget.id}
                  widget={widget}
                  isAdded={existingWidgetTypes.includes(widget.id)}
                  onAdd={() => {
                    onAddWidget(widget.id);
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <p className="text-sm text-slate-500">
            <span className="font-bold text-slate-700">{existingWidgetTypes.length}</span> widgets no seu dashboard
          </p>
          <button
            onClick={onClose}
            className="px-6 py-2.5 bg-indigo-600 text-white rounded-xl font-bold text-sm
                       hover:bg-indigo-700 transition-colors shadow-lg"
          >
            Concluir
          </button>
        </div>
      </div>
    </div>
  );
}

export default WidgetCatalog;
