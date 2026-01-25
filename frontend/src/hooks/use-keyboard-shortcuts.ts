/**
 * useKeyboardShortcuts - Hook para Atalhos de Teclado
 * ====================================================
 *
 * Gerencia atalhos globais do CRM Inbox.
 *
 * Atalhos disponíveis:
 * - Ctrl+K: Buscar mensagens
 * - /: Abrir templates
 * - Ctrl+A: Arquivar lead atual
 * - Ctrl+Shift+N: Nova nota
 * - ?: Mostrar ajuda de atalhos
 * - Esc: Fechar modais
 */

import { useEffect } from 'react';

export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  description: string;
  action: () => void;
  preventDefault?: boolean;
}

interface UseKeyboardShortcutsOptions {
  shortcuts: KeyboardShortcut[];
  enabled?: boolean;
}

export function useKeyboardShortcuts({ shortcuts, enabled = true }: UseKeyboardShortcutsOptions) {
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignora se estiver em input/textarea (exceto para atalhos específicos)
      const target = event.target as HTMLElement;
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA';

      for (const shortcut of shortcuts) {
        // Verifica se tecla corresponde
        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase();

        // Verifica modificadores
        const ctrlMatch = shortcut.ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey;
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey;
        const altMatch = shortcut.alt ? event.altKey : !event.altKey;

        if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
          // Se estiver em input e atalho NÃO for "/" ou "?", ignora
          if (isInput && !['/', '?', 'Escape'].includes(shortcut.key)) {
            continue;
          }

          // Previne comportamento padrão se configurado
          if (shortcut.preventDefault !== false) {
            event.preventDefault();
          }

          // Executa ação
          shortcut.action();

          console.log('[Shortcuts] Atalho executado:', shortcut.description);
          break;
        }
      }
    };

    // Adiciona listener
    window.addEventListener('keydown', handleKeyDown);

    // Cleanup
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [shortcuts, enabled]);
}

/**
 * Shortcut helper para criar configurações de atalhos
 */
export function createShortcut(
  key: string,
  description: string,
  action: () => void,
  modifiers?: { ctrl?: boolean; shift?: boolean; alt?: boolean }
): KeyboardShortcut {
  return {
    key,
    description,
    action,
    ctrl: modifiers?.ctrl,
    shift: modifiers?.shift,
    alt: modifiers?.alt,
    preventDefault: true
  };
}

/**
 * Formata atalho para exibição visual
 * Ex: "Ctrl+K" ou "Cmd+K" (Mac) ou "/"
 */
export function formatShortcut(shortcut: KeyboardShortcut): string {
  const parts: string[] = [];

  // Detecta Mac
  const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;

  if (shortcut.ctrl) {
    parts.push(isMac ? '⌘' : 'Ctrl');
  }

  if (shortcut.shift) {
    parts.push(isMac ? '⇧' : 'Shift');
  }

  if (shortcut.alt) {
    parts.push(isMac ? '⌥' : 'Alt');
  }

  // Tecla principal
  const keyDisplay = shortcut.key === ' ' ? 'Space' : shortcut.key.toUpperCase();
  parts.push(keyDisplay);

  return parts.join(isMac ? '' : '+');
}
