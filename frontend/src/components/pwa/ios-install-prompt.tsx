'use client';

import { useState, useEffect } from 'react';
import { X, Share, Plus, Smartphone } from 'lucide-react';

/**
 * Banner para guiar usuários do iOS a instalarem o PWA
 * Notificações push só funcionam no iOS quando o app está instalado na tela inicial
 */
export function IOSInstallPrompt() {
  const [show, setShow] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [isPWA, setIsPWA] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Detecta iOS
    const iOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

    // Detecta se já está instalado como PWA
    const installedPWA =
      ('standalone' in window.navigator && (window.navigator as any).standalone === true) ||
      window.matchMedia('(display-mode: standalone)').matches ||
      window.matchMedia('(display-mode: fullscreen)').matches;

    setIsIOS(iOS);
    setIsPWA(installedPWA);

    // Verifica se deve mostrar o prompt
    const shouldShow = localStorage.getItem('show_ios_install_prompt') === 'true';
    const dismissed = localStorage.getItem('ios_install_prompt_dismissed') === 'true';

    // Mostra apenas para iOS não instalado e não foi dispensado antes
    if (iOS && !installedPWA && shouldShow && !dismissed) {
      setShow(true);
    }
  }, []);

  function handleDismiss() {
    setShow(false);
    localStorage.setItem('ios_install_prompt_dismissed', 'true');
    localStorage.removeItem('show_ios_install_prompt');
  }

  // Não renderiza se não for iOS ou já estiver instalado
  if (!isIOS || isPWA || !show) {
    return null;
  }

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 max-w-md mx-auto animate-in slide-in-from-bottom duration-300">
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl shadow-2xl p-4 text-white">
        {/* Close Button */}
        <button
          onClick={handleDismiss}
          className="absolute top-2 right-2 p-1 rounded-full hover:bg-white/20 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Content */}
        <div className="flex items-start gap-3 mb-3">
          <div className="p-2 bg-white/20 rounded-lg">
            <Smartphone className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-lg mb-1">
              Instalar Vellarys
            </h3>
            <p className="text-sm text-blue-100">
              Para receber notificações push no iPhone, instale o app na tela inicial
            </p>
          </div>
        </div>

        {/* Instructions */}
        <div className="bg-white/10 rounded-lg p-3 space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-6 h-6 rounded-full bg-white/20 text-xs font-bold">
              1
            </div>
            <span>Toque no botão <strong>Compartilhar</strong></span>
            <Share className="w-4 h-4 ml-auto" />
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-6 h-6 rounded-full bg-white/20 text-xs font-bold">
              2
            </div>
            <span>Selecione <strong>Adicionar à Tela de Início</strong></span>
            <Plus className="w-4 h-4 ml-auto" />
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-6 h-6 rounded-full bg-white/20 text-xs font-bold">
              3
            </div>
            <span>Toque em <strong>Adicionar</strong></span>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-3 text-xs text-blue-100 text-center">
          Após instalar, você receberá notificações em tempo real 🔔
        </div>
      </div>
    </div>
  );
}
