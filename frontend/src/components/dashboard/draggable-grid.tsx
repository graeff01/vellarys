'use client';

/**
 * DRAGGABLE GRID DASHBOARD
 * ========================
 *
 * Sistema de grid com drag-and-drop e resize inspirado no Monday.com.
 * Usa react-grid-layout para manipulação visual dos widgets.
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import { Responsive, WidthProvider, Layout, Layouts } from 'react-grid-layout';
import {
  GripVertical,
  Maximize2,
  Minimize2,
  X,
  Plus,
  Lock,
  Unlock,
  Save,
  RotateCcw,
} from 'lucide-react';

// Importa os estilos do react-grid-layout
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

const ResponsiveGridLayout = WidthProvider(Responsive);

// =============================================
// TIPOS
// =============================================

export interface GridWidget {
  i: string;           // ID único
  type: string;        // Tipo do widget (sales_goal, metrics, etc)
  x: number;           // Posição X (coluna)
  y: number;           // Posição Y (linha)
  w: number;           // Largura em colunas
  h: number;           // Altura em rows
  minW?: number;       // Largura mínima
  maxW?: number;       // Largura máxima
  minH?: number;       // Altura mínima
  maxH?: number;       // Altura máxima
  static?: boolean;    // Widget fixo (não pode mover)
}

interface DraggableGridProps {
  widgets: GridWidget[];
  onLayoutChange: (widgets: GridWidget[]) => void;
  onRemoveWidget: (widgetId: string) => void;
  onAddWidget: () => void;
  renderWidget: (widget: GridWidget) => React.ReactNode;
  editMode: boolean;
  onToggleEditMode: () => void;
  onSave: () => void;
  onReset: () => void;
  hasChanges: boolean;
  saving: boolean;
}

// =============================================
// CONFIGURAÇÕES DO GRID
// =============================================

const GRID_CONFIG = {
  // Breakpoints (largura da tela)
  breakpoints: { lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 },

  // Colunas por breakpoint
  cols: { lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 },

  // Altura de cada row em pixels
  rowHeight: 80,

  // Margem entre widgets [horizontal, vertical]
  margin: [12, 12] as [number, number],

  // Padding do container
  containerPadding: [0, 0] as [number, number],

  // Previne colisão (widgets não sobrepõem)
  preventCollision: false,

  // Compacta widgets automaticamente
  compactType: 'vertical' as const,
};

// =============================================
// WIDGET WRAPPER (com controles de edição)
// =============================================

interface WidgetWrapperProps {
  widget: GridWidget;
  editMode: boolean;
  onRemove: () => void;
  children: React.ReactNode;
}

function WidgetWrapper({ widget, editMode, onRemove, children }: WidgetWrapperProps) {
  return (
    <div className={`
      h-full w-full relative group
      ${editMode ? 'cursor-move' : ''}
    `}>
      {/* Controles de Edição (visíveis no editMode) */}
      {editMode && (
        <>
          {/* Handle de Drag (topo) */}
          <div className="absolute -top-0 left-0 right-0 h-8 bg-gradient-to-b from-slate-900/10 to-transparent
                          opacity-0 group-hover:opacity-100 transition-opacity z-20
                          flex items-center justify-center cursor-grab active:cursor-grabbing">
            <div className="flex items-center gap-1 px-3 py-1 bg-white/90 backdrop-blur-sm rounded-full shadow-lg border border-slate-200">
              <GripVertical className="w-4 h-4 text-slate-400" />
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Arrastar</span>
            </div>
          </div>

          {/* Botão Remover */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            className="absolute -top-2 -right-2 w-6 h-6 bg-rose-500 text-white rounded-full
                       shadow-lg opacity-0 group-hover:opacity-100 transition-all z-30
                       hover:bg-rose-600 hover:scale-110 flex items-center justify-center"
          >
            <X className="w-3.5 h-3.5" />
          </button>

          {/* Indicador de Tamanho */}
          <div className="absolute bottom-1 right-1 px-2 py-0.5 bg-slate-900/70 text-white
                          text-[9px] font-mono rounded opacity-0 group-hover:opacity-100 transition-opacity z-20">
            {widget.w}x{widget.h}
          </div>

          {/* Borda de Edição */}
          <div className="absolute inset-0 border-2 border-dashed border-indigo-300 rounded-2xl
                          opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10" />
        </>
      )}

      {/* Conteúdo do Widget */}
      <div className="h-full w-full overflow-hidden rounded-2xl">
        {children}
      </div>
    </div>
  );
}

// =============================================
// TOOLBAR DE EDIÇÃO
// =============================================

interface EditToolbarProps {
  editMode: boolean;
  onToggle: () => void;
  onSave: () => void;
  onReset: () => void;
  onAddWidget: () => void;
  hasChanges: boolean;
  saving: boolean;
}

function EditToolbar({ editMode, onToggle, onSave, onReset, onAddWidget, hasChanges, saving }: EditToolbarProps) {
  return (
    <div className={`
      flex items-center gap-2 p-2 rounded-xl transition-all
      ${editMode
        ? 'bg-indigo-50 border border-indigo-200'
        : 'bg-slate-50 border border-slate-200'}
    `}>
      {/* Toggle Edição */}
      <button
        onClick={onToggle}
        className={`
          flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-sm transition-all
          ${editMode
            ? 'bg-indigo-600 text-white shadow-lg hover:bg-indigo-700'
            : 'bg-white text-slate-600 border border-slate-200 hover:border-slate-300 hover:bg-slate-50'}
        `}
      >
        {editMode ? (
          <>
            <Unlock className="w-4 h-4" />
            <span>Editando</span>
          </>
        ) : (
          <>
            <Lock className="w-4 h-4" />
            <span>Editar Layout</span>
          </>
        )}
      </button>

      {/* Controles de Edição (visíveis apenas no editMode) */}
      {editMode && (
        <>
          <div className="w-px h-6 bg-indigo-200" />

          {/* Adicionar Widget */}
          <button
            onClick={onAddWidget}
            className="flex items-center gap-2 px-3 py-2 bg-white text-indigo-600
                       border border-indigo-200 rounded-lg font-bold text-sm
                       hover:bg-indigo-50 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">Adicionar</span>
          </button>

          {/* Reset */}
          <button
            onClick={onReset}
            className="flex items-center gap-2 px-3 py-2 bg-white text-slate-600
                       border border-slate-200 rounded-lg font-bold text-sm
                       hover:bg-slate-50 transition-all"
          >
            <RotateCcw className="w-4 h-4" />
            <span className="hidden sm:inline">Resetar</span>
          </button>

          {/* Salvar */}
          <button
            onClick={onSave}
            disabled={!hasChanges || saving}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-sm transition-all
              ${hasChanges && !saving
                ? 'bg-emerald-600 text-white shadow-lg hover:bg-emerald-700'
                : 'bg-slate-100 text-slate-400 cursor-not-allowed'}
            `}
          >
            {saving ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Salvando...</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>Salvar</span>
              </>
            )}
          </button>
        </>
      )}

      {/* Indicador de mudanças não salvas */}
      {hasChanges && !editMode && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
          <span className="text-xs font-bold text-amber-700">Alterações não salvas</span>
        </div>
      )}
    </div>
  );
}

// =============================================
// COMPONENTE PRINCIPAL
// =============================================

export function DraggableGrid({
  widgets,
  onLayoutChange,
  onRemoveWidget,
  onAddWidget,
  renderWidget,
  editMode,
  onToggleEditMode,
  onSave,
  onReset,
  hasChanges,
  saving,
}: DraggableGridProps) {
  // Converte widgets para formato do react-grid-layout
  const layouts = useMemo(() => {
    const layout: Layout[] = widgets.map(w => ({
      i: w.i,
      x: w.x,
      y: w.y,
      w: w.w,
      h: w.h,
      minW: w.minW || 2,
      maxW: w.maxW || 12,
      minH: w.minH || 1,
      maxH: w.maxH || 6,
      static: w.static || false,
    }));

    return {
      lg: layout,
      md: layout,
      sm: layout,
      xs: layout,
      xxs: layout,
    };
  }, [widgets]);

  // Handler de mudança de layout
  const handleLayoutChange = useCallback((currentLayout: Layout[], allLayouts: Layouts) => {
    // Atualiza posições dos widgets baseado no layout atual
    const updatedWidgets = widgets.map(widget => {
      const layoutItem = currentLayout.find(l => l.i === widget.i);
      if (layoutItem) {
        return {
          ...widget,
          x: layoutItem.x,
          y: layoutItem.y,
          w: layoutItem.w,
          h: layoutItem.h,
        };
      }
      return widget;
    });

    onLayoutChange(updatedWidgets);
  }, [widgets, onLayoutChange]);

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <EditToolbar
        editMode={editMode}
        onToggle={onToggleEditMode}
        onSave={onSave}
        onReset={onReset}
        onAddWidget={onAddWidget}
        hasChanges={hasChanges}
        saving={saving}
      />

      {/* Grid de Widgets */}
      <div className={`
        relative transition-all duration-300
        ${editMode ? 'bg-slate-50/50 rounded-2xl p-2 -m-2' : ''}
      `}>
        {/* Indicador de Grid (visível no editMode) */}
        {editMode && (
          <div
            className="absolute inset-0 pointer-events-none z-0 opacity-30"
            style={{
              backgroundImage: `
                linear-gradient(to right, #e2e8f0 1px, transparent 1px),
                linear-gradient(to bottom, #e2e8f0 1px, transparent 1px)
              `,
              backgroundSize: `calc(100% / 12) ${GRID_CONFIG.rowHeight}px`,
            }}
          />
        )}

        <ResponsiveGridLayout
          className="layout"
          layouts={layouts}
          breakpoints={GRID_CONFIG.breakpoints}
          cols={GRID_CONFIG.cols}
          rowHeight={GRID_CONFIG.rowHeight}
          margin={GRID_CONFIG.margin}
          containerPadding={GRID_CONFIG.containerPadding}
          preventCollision={GRID_CONFIG.preventCollision}
          compactType={GRID_CONFIG.compactType}
          isDraggable={editMode}
          isResizable={editMode}
          onLayoutChange={handleLayoutChange}
          draggableHandle=".drag-handle"
          resizeHandles={['se', 'sw', 'ne', 'nw', 'e', 'w']}
          useCSSTransforms={true}
        >
          {widgets.map(widget => (
            <div key={widget.i} className="drag-handle">
              <WidgetWrapper
                widget={widget}
                editMode={editMode}
                onRemove={() => onRemoveWidget(widget.i)}
              >
                {renderWidget(widget)}
              </WidgetWrapper>
            </div>
          ))}
        </ResponsiveGridLayout>

        {/* Empty State */}
        {widgets.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
              <Plus className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-bold text-slate-700 mb-2">Dashboard Vazio</h3>
            <p className="text-sm text-slate-500 mb-4 max-w-sm">
              Clique em "Editar Layout" e depois em "Adicionar" para começar a personalizar seu dashboard
            </p>
            <button
              onClick={() => {
                onToggleEditMode();
                setTimeout(onAddWidget, 100);
              }}
              className="px-6 py-2 bg-indigo-600 text-white rounded-xl font-bold text-sm
                         hover:bg-indigo-700 transition-colors shadow-lg"
            >
              Começar a Personalizar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default DraggableGrid;
