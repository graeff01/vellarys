'use client';

/**
 * DRAGGABLE GRID DASHBOARD
 * ========================
 *
 * Sistema de grid com drag-and-drop e resize inspirado no Monday.com.
 * Usa react-grid-layout para manipulação visual dos widgets.
 *
 * Features:
 * - Handles de resize grandes e visíveis nos 4 cantos
 * - Indicador de tamanho em tempo real durante resize
 * - Botões de tamanho rápido (preset sizes)
 * - Feedback visual completo
 */

import { useState, useCallback, useMemo } from 'react';
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
  Move,
  Expand,
  Square,
  RectangleHorizontal,
  RectangleVertical,
  Grid3X3,
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

// Presets de tamanho
const SIZE_PRESETS = [
  { label: 'P', w: 3, h: 2, icon: Square, title: 'Pequeno (3x2)' },
  { label: 'M', w: 6, h: 2, icon: RectangleHorizontal, title: 'Médio (6x2)' },
  { label: 'G', w: 6, h: 3, icon: RectangleVertical, title: 'Grande (6x3)' },
  { label: 'XG', w: 12, h: 3, icon: Maximize2, title: 'Extra Grande (12x3)' },
];

// =============================================
// CUSTOM RESIZE HANDLE
// =============================================

interface CustomResizeHandleProps {
  handleAxis: string;
}

function CustomResizeHandle({ handleAxis }: CustomResizeHandleProps) {
  // Posições baseadas no eixo
  const positions: Record<string, string> = {
    se: 'bottom-0 right-0 cursor-se-resize',
    sw: 'bottom-0 left-0 cursor-sw-resize',
    ne: 'top-0 right-0 cursor-ne-resize',
    nw: 'top-0 left-0 cursor-nw-resize',
    e: 'top-1/2 -translate-y-1/2 right-0 cursor-e-resize',
    w: 'top-1/2 -translate-y-1/2 left-0 cursor-w-resize',
    n: 'top-0 left-1/2 -translate-x-1/2 cursor-n-resize',
    s: 'bottom-0 left-1/2 -translate-x-1/2 cursor-s-resize',
  };

  const isCorner = ['se', 'sw', 'ne', 'nw'].includes(handleAxis);
  const isVertical = ['n', 's'].includes(handleAxis);

  return (
    <div
      className={`
        react-resizable-handle react-resizable-handle-${handleAxis}
        absolute z-50 transition-all duration-150
        ${positions[handleAxis]}
        ${isCorner
          ? 'w-5 h-5 hover:w-6 hover:h-6'
          : isVertical
            ? 'w-10 h-3 hover:h-4'
            : 'w-3 h-10 hover:w-4'}
      `}
    >
      {/* Visual Handle */}
      <div className={`
        absolute inset-0 flex items-center justify-center
        ${isCorner ? 'bg-indigo-500 rounded-full shadow-lg' : 'bg-indigo-400 rounded-full'}
        opacity-70 hover:opacity-100 hover:scale-110 transition-all
      `}>
        {isCorner && (
          <Expand className="w-3 h-3 text-white" />
        )}
      </div>
    </div>
  );
}

// =============================================
// WIDGET WRAPPER (com controles de edição avançados)
// =============================================

interface WidgetWrapperProps {
  widget: GridWidget;
  editMode: boolean;
  onRemove: () => void;
  onResize: (w: number, h: number) => void;
  children: React.ReactNode;
  isResizing: boolean;
}

function WidgetWrapper({ widget, editMode, onRemove, onResize, children, isResizing }: WidgetWrapperProps) {
  const [showSizeMenu, setShowSizeMenu] = useState(false);

  return (
    <div className={`
      h-full w-full relative group
      ${editMode ? 'cursor-move' : ''}
    `}>
      {/* Controles de Edição (visíveis no editMode) */}
      {editMode && (
        <>
          {/* Toolbar Superior */}
          <div className="absolute -top-1 left-0 right-0 h-10
                          opacity-0 group-hover:opacity-100 transition-all z-30
                          flex items-center justify-center pointer-events-none">
            <div className="flex items-center gap-1 px-2 py-1.5 bg-white/95 backdrop-blur-sm rounded-xl shadow-xl border border-slate-200 pointer-events-auto">
              {/* Handle de Drag */}
              <div className="flex items-center gap-1 px-2 py-1 cursor-grab active:cursor-grabbing rounded-lg hover:bg-slate-100 transition-colors">
                <Move className="w-4 h-4 text-slate-500" />
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider hidden sm:inline">Mover</span>
              </div>

              <div className="w-px h-5 bg-slate-200" />

              {/* Botão de Tamanhos Rápidos */}
              <div className="relative">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowSizeMenu(!showSizeMenu);
                  }}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-indigo-50 transition-colors text-indigo-600"
                >
                  <Grid3X3 className="w-4 h-4" />
                  <span className="text-[10px] font-bold uppercase tracking-wider hidden sm:inline">Tamanho</span>
                </button>

                {/* Menu de Tamanhos */}
                {showSizeMenu && (
                  <div className="absolute top-full left-0 mt-1 p-2 bg-white rounded-xl shadow-2xl border border-slate-200 min-w-[180px] z-50">
                    <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-2 px-2">Tamanhos Rápidos</p>
                    <div className="grid grid-cols-2 gap-1">
                      {SIZE_PRESETS.map((preset) => {
                        const Icon = preset.icon;
                        const isActive = widget.w === preset.w && widget.h === preset.h;
                        return (
                          <button
                            key={preset.label}
                            onClick={(e) => {
                              e.stopPropagation();
                              onResize(preset.w, preset.h);
                              setShowSizeMenu(false);
                            }}
                            className={`
                              flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-bold transition-all
                              ${isActive
                                ? 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                                : 'bg-slate-50 text-slate-600 hover:bg-indigo-50 hover:text-indigo-600'}
                            `}
                            title={preset.title}
                          >
                            <Icon className="w-4 h-4" />
                            <span>{preset.label}</span>
                          </button>
                        );
                      })}
                    </div>

                    {/* Tamanho Atual */}
                    <div className="mt-2 pt-2 border-t border-slate-100">
                      <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider px-2 mb-1">Atual</p>
                      <div className="flex items-center justify-center gap-2 px-2 py-1.5 bg-slate-100 rounded-lg">
                        <span className="text-sm font-mono font-bold text-slate-700">{widget.w}</span>
                        <span className="text-slate-400">x</span>
                        <span className="text-sm font-mono font-bold text-slate-700">{widget.h}</span>
                        <span className="text-[9px] text-slate-400">colunas</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="w-px h-5 bg-slate-200" />

              {/* Botão Remover */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove();
                }}
                className="flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-rose-50 transition-colors text-rose-500"
              >
                <X className="w-4 h-4" />
                <span className="text-[10px] font-bold uppercase tracking-wider hidden sm:inline">Remover</span>
              </button>
            </div>
          </div>

          {/* Indicador de Tamanho (sempre visível no hover ou durante resize) */}
          <div className={`
            absolute bottom-2 right-2 px-3 py-1.5 bg-slate-900/90 text-white
            text-xs font-mono font-bold rounded-lg z-20 flex items-center gap-2 transition-all
            ${isResizing ? 'opacity-100 scale-110 bg-indigo-600' : 'opacity-0 group-hover:opacity-100'}
          `}>
            <Expand className="w-3 h-3" />
            <span>{widget.w} x {widget.h}</span>
          </div>

          {/* Handles de Resize Visuais nos Cantos */}
          <div className="absolute -bottom-1 -right-1 w-6 h-6 opacity-0 group-hover:opacity-100 transition-all z-40">
            <div className="w-full h-full bg-indigo-500 rounded-full shadow-lg flex items-center justify-center cursor-se-resize hover:scale-125 transition-transform">
              <Expand className="w-3 h-3 text-white rotate-90" />
            </div>
          </div>
          <div className="absolute -bottom-1 -left-1 w-6 h-6 opacity-0 group-hover:opacity-100 transition-all z-40">
            <div className="w-full h-full bg-indigo-500 rounded-full shadow-lg flex items-center justify-center cursor-sw-resize hover:scale-125 transition-transform">
              <Expand className="w-3 h-3 text-white" />
            </div>
          </div>
          <div className="absolute -top-1 -right-1 w-6 h-6 opacity-0 group-hover:opacity-100 transition-all z-40">
            <div className="w-full h-full bg-indigo-500 rounded-full shadow-lg flex items-center justify-center cursor-ne-resize hover:scale-125 transition-transform">
              <Expand className="w-3 h-3 text-white -rotate-90" />
            </div>
          </div>
          <div className="absolute -top-1 -left-1 w-6 h-6 opacity-0 group-hover:opacity-100 transition-all z-40">
            <div className="w-full h-full bg-indigo-500 rounded-full shadow-lg flex items-center justify-center cursor-nw-resize hover:scale-125 transition-transform">
              <Expand className="w-3 h-3 text-white rotate-180" />
            </div>
          </div>

          {/* Handles de Resize nas Bordas */}
          <div className="absolute top-1/2 -translate-y-1/2 -right-1.5 w-4 h-12 opacity-0 group-hover:opacity-100 transition-all z-40">
            <div className="w-full h-full bg-indigo-400 rounded-full shadow-md cursor-e-resize hover:bg-indigo-500 hover:scale-110 transition-all" />
          </div>
          <div className="absolute top-1/2 -translate-y-1/2 -left-1.5 w-4 h-12 opacity-0 group-hover:opacity-100 transition-all z-40">
            <div className="w-full h-full bg-indigo-400 rounded-full shadow-md cursor-w-resize hover:bg-indigo-500 hover:scale-110 transition-all" />
          </div>
          <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-12 h-4 opacity-0 group-hover:opacity-100 transition-all z-40">
            <div className="w-full h-full bg-indigo-400 rounded-full shadow-md cursor-s-resize hover:bg-indigo-500 hover:scale-110 transition-all" />
          </div>
          <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-12 h-4 opacity-0 group-hover:opacity-100 transition-all z-40">
            <div className="w-full h-full bg-indigo-400 rounded-full shadow-md cursor-n-resize hover:bg-indigo-500 hover:scale-110 transition-all" />
          </div>

          {/* Borda de Edição */}
          <div className={`
            absolute inset-0 border-2 rounded-2xl pointer-events-none z-10 transition-all
            ${isResizing
              ? 'border-indigo-500 border-solid bg-indigo-50/20'
              : 'border-dashed border-indigo-300 opacity-0 group-hover:opacity-100'}
          `} />
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
      flex flex-wrap items-center gap-2 p-2 rounded-xl transition-all
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

          {/* Dica */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border border-indigo-100">
            <Move className="w-4 h-4 text-indigo-400" />
            <span className="text-xs text-indigo-600 font-medium">Arraste para mover</span>
            <span className="text-indigo-300">|</span>
            <Expand className="w-4 h-4 text-indigo-400" />
            <span className="text-xs text-indigo-600 font-medium">Cantos para redimensionar</span>
          </div>

          <div className="flex-1" />

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
// ESTILOS CUSTOMIZADOS PARA RESIZE HANDLES
// =============================================

const customStyles = `
  .react-grid-item > .react-resizable-handle {
    position: absolute;
    width: 20px;
    height: 20px;
    z-index: 100;
  }

  .react-grid-item > .react-resizable-handle::after {
    content: '';
    position: absolute;
    width: 12px;
    height: 12px;
    background: #6366f1;
    border-radius: 50%;
    opacity: 0;
    transition: all 0.2s;
  }

  .react-grid-item:hover > .react-resizable-handle::after {
    opacity: 0.8;
  }

  .react-grid-item > .react-resizable-handle:hover::after {
    transform: scale(1.2);
    opacity: 1;
  }

  .react-grid-item > .react-resizable-handle-se {
    bottom: -6px;
    right: -6px;
    cursor: se-resize;
  }
  .react-grid-item > .react-resizable-handle-se::after {
    bottom: 4px;
    right: 4px;
  }

  .react-grid-item > .react-resizable-handle-sw {
    bottom: -6px;
    left: -6px;
    cursor: sw-resize;
  }
  .react-grid-item > .react-resizable-handle-sw::after {
    bottom: 4px;
    left: 4px;
  }

  .react-grid-item > .react-resizable-handle-ne {
    top: -6px;
    right: -6px;
    cursor: ne-resize;
  }
  .react-grid-item > .react-resizable-handle-ne::after {
    top: 4px;
    right: 4px;
  }

  .react-grid-item > .react-resizable-handle-nw {
    top: -6px;
    left: -6px;
    cursor: nw-resize;
  }
  .react-grid-item > .react-resizable-handle-nw::after {
    top: 4px;
    left: 4px;
  }

  .react-grid-item > .react-resizable-handle-e {
    top: 50%;
    right: -6px;
    transform: translateY(-50%);
    width: 12px;
    height: 40px;
    cursor: e-resize;
  }
  .react-grid-item > .react-resizable-handle-e::after {
    width: 6px;
    height: 30px;
    border-radius: 3px;
    top: 5px;
    right: 3px;
  }

  .react-grid-item > .react-resizable-handle-w {
    top: 50%;
    left: -6px;
    transform: translateY(-50%);
    width: 12px;
    height: 40px;
    cursor: w-resize;
  }
  .react-grid-item > .react-resizable-handle-w::after {
    width: 6px;
    height: 30px;
    border-radius: 3px;
    top: 5px;
    left: 3px;
  }

  .react-grid-item > .react-resizable-handle-n {
    top: -6px;
    left: 50%;
    transform: translateX(-50%);
    width: 40px;
    height: 12px;
    cursor: n-resize;
  }
  .react-grid-item > .react-resizable-handle-n::after {
    width: 30px;
    height: 6px;
    border-radius: 3px;
    top: 3px;
    left: 5px;
  }

  .react-grid-item > .react-resizable-handle-s {
    bottom: -6px;
    left: 50%;
    transform: translateX(-50%);
    width: 40px;
    height: 12px;
    cursor: s-resize;
  }
  .react-grid-item > .react-resizable-handle-s::after {
    width: 30px;
    height: 6px;
    border-radius: 3px;
    bottom: 3px;
    left: 5px;
  }

  .react-grid-item.react-grid-placeholder {
    background: #6366f1 !important;
    opacity: 0.2 !important;
    border-radius: 1rem !important;
  }

  .react-grid-item.resizing {
    z-index: 100;
    opacity: 0.9;
  }

  .react-grid-item.react-draggable-dragging {
    z-index: 100;
    opacity: 0.9;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  }
`;

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
  const [resizingWidget, setResizingWidget] = useState<string | null>(null);

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

  // Handler para resize via preset
  const handlePresetResize = useCallback((widgetId: string, w: number, h: number) => {
    const updatedWidgets = widgets.map(widget => {
      if (widget.i === widgetId) {
        return { ...widget, w, h };
      }
      return widget;
    });
    onLayoutChange(updatedWidgets);
  }, [widgets, onLayoutChange]);

  // Handlers de resize
  const handleResizeStart = useCallback((layout: Layout[], oldItem: Layout) => {
    setResizingWidget(oldItem.i);
  }, []);

  const handleResizeStop = useCallback(() => {
    setResizingWidget(null);
  }, []);

  return (
    <div className="space-y-4">
      {/* Estilos customizados */}
      <style dangerouslySetInnerHTML={{ __html: customStyles }} />

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
        ${editMode ? 'bg-slate-50/50 rounded-2xl p-3 -m-3' : ''}
      `}>
        {/* Indicador de Grid (visível no editMode) */}
        {editMode && (
          <div
            className="absolute inset-0 pointer-events-none z-0 opacity-20 rounded-2xl overflow-hidden"
            style={{
              backgroundImage: `
                linear-gradient(to right, #94a3b8 1px, transparent 1px),
                linear-gradient(to bottom, #94a3b8 1px, transparent 1px)
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
          onResizeStart={handleResizeStart}
          onResizeStop={handleResizeStop}
          draggableHandle=".drag-handle"
          resizeHandles={['se', 'sw', 'ne', 'nw', 'e', 'w', 'n', 's']}
          useCSSTransforms={true}
        >
          {widgets.map(widget => (
            <div key={widget.i} className="drag-handle">
              <WidgetWrapper
                widget={widget}
                editMode={editMode}
                onRemove={() => onRemoveWidget(widget.i)}
                onResize={(w, h) => handlePresetResize(widget.i, w, h)}
                isResizing={resizingWidget === widget.i}
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
