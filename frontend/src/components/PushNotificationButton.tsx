'use client';

import { useNotifications } from '@/hooks/use-notifications';
import { Bell, BellOff, Smartphone, Share } from 'lucide-react';
import { useState } from 'react';

export function PushNotificationButton() {
  const {
    supported,
    permission,
    loading,
    subscribed,
    isIOS,
    isPWA,
    needsPWAInstall,
    requestPermission,
    subscribeToPush,
    unsubscribeFromPush,
  } = useNotifications();

  const [showIOSInstructions, setShowIOSInstructions] = useState(false);

  // Se não suporta notificações, não mostra o botão
  if (!supported) {
    return null;
  }

  const handleToggle = async () => {
    // Se é iOS e não está instalado como PWA, mostra instruções
    if (needsPWAInstall) {
      setShowIOSInstructions(true);
      return;
    }

    if (subscribed) {
      // Desativar
      const success = await unsubscribeFromPush();
      if (success) {
        alert('✅ Notificações desativadas');
      } else {
        alert('❌ Erro ao desativar notificações');
      }
    } else {
      // Ativar
      const success = await subscribeToPush();
      if (success) {
        alert('✅ Notificações ativadas! Você receberá notificações mesmo com o app fechado.');
      } else {
        if (permission === 'denied') {
          alert('❌ Você bloqueou as notificações. Ative nas configurações do navegador.');
        } else {
          alert('❌ Erro ao ativar notificações');
        }
      }
    }
  };

  return (
    <>
      <button
        onClick={handleToggle}
        disabled={loading}
        className={`
          flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors
          ${
            subscribed
              ? 'bg-green-100 text-green-700 hover:bg-green-200'
              : needsPWAInstall
              ? 'bg-orange-600 text-white hover:bg-orange-700'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }
          ${loading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        {loading ? (
          <>
            <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
            <span>Processando...</span>
          </>
        ) : subscribed ? (
          <>
            <Bell className="w-5 h-5" />
            <span>Notificações Ativadas</span>
          </>
        ) : needsPWAInstall ? (
          <>
            <Smartphone className="w-5 h-5" />
            <span>Instalar App (iOS)</span>
          </>
        ) : (
          <>
            <BellOff className="w-5 h-5" />
            <span>Ativar Notificações</span>
          </>
        )}
      </button>

      {/* Modal de instruções iOS */}
      {showIOSInstructions && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <Smartphone className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h3 className="font-bold text-lg text-gray-900">Instalar no iPhone</h3>
                <p className="text-sm text-gray-500">Para receber notificações</p>
              </div>
            </div>

            <div className="space-y-4 mb-6">
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                  1
                </div>
                <div>
                  <p className="font-medium text-gray-900">Toque no botão Compartilhar</p>
                  <div className="flex items-center gap-2 mt-1 text-sm text-gray-600">
                    <Share className="w-4 h-4" />
                    <span>No menu inferior do Safari</span>
                  </div>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                  2
                </div>
                <div>
                  <p className="font-medium text-gray-900">Adicionar à Tela de Início</p>
                  <p className="text-sm text-gray-600 mt-1">Role para baixo e toque nesta opção</p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                  3
                </div>
                <div>
                  <p className="font-medium text-gray-900">Abra o app instalado</p>
                  <p className="text-sm text-gray-600 mt-1">Use o ícone na tela inicial (não o Safari)</p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-green-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                  4
                </div>
                <div>
                  <p className="font-medium text-gray-900">Ative as notificações</p>
                  <p className="text-sm text-gray-600 mt-1">Volte aqui e clique no botão novamente</p>
                </div>
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
              <p className="text-xs text-blue-800">
                <strong>Nota:</strong> O iOS requer iOS 16.4+ para notificações push funcionarem.
              </p>
            </div>

            <button
              onClick={() => setShowIOSInstructions(false)}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              Entendi
            </button>
          </div>
        </div>
      )}
    </>
  );
}