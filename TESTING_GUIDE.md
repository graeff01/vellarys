# 🧪 Guia de Testes - Upgrade CRM Inbox

## Visão Geral

Este guia contém os testes end-to-end para validar as 13 funcionalidades profissionais implementadas no CRM Inbox.

---

## 📋 Pré-requisitos

1. **Subir ambiente:**
```bash
docker compose up -d
```

2. **Verificar logs do backend:**
```bash
docker compose logs -f backend
```
Confirme que você vê: `✅ Database ready!` e as 7 novas migrations foram aplicadas.

3. **Acessar aplicação:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs

4. **Criar usuário vendedor:**
- Faça login como admin
- Crie um usuário com role `seller`
- Faça login com esse usuário

---

## ✅ Checklist de Testes

### 1. ✨ Atualizações em Tempo Real (SSE)

**Objetivo:** Validar que eventos em tempo real chegam ao frontend.

**Passos:**
1. Abra o inbox do vendedor em **dois navegadores diferentes** (ou uma aba normal + uma anônima)
2. Em ambos, faça login com o mesmo vendedor
3. Na **aba 1**, clique em um lead e assuma a conversa
4. Na **aba 2**, observe se o lead atualiza automaticamente para "Atendido pelo vendedor"
5. Na **aba 1**, envie uma mensagem
6. Na **aba 2**, observe se a mensagem aparece **instantaneamente sem refresh**

**Resultado esperado:**
- ✅ Mensagens aparecem em tempo real em todas as abas
- ✅ Status do lead atualiza automaticamente
- ✅ Console do navegador mostra: `SSE connected to lead X`

---

### 2. ✅ Status de Mensagens (✓✓)

**Objetivo:** Validar ícones de entrega/leitura estilo WhatsApp.

**Passos:**
1. Assuma uma conversa
2. Envie uma mensagem
3. Observe o status à direita da mensagem enviada:
   - Logo após enviar: **✓ (check simples)** = `sent`
   - Após 2-5 segundos: **✓✓ (check duplo cinza)** = `delivered`
   - Se o lead abrir: **✓✓ (check duplo azul)** = `read`

**Testar webhook Z-API:**
```bash
# Simular webhook de status (substituir IDs reais)
curl -X POST http://localhost:8000/seller/inbox/webhook/message-status \
  -H "Content-Type: application/json" \
  -d '{
    "whatsapp_message_id": "ABC123",
    "status": "read",
    "read_at": "2026-01-25T10:30:00Z"
  }'
```

**Resultado esperado:**
- ✅ Ícone muda de ✓ para ✓✓ automaticamente
- ✅ ✓✓ fica azul quando lido
- ✅ Webhook atualiza status no banco

---

### 3. 📝 Templates de Respostas Rápidas

**Objetivo:** Criar e usar templates com variáveis interpoladas.

**Passos:**
1. Na página do inbox, clique no ícone **😊 (Smile)** no campo de mensagem
2. Clique em **"+ Novo Template"** (se houver)
3. Crie um template:
   - **Nome:** "Boas-vindas"
   - **Atalho:** `/bv`
   - **Categoria:** "saudacao"
   - **Conteúdo:**
   ```
   Olá {{lead_name}}! 👋

   Meu nome é {{seller_name}} e vou te ajudar a encontrar o imóvel ideal.

   Vi que você tem interesse em {{lead_interest}}. Ótima escolha!
   ```
4. Salve o template
5. Em uma conversa, clique no ícone 😊 novamente
6. Selecione o template "Boas-vindas"
7. Observe que o texto aparece no input **já interpolado** com os dados reais do lead

**Resultado esperado:**
- ✅ Template é criado com sucesso
- ✅ Variáveis `{{lead_name}}`, `{{seller_name}}`, `{{lead_interest}}` são substituídas por valores reais
- ✅ Contador de uso (`usage_count`) incrementa ao usar o template

**Testar via API:**
```bash
# Listar templates
curl http://localhost:8000/seller/inbox/templates \
  -H "Authorization: Bearer SEU_TOKEN"

# Interpolar template
curl http://localhost:8000/seller/inbox/templates/1/use?lead_id=123 \
  -X POST \
  -H "Authorization: Bearer SEU_TOKEN"
```

---

### 4. 📌 Anotações Internas

**Objetivo:** Adicionar notas visíveis apenas para a equipe.

**Passos:**
1. Na conversa de um lead, clique no ícone **📝 (StickyNote)** no header
2. Um painel lateral deve abrir à direita
3. Clique em **"+ Nova Anotação"**
4. Escreva: `Cliente pediu desconto de 10%. Conversar com gerente.`
5. Clique em **"Salvar"**
6. A anotação aparece na lista com:
   - Avatar do autor
   - Nome do vendedor
   - Data/hora
   - Conteúdo em estilo "post-it amarelo"
7. Clique no ícone **🗑️ (Trash)** para excluir a anotação
8. Confirme que apenas o **autor da nota pode excluir**

**Resultado esperado:**
- ✅ Notas são salvas no banco
- ✅ Apenas o autor pode excluir
- ✅ Notas aparecem ordenadas por data decrescente

---

### 5. 📎 Suporte a Anexos

**Objetivo:** Enviar imagens, PDFs, áudios via WhatsApp.

**Passos:**
1. Na conversa, clique no ícone **📎 (Paperclip)**
2. Um modal de upload deve aparecer
3. Arraste um arquivo de **imagem** (PNG/JPG, até 10MB)
4. Observe o **preview da imagem**
5. Observe a **barra de progresso** durante o upload
6. Ao completar, a mensagem com anexo aparece no histórico
7. Teste também com:
   - PDF (ícone de documento)
   - Áudio (ícone de microfone)
   - Vídeo (ícone de vídeo)

**Validações de segurança:**
- ❌ Tentar enviar arquivo > 10MB (deve rejeitar)
- ❌ Tentar enviar tipo não suportado `.exe` (deve rejeitar)
- ✅ Apenas imagens, PDFs, áudios, vídeos são aceitos

**Resultado esperado:**
- ✅ Upload funciona com progresso visual
- ✅ Arquivo é salvo em `/app/storage` (ou S3, se configurado)
- ✅ Link é enviado via WhatsApp
- ✅ Campo `attachments` no banco é populado (JSONB)

**Verificar no banco:**
```sql
SELECT id, content, attachments FROM messages WHERE attachments IS NOT NULL LIMIT 5;
```

---

### 6. 📦 Arquivamento de Conversas

**Objetivo:** Arquivar leads concluídos/inativos.

**Passos:**
1. Na lista de leads, clique em um lead
2. No menu **⋮ (More Options)**, clique em **"Arquivar Lead"**
3. Um modal pede o **motivo**:
   - Selecione: `✅ Venda concluída`
   - Ou escreva: `Lead não respondeu há 30 dias`
4. Confirme
5. O lead **desaparece da lista principal**
6. Clique na aba **"Arquivados"**
7. O lead aparece com badge **📦 Arquivado**
8. Clique em **"Desarquivar"**
9. O lead volta para a lista principal

**Resultado esperado:**
- ✅ Lead é marcado com `archived_at`, `archived_by`, `archive_reason`
- ✅ Lead não aparece na lista principal (filtro: `WHERE archived_at IS NULL`)
- ✅ Desarquivar limpa os campos de arquivamento

**Verificar no banco:**
```sql
SELECT id, name, archived_at, archive_reason FROM leads WHERE archived_at IS NOT NULL;
```

---

### 7. 📊 Métricas de Performance/SLA

**Objetivo:** Visualizar tempo médio de resposta e SLA.

**Passos:**
1. No topo do inbox, clique em **"📊 Métricas"** (ou acesse `/seller/inbox/metrics`)
2. Observe os KPIs:
   - **Tempo Médio de Primeira Resposta:** `2min 34s`
   - **Taxa de Conversão:** `45%` (leads que viraram oportunidades)
   - **SLA Compliance:** `92%` (respostas em < 5min)
   - **Total de Conversas:** `128`
3. Filtre por período:
   - Última semana
   - Último mês
   - Custom (date picker)

**Resultado esperado:**
- ✅ Métricas são calculadas a partir dos campos:
  - `first_response_time_seconds`
  - `total_seller_messages`, `total_lead_messages`
  - `conversation_started_at`
- ✅ Gráficos mostram evolução ao longo do tempo
- ✅ Comparação com período anterior (`+12% vs. semana passada`)

---

### 8. 🏷️ UI para Tags

**Objetivo:** Adicionar/remover tags visualmente.

**Passos:**
1. Na conversa de um lead, observe as tags existentes (ex: `VIP`, `Urgente`)
2. Clique em **"+ Tag"**
3. Digite: `Desconto 10%`
4. Pressione **Enter**
5. A tag aparece como badge colorido
6. Clique no **✕** da tag para remover

**Resultado esperado:**
- ✅ Tags são salvas na tabela `lead_tags` (many-to-many)
- ✅ Cores são atribuídas automaticamente
- ✅ Tags aparecem na lista de leads como badges

---

### 9. ⌨️ Atalhos de Teclado

**Objetivo:** Navegar rapidamente com atalhos.

**Passos:**
1. Pressione **`?`** (interrogação)
2. Um modal de ajuda deve abrir mostrando todos os atalhos
3. Feche o modal (ESC)
4. Teste cada atalho:
   - **`Ctrl + K`** → Abre busca de mensagens
   - **`/`** → Abre popover de templates
   - **`Ctrl + A`** → Arquiva lead atual
   - **`Ctrl + Shift + N`** → Abre painel de notas
   - **`ESC`** → Fecha modais
   - **`?`** → Abre ajuda de atalhos

**Resultado esperado:**
- ✅ Hook `useKeyboardShortcuts` captura teclas globalmente
- ✅ Atalhos funcionam mesmo com input desfocado
- ✅ Modais abrem/fecham corretamente

---

### 10. 📜 Histórico de Transferências

**Objetivo:** Rastrear passagens de mão (IA → Seller → Manager).

**Passos:**
1. Assuma uma conversa (IA → Seller)
2. Na sidebar do lead, observe a seção **"Histórico de Transferências"**
3. Deve aparecer:
   ```
   🤖 IA → 👤 João Silva
   Iniciado por: João Silva
   Motivo: Assumiu atendimento
   25/01/2026 10:32
   ```
4. Devolva o lead para a IA (Seller → IA)
5. Observe novo registro no histórico

**Resultado esperado:**
- ✅ Tabela `handoff_history` registra cada transferência
- ✅ Campos: `from_attended_by`, `to_attended_by`, `reason`, `initiated_by_user_id`
- ✅ UI mostra timeline visual

**Verificar no banco:**
```sql
SELECT * FROM handoff_history WHERE lead_id = 123 ORDER BY created_at DESC;
```

---

### 11. 🔍 Busca de Mensagens

**Objetivo:** Busca full-text em todo o histórico de conversas.

**Passos:**
1. Pressione **`Ctrl + K`**
2. Modal de busca abre
3. Digite: `apartamento 3 quartos`
4. Observe os resultados:
   - Leads que mencionaram esses termos
   - Trecho da mensagem com **highlight** dos termos
   - Data da mensagem
5. Clique em um resultado
6. O modal fecha e a conversa desse lead abre automaticamente

**Resultado esperado:**
- ✅ Busca usa **full-text search** no PostgreSQL (índice GIN)
- ✅ Termos são destacados em amarelo
- ✅ Resultados ordenados por relevância

**Testar via API:**
```bash
curl "http://localhost:8000/seller/inbox/search?q=apartamento+3+quartos" \
  -H "Authorization: Bearer SEU_TOKEN"
```

---

### 12. ⏱️ Indicador "Digitando..."

**Objetivo:** Mostrar quando o lead está digitando.

**Passos:**
1. **Simulação manual (via webhook SSE):**
   - Abra console do navegador
   - Digite:
   ```javascript
   // Simular evento SSE de digitação
   const event = new CustomEvent('typing', {
     detail: { is_typing: true, user_name: 'João Silva' }
   });
   window.dispatchEvent(event);
   ```
2. Observe o **TypingIndicator** aparecer na conversa:
   ```
   ● ● ●  João Silva está digitando...
   ```
3. Após 3 segundos, o indicador deve **desaparecer automaticamente**

**Resultado esperado:**
- ✅ Animação de 3 pontos pulsando
- ✅ Auto-hide após timeout
- ✅ Recebe evento via SSE quando lead digita no WhatsApp

---

### 13. ♿ Acessibilidade

**Objetivo:** Garantir usabilidade para todos.

**Passos:**
1. **Navegação por teclado:**
   - Pressione **Tab** repetidamente
   - Foco visual deve percorrer: lista de leads → campo de busca → botões → mensagem
   - Pressione **Enter** no lead focado → abre conversa
   - Pressione **Shift + Tab** → volta foco

2. **Screen reader (se disponível):**
   - Ative VoiceOver (Mac: Cmd+F5) ou NVDA (Windows)
   - Navegue pela página
   - Verifique se todos os botões têm `aria-label`
   - Ex: `<button aria-label="Assumir conversa">Assumir</button>`

3. **Contraste de cores:**
   - Use DevTools → Lighthouse → Accessibility
   - Score deve ser **≥ 90**

**Resultado esperado:**
- ✅ Todos os elementos interativos são focáveis
- ✅ Labels descritivos em ícones
- ✅ Contraste WCAG AA (mínimo 4.5:1)

---

## 🎯 Fluxos End-to-End Críticos

### Fluxo 1: Tempo Real Completo
1. **Aba 1:** Vendedor A assume lead
2. **Aba 2:** Vendedor B vê atualização instantânea
3. **Aba 1:** Envia mensagem com template
4. **Aba 2:** Mensagem aparece em < 1s
5. **Webhook Z-API:** Atualiza status para ✓✓
6. **Ambas as abas:** Status atualiza sem refresh

### Fluxo 2: Atendimento Completo
1. Lead entra pelo WhatsApp (simulado via webhook)
2. IA qualifica → lead aparece no inbox do vendedor
3. Vendedor vê notificação push
4. Vendedor abre inbox, vê lead com badge `🔴 Nova mensagem`
5. Vendedor assume conversa
6. Usa template para saudar
7. Adiciona nota: `Cliente quer visitar sábado`
8. Envia PDF da planta do imóvel
9. Cria tag `Visita agendada`
10. Arquiva lead com motivo: `Venda concluída`
11. Métricas atualizam: +1 conversão

### Fluxo 3: Colaboração Multi-Vendedor
1. Vendedor A assume lead
2. Vendedor A adiciona nota: `Cliente pede desconto`
3. Manager vê nota no painel de supervisão
4. Manager transfere lead para Vendedor B (especialista em negociação)
5. Histórico de transferências registra: A → B, iniciado por Manager
6. Vendedor B vê lead com todas as notas e histórico
7. Vendedor B fecha negócio

---

## 🐛 Troubleshooting

### Problema: SSE não conecta
**Sintoma:** Console mostra `Failed to connect to SSE stream`

**Soluções:**
1. Verificar se backend está rodando: `curl http://localhost:8000/api/health`
2. Verificar logs: `docker compose logs -f backend | grep SSE`
3. Testar endpoint diretamente:
   ```bash
   curl -N http://localhost:8000/seller/inbox/leads/123/stream \
     -H "Authorization: Bearer TOKEN"
   ```

### Problema: Templates não interpolam
**Sintoma:** Variáveis `{{lead_name}}` aparecem literalmente

**Soluções:**
1. Verificar se `template_interpolation_service` está importando corretamente
2. Verificar logs: `docker compose logs backend | grep template`
3. Testar API:
   ```bash
   curl http://localhost:8000/seller/inbox/templates/1/use?lead_id=123 -X POST
   ```

### Problema: Upload falha
**Sintoma:** `413 Payload Too Large` ou `500 Internal Server Error`

**Soluções:**
1. Verificar tamanho do arquivo (max 10MB)
2. Verificar tipo MIME (apenas imagens, PDFs, áudios, vídeos)
3. Verificar permissões: `ls -la backend/storage`
4. Verificar variável de ambiente: `STORAGE_LOCAL_PATH=/app/storage`

---

## 📈 Métricas de Sucesso

Após os testes, valide:

- ✅ **100% das mensagens** chegam em tempo real (< 1s)
- ✅ **Status ✓✓** atualiza em 100% das mensagens enviadas
- ✅ **Templates interpolam** corretamente (0 erros)
- ✅ **Upload de anexos** funciona para todos os tipos suportados
- ✅ **Busca retorna resultados** em < 500ms
- ✅ **Métricas são calculadas** sem erros
- ✅ **Atalhos funcionam** 100% das vezes
- ✅ **Acessibilidade score** ≥ 90 no Lighthouse

---

## 🚀 Próximos Passos

1. **Performance:** Adicionar cache Redis para templates
2. **Segurança:** Rate limiting em uploads (max 5 por minuto)
3. **Analytics:** Integrar com Google Analytics para rastrear uso de templates
4. **Webhooks:** Configurar Z-API para enviar webhooks reais de status
5. **Notificações:** Push notifications quando lead envia mensagem

---

**Documentação gerada automaticamente pelo sistema Velaris**
**Última atualização:** 2026-01-25
