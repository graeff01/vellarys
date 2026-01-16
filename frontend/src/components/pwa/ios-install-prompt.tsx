'use client';

import { useState, useEffect } from 'react';
import { X, Share, Smartphone, ArrowDown } from 'lucide-react';

interface IOSInstallPromptProps {
  onDismiss?: () => void;
  autoShow?: boolean;
}

export function IOSInstallPrompt({ onDismiss, autoShow = false }: IOSInstallPromptProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isDismissedPermanently, setIsDismissedPermanently] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Verifica se já foi dispensado permanentemente
    const dismissed = localStorage.getItem('ios-install-prompt-dismissed');
    if (dismissed === 'true') {
      setIsDismissedPermanently(true);
      return;
    }

    // Detecta iOS
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

    // Detecta se já está instalado como PWA
    const isPWA =
      ('standalone' in window.navigator && (window.navigator as any).standalone === true) ||
      window.matchMedia('(display-mode: standalone)').matches;

    // Mostra o prompt se for iOS, não for PWA e autoShow estiver ativado
    if (autoShow && isIOS && !isPWA) {
      // Espera 3 segundos antes de mostrar
      setTimeout(() => setIsVisible(true), 3000);
    }
  }, [autoShow]);

  const handleDismiss = () => {
    setIsVisible(false);
    onDismiss?.();
  };

  const handleDismissForever = () => {
    localStorage.setItem('ios-install-prompt-dismissed', 'true');
    setIsDismissedPermanently(true);
    setIsVisible(false);
    onDismiss?.();
  };

  if (isDismissedPermanently || !isVisible) {
    return null;
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gradient-to-t from-blue-600 to-blue-500 text-white p-4 shadow-2xl z-50 animate-slide-up">
      <button
        onClick={handleDismiss}
        className="absolute top-2 right-2 p-1 hover:bg-white/20 rounded-full transition-colors"
      >
        <X className="w-5 h-5" />
      </button>

      <div className="max-w-md mx-auto">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
            <Smartphone className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-bold text-lg">Instale o App Vellarys</h3>
            <p className="text-sm text-blue-100">Receba notificações instantâneas</p>
          </div>
        </div>

        <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 mb-3 space-y-2">
          <div className="flex items-start gap-2 text-sm">
            <ArrowDown className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <p>Toque no botão <Share className="w-4 h-4 inline mx-1" /> <strong>Compartilhar</strong> abaixo</p>
          </div>
          <div className="flex items-start gap-2 text-sm">
            <span className="font-bold">2.</span>
            <p>Selecione <strong>"Adicionar à Tela de Início"</strong></p>
          </div>
          <div className="flex items-start gap-2 text-sm">
            <span className="font-bold">3.</span>
            <p>Abra o app pelo ícone na tela inicial</p>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleDismissForever}
            className="flex-1 bg-white/20 hover:bg-white/30 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Não mostrar novamente
          </button>
          <button
            onClick={handleDismiss}
            className="flex-1 bg-white text-blue-600 hover:bg-blue-50 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Entendi
          </button>
        </div>
      </div>
    </div>
  );
}
