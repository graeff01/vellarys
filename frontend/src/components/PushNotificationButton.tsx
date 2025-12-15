'use client';

import { useNotifications } from '@/hooks/use-notifications';
import { Bell, BellOff } from 'lucide-react';

export function PushNotificationButton() {
  const {
    supported,
    permission,
    loading,
    subscribed,
    requestPermission,
    subscribeToPush,
    unsubscribeFromPush,
  } = useNotifications();

  // Se não suporta notificações, não mostra o botão
  if (!supported) {
    return null;
  }

  const handleToggle = async () => {
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
    <button
      onClick={handleToggle}
      disabled={loading}
      className={`
        flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors
        ${
          subscribed
            ? 'bg-green-100 text-green-700 hover:bg-green-200'
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
      ) : (
        <>
          <BellOff className="w-5 h-5" />
          <span>Ativar Notificações</span>
        </>
      )}
    </button>
  );
}