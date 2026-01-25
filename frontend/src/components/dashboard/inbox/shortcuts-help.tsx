/**
 * ShortcutsHelp - Ajuda de Atalhos de Teclado
 * ============================================
 *
 * Modal que exibe todos os atalhos disponíveis no CRM Inbox.
 * Acionado pela tecla "?".
 */

'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Keyboard } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ShortcutsHelpProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface ShortcutItem {
  keys: string[];
  description: string;
  category: string;
}

const shortcuts: ShortcutItem[] = [
  // Navegação
  {
    keys: ['Ctrl', 'K'],
    description: 'Buscar mensagens',
    category: 'Navegação'
  },
  {
    keys: ['Esc'],
    description: 'Fechar modal/popover',
    category: 'Navegação'
  },

  // Ações
  {
    keys: ['/'],
    description: 'Abrir templates de respostas',
    category: 'Ações'
  },
  {
    keys: ['Ctrl', 'A'],
    description: 'Arquivar lead atual',
    category: 'Ações'
  },
  {
    keys: ['Ctrl', 'Shift', 'N'],
    description: 'Adicionar nova anotação',
    category: 'Ações'
  },
  {
    keys: ['Enter'],
    description: 'Enviar mensagem',
    category: 'Ações'
  },
  {
    keys: ['Shift', 'Enter'],
    description: 'Nova linha na mensagem',
    category: 'Ações'
  },

  // Ajuda
  {
    keys: ['?'],
    description: 'Mostrar esta ajuda',
    category: 'Ajuda'
  }
];

// Agrupa atalhos por categoria
const groupedShortcuts = shortcuts.reduce((acc, shortcut) => {
  if (!acc[shortcut.category]) {
    acc[shortcut.category] = [];
  }
  acc[shortcut.category].push(shortcut);
  return acc;
}, {} as Record<string, ShortcutItem[]>);

export function ShortcutsHelp({ open, onOpenChange }: ShortcutsHelpProps) {
  // Detecta Mac
  const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;

  // Formata tecla para display
  const formatKey = (key: string): string => {
    if (!isMac) return key;

    // Substitui para símbolos Mac
    const macKeys: Record<string, string> = {
      'Ctrl': '⌘',
      'Shift': '⇧',
      'Alt': '⌥',
      'Enter': '↵'
    };

    return macKeys[key] || key;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Keyboard className="h-5 w-5" />
            Atalhos de Teclado
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          {Object.entries(groupedShortcuts).map(([category, items]) => (
            <div key={category}>
              <h3 className="text-sm font-semibold mb-3 text-muted-foreground">
                {category}
              </h3>

              <div className="space-y-2">
                {items.map((shortcut, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <span className="text-sm">{shortcut.description}</span>

                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key, keyIndex) => (
                        <div key={keyIndex} className="flex items-center gap-1">
                          <kbd
                            className={cn(
                              "px-2 py-1 text-xs font-semibold",
                              "bg-muted border border-border rounded",
                              "shadow-sm min-w-[28px] text-center"
                            )}
                          >
                            {formatKey(key)}
                          </kbd>
                          {keyIndex < shortcut.keys.length - 1 && (
                            <span className="text-muted-foreground">+</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-6 pt-4 border-t text-xs text-muted-foreground text-center">
          Pressione <kbd className="px-1.5 py-0.5 bg-muted rounded font-semibold">?</kbd> a qualquer momento para ver esta ajuda
        </div>
      </DialogContent>
    </Dialog>
  );
}
