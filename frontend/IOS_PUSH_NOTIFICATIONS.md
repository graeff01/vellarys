# Notificações Push no iOS - Guia Completo

## Requisitos para Notificações Push no iOS

### Versão do iOS
- **iOS 16.4+** é obrigatório
- Versões anteriores não suportam Web Push API

### Instalação como PWA
⚠️ **CRÍTICO**: Notificações push **só funcionam** quando o app está instalado na tela inicial do iPhone.

Safari no modo navegador normal **NÃO** suporta notificações push.

## Passo a Passo: Como Instalar o PWA no iPhone

### 1. Acesse o Site no Safari
- Abra o Safari (navegador padrão do iOS)
- Navegue até: `https://seu-dominio.com`

### 2. Instale na Tela Inicial
1. Toque no botão **Compartilhar** (ícone de quadrado com seta para cima)
2. Role para baixo e toque em **"Adicionar à Tela de Início"**
3. Confirme tocando em **"Adicionar"**

### 3. Abra o App Instalado
- Vá para a tela inicial do iPhone
- Toque no ícone do Vellarys (agora instalado como app)
- **NÃO** abra pelo Safari navegador!

### 4. Permita Notificações
Quando abrir o app instalado:
1. Será solicitada permissão para notificações
2. Toque em **"Permitir"**

## Como Testar se Está Funcionando

### Verificação no Console do Navegador
Abra o console (Safari > Desenvolver > Show JavaScript Console):

```javascript
// Verifica se está rodando como PWA
if (window.matchMedia('(display-mode: standalone)').matches) {
  console.log('✅ Rodando como PWA instalado');
} else {
  console.log('❌ Rodando no navegador Safari (NÃO vai funcionar)');
}

// Verifica permissão de notificações
console.log('Permissão:', Notification.permission);
// Deve mostrar "granted" se permitido
```

### Teste Manual de Notificação
Execute no console:

```javascript
// Testa notificação local
navigator.serviceWorker.ready.then(registration => {
  registration.showNotification('Teste iOS', {
    body: 'Se você viu isso, está funcionando! 🎉',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
  });
});
```

## Checklist de Troubleshooting

### ❌ Notificações não aparecem?

1. **Verifique se está instalado como PWA**
   ```javascript
   window.matchMedia('(display-mode: standalone)').matches
   // Deve retornar: true
   ```

2. **Verifique versão do iOS**
   - Ajustes > Geral > Sobre
   - iOS deve ser 16.4 ou superior

3. **Verifique permissões**
   - Ajustes > Vellarys > Notificações
   - Deve estar habilitado

4. **Verifique HTTPS**
   - Site deve estar em HTTPS (obrigatório)
   - `http://` não funciona para push

5. **Verifique Service Worker**
   ```javascript
   navigator.serviceWorker.getRegistration().then(reg => {
     console.log('SW registrado:', reg ? 'Sim' : 'Não');
   });
   ```

### ⚠️ Limitações Conhecidas do iOS

1. **Sem suporte a Actions**
   - Botões de ação na notificação não aparecem no iOS
   - Apenas clique na notificação principal funciona

2. **Vibração limitada**
   - Padrões de vibração podem ser ignorados

3. **Badge pode não aparecer**
   - Alguns ícones badge podem não renderizar corretamente

4. **Notificações silenciosas não funcionam**
   - Todas as notificações fazem som no iOS

## Arquitetura Técnica

### Arquivos Críticos

1. **`/public/sw.js`**
   - Service Worker com handlers de push
   - Versão atual: v1.2.0

2. **`/public/manifest.json`**
   - Configurações do PWA
   - Ícones específicos para iOS

3. **`/src/components/pwa/service-worker-registration.tsx`**
   - Lógica de registro do SW
   - Detecção de iOS e PWA

4. **`/src/components/pwa/ios-install-prompt.tsx`**
   - Banner educacional para instalação
   - Mostra instruções visuais

5. **`/src/app/layout.tsx`**
   - Meta tags iOS-specific
   - Links para ícones apple-touch-icon

### Meta Tags Críticas

```html
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="default" />
<meta name="apple-mobile-web-app-title" content="Vellarys" />
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />
```

## Testando Push Notifications

### Teste com Backend
Se o backend estiver configurado com VAPID keys:

```bash
# Backend deve ter endpoint para enviar push
POST /api/v1/notifications/send-push
{
  "user_id": 1,
  "title": "Novo Lead",
  "body": "João Silva entrou em contato",
  "url": "/dashboard/leads/123"
}
```

### Teste Manual (DevTools)
```javascript
// 1. Obter subscription
navigator.serviceWorker.ready.then(reg => {
  return reg.pushManager.getSubscription();
}).then(sub => {
  console.log('Subscription:', JSON.stringify(sub));
  // Copie o JSON e use ferramentas como web-push para enviar
});
```

## Monitoramento e Logs

### Logs Importantes
O sistema faz log de todos os eventos importantes:

- ✅ Service Worker registrado
- 🔔 Permissão solicitada
- 📩 Push recebido
- 👆 Notificação clicada
- 🪟 Janela focada/aberta

### Console do iPhone
Para ver logs no iPhone:
1. Mac: Safari > Desenvolver > [iPhone] > [Vellarys]
2. Ou use ferramentas remotas de debug

## FAQs

### Por que não funciona no Safari normal?
O iOS só suporta push em PWAs instalados. É uma limitação da Apple.

### Preciso publicar na App Store?
Não! PWA não precisa de App Store. É instalado diretamente do site.

### Funciona em modo privado?
Não. Service Workers não funcionam em modo privado/anônimo.

### Posso testar no Simulator?
Não. Push notifications não funcionam no Simulator. Precisa de dispositivo real.

### E se o usuário desinstalar o app?
A desinstalação remove o PWA e cancela a subscription automaticamente.

## Suporte e Debugging

### Habilitar Modo Desenvolvedor no iOS
1. Ajustes > Safari > Avançado
2. Ativar "Web Inspector"
3. Conectar iPhone ao Mac via USB
4. Safari Mac > Desenvolver > iPhone > Página

### Verificar Estado do Service Worker
```javascript
navigator.serviceWorker.getRegistrations().then(registrations => {
  console.log('Total de SWs:', registrations.length);
  registrations.forEach(reg => {
    console.log('Estado:', reg.active?.state);
    console.log('Scope:', reg.scope);
  });
});
```

## Referências Oficiais

- [Web Push API - Apple](https://webkit.org/blog/12945/meet-web-push/)
- [PWA iOS Support](https://developer.apple.com/documentation/webkit/delivering-web-content-to-ios-apps)
- [Service Workers - MDN](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)

---

**Última atualização:** 2026-02-03
**Versão do Service Worker:** v1.2.0
