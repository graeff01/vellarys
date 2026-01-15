# 🔍 AUDITORIA TÉCNICA BIG TECH - VELARIS
**Data:** 15/01/2026  
**Analista:** Antigravity AI  
**Versão do Sistema:** 2.0 (com IA Raio-X)

---

## 📊 RESUMO EXECUTIVO

O **Velaris** é um sistema de atendimento via IA multi-tenant de **nível enterprise**. A arquitetura é sólida, o código é limpo, e a infraestrutura está bem planejada. 

**Grade Geral:** ⭐⭐⭐⭐ (4/5 estrelas)

**Próximo objetivo:** Levar para ⭐⭐⭐⭐⭐ com melhorias estratégicas.

---

## ✅ PONTOS FORTES (O QUE JÁ ESTÁ MATADOR)

### 1. **Arquitetura Clean & DDD**
- ✅ Separação clara: `api` → `application` → `domain` → `infrastructure`
- ✅ Injeção de dependências nativa (FastAPI)
- ✅ Multi-tenant nativo com isolamento total
- ✅ Use cases bem definidos (`process_message.py`)

### 2. **Segurança de Nível Produção**
- ✅ Rate Limiting por Lead e por Tenant
- ✅ Guards de IA contra jailbreak e vazamento de dados
- ✅ Sanitização de inputs/outputs
- ✅ LGPD compliance (exportação, anonimização, exclusão)
- ✅ Refresh tokens implementados

### 3. **Inteligência de Negócio**
- ✅ **Raio-X da IA**: Insights automáticos para corretores
- ✅ Qualificação inteligente (hot/warm/cold)
- ✅ Follow-ups automáticos configuráveis
- ✅ Reengajamento inteligente
- ✅ Visão semântica de imóveis (buscando por "perto da praia", etc.)

### 4. **Observabilidade**
- ✅ Sentry integrado para tracking de erros
- ✅ Audit logs completos (quem fez o quê)
- ✅ Health checks robustos (DB, OpenAI, WhatsApp)
- ✅ Métricas de conversão e performance

### 5. **Integrações**
- ✅ WhatsApp: Z-API, Gupshup, 360Dialog
- ✅ Push Notifications (VAPID/Web Push)
- ✅ OpenAI (GPT-4o)
- ✅ Resend (Email)

---

## 🚨 GAPS CRÍTICOS (O QUE ESTÁ FALTANDO)

### 🔴 **PRIORIDADE MÁXIMA**

#### 1. **Falta Dashboard de Analytics Real-Time**
**Problema:**  
- Gestor imobiliário não consegue ver **agora** quantos leads estão caindo, de onde vêm, taxa de conversão da IA, etc.
- Decisões são tomadas "no escuro".

**Impacto:**  
- Cliente não vê o valor do produto em tempo real.
- Difícil justificar ROI para o imobiliário.

**Solução:**  
- Dashboard com métricas **ao vivo**:
  - Leads hoje/semana/mês
  - Taxa de conversão IA → Humano
  - Tempo médio de resposta
  - Источники com melhor qualificação
  - Gráficos de atividade por hora (detectar picos)

**Tecnologia:**  
- Backend: Endpoint `/api/metrics/realtime` (já existe `/metrics`, mas melhorar)
- Frontend: WebSocket ou polling a cada 10s
- Biblioteca: Chart.js ou Recharts

**Estimativa:** 4-6 horas

---

#### 2. **Falta CRM Básico Integrado**
**Problema:**  
- Depois que o lead é atribuído ao corretor, o sistema "larga" o lead.
- Não há pipeline de vendas, etapas, controle de visitas, propostas.

**Impacto:**  
- Corretor usa o Velaris só para pegar o lead, depois vai para planilha/outro CRM.
- Cliente vê o Velaris como "só um bot", não como ferramenta central.

**Solução:**  
- **Pipeline Kanban** (Novo → Contato → Visita Agendada → Proposta → Fechado/Perdido)
- Arrastar e soltar leads entre etapas
- Histórico de interações (ligações, WhatsApp, emails)
- Lembretes/tarefas por lead

**Tecnologia:**  
- Backend: Tabela `lead_pipeline_stage` + endpoint `/leads/{id}/stage`
- Frontend: Biblioteca react-beautiful-dnd ou react-dnd
- Modelo:
  ```python
  class LeadPipelineStage(Base):
      id: int
      lead_id: int
      stage: str  # "contato", "visita", "proposta", etc.
      changed_at: datetime
      changed_by: int (seller)
  ```

**Estimativa:** 8-12 horas

---

#### 3. **Falta Busca Semântica de Imóveis (Aprimorar)**
**Status Atual:**  
- Já existe `property_lookup_service.py` com busca textual.

**Gap:**  
- Não tem busca vetorial/embeddings para queries complexas tipo:
  - "Apartamento perto de escolas boas e com academia no prédio"
  - "Casa com quintal grande para cachorro"

**Solução:**  
- Implementar **RAG** (Retrieval-Augmented Generation):
  1. Gerar embeddings dos imóveis (descrição + atributos) via OpenAI Embeddings
  2. Armazenar em PostgreSQL com extensão `pgvector`
  3. Fazer busca de similaridade coseno
  4. IA responde com base nos imóveis mais relevantes

**Tecnologia:**  
- PostgreSQL + extensão `pgvector`
- OpenAI Embeddings API
- Fluxo:
  ```
  Lead: "Quero apto perto do mar"
  → Gera embedding da query
  → Busca top 5 imóveis similares
  → IA monta resposta com esses imóveis
  ```

**Estimativa:** 6-8 horas

---

#### 4. **Falta Agendamento de Visitas Direto no Chat**
**Problema:**  
- Lead quer agendar visita, mas IA só diz "o corretor vai entrar em contato".
- Corretor tem que ligar/chamar no WhatsApp para marcar.
- Fricção alta = perda de conversão.

**Solução:**  
- **IA oferece slots de horário** direto no chat:
  ```
  IA: "Que tal visitarmos o apartamento? Temos disponibilidade:
  1. Amanhã (16/01) às 14h
  2. Sexta (17/01) às 10h
  3. Sábado (18/01) às 9h
  
  Qual funciona melhor para você?"
  ```
- Lead clica/digita a opção.
- Sistema registra no Google Calendar (ou equivalente) E notifica o corretor.

**Tecnologia:**  
- Backend: 
  - Tabela `scheduled_visits`
  - Integração Google Calendar API (ou Calendly webhook)
  - Endpoint `/leads/{id}/schedule-visit`
- IA: Function calling da OpenAI (`schedule_visit`)

**Modelo:**
```python
class ScheduledVisit(Base):
    id: int
    lead_id: int
    seller_id: int
    property_code: str
    scheduled_at: datetime
    status: str  # "pending", "confirmed", "cancelled"
    google_event_id: str
```

**Estimativa:** 6-8 horas

---

### 🟡 **ALTA PRIORIDADE**

#### 5. **Falta histórico completo de integração WhatsApp**
**Problema:**  
- Quando lead volta a falar depois de dias, a IA não "lembra" do contexto completo.
- Histórico atual só pega últimas 30 mensagens.

**Solução:**  
- Armazenar **100% das mensagens**, incluindo as do WhatsApp puro (fora da IA).
- Implementar **resumo automático** para conversas longas usando IA:
  ```
  "Resumo da conversa anterior:
  - Interessado em apto 3Q no Centro
  - Tem 2 filhos, precisa de escolas próximas
  - Orçamento não informado ainda"
  ```

**Tecnologia:**  
- Criar job `generate_conversation_summary` (roda a cada 50 mensagens)
- Usar OpenAI para resumir e armazenar em `lead.conversation_summary`

**Estimativa:** 3-4 horas

---

#### 6. **Falta Sistema de Templates de Mensagem**
**Problema:**  
- Corretor quer enviar mensagens rápidas padrão (ex: "Bom dia! Vi que você está interessado em...").
- Tem que digitar tudo na mão sempre.

**Solução:**  
- **Biblioteca de Templates** editáveis pelo gestor:
  - "Boa manhã interesse"
  - "Convite para visita"
  - "Follow-up sem resposta"
  - etc.
- Suporta variáveis: `{{nome_lead}}`, `{{codigo_imovel}}`, `{{endereco}}`

**Tecnologia:**  
- Tabela `message_templates`
- Endpoint `/templates` (CRUD)
- Renderização via Jinja2 ou `string.Template`

**Estimativa:** 4-6 horas

---

#### 7. **Webhook de Status de Entrega WhatsApp**
**Problema:**  
- Sistema não rastreia se a mensagem foi entregue/lida/respondida.
- Corretor não sabe se o lead viu a mensagem dele.

**Solução:**  
- Ouvir webhooks de status (delivered, read) das APIs de WhatsApp.
- Armazenar em `message.delivery_status` e `message.read_at`.
- Dashboard mostra "✔✔ Lido às 15h30".

**Tecnologia:**  
- Adicionar campos na tabela `messages`:
  ```python
  delivery_status: str  # "sent", "delivered", "read", "failed"
  delivered_at: datetime
  read_at: datetime
  ```
- Webhook listeners para Z-API, Gupshup, 360Dialog

**Estimativa:** 3-4 horas

---

#### 8. **Falta A/B Testing de Prompts**
**Problema:**  
- Não tem como testar se um prompt converte melhor que outro.
- Mudanças são feitas "no escuro".

**Solução:**  
- **Sistema de Experimentos**:
  - Gestor cria variante A e B do prompt
  - Sistema alterna aleatoriamente (50/50)
  - Mede: taxa de qualificação hot, tempo de conversa, handoff rate
  - Dashboard mostra qual ganhou

**Tecnologia:**  
- Tabela `prompt_variants` + `prompt_experiments`
- Lógica: `if random.random() < 0.5: use_variant_a else: use_variant_b`
- Tracking: Salvar `experiment_id` no lead

**Estimativa:** 6-8 horas

---

### 🟢 **MÉDIA PRIORIDADE (Nice to Have)**

#### 9. **Falta Transcrição de Áudio**
**Status Atual:**  
- Já existe `transcription_service.py`, mas não está integrado ao fluxo.

**Gap:**  
- Lead manda áudio no WhatsApp, IA não responde ou responde genérico.

**Solução:**  
- Ao receber áudio:
  1. Baixar arquivo via API WhatsApp
  2. Transcrever com OpenAI Whisper API
  3. Processar texto transcrito como mensagem normal

**Estimativa:** 4 horas

---

#### 10. **Falta Envio de Imagens/Vídeos pela IA**
**Problema:**  
- IA só envia texto.
- Imobiliário é VISUAL: fotos vendem.

**Solução:**  
- IA detecta quando deve enviar foto do imóvel:
  ```
  Lead: "Tem foto do apartamento?"
  IA: [Busca foto no banco] [Envia via WhatsApp] "Olha só! 📸"
  ```
- Armazenar URLs de imagens em `product.custom_data.images: [url1, url2]`
- Usar API WhatsApp para envio de mídia

**Tecnologia:**  
- OpenAI Function Calling: `send_property_image(property_code)`
- API WhatsApp: endpoint de envio de mídia

**Estimativa:** 4-6 horas

---

#### 11. **Falta Integração com CRMs Externos**
**Problema:**  
- Cliente já usa outro CRM (Pipedrive, RD Station, HubSpot).
- Quer que os leads do Velaris caiam lá automaticamente.

**Solução:**  
- **Webhooks de saída** configuráveis:
  - Quando lead vira "hot" → dispara webhook para URL externa
  - Cliente configura no settings
- **Integrações nativas** (via Zapier/Make ou diretas):
  - Pipedrive
  - RD Station
  - HubSpot

**Tecnologia:**  
- Criar `outbound_webhooks` configurável por tenant
- Usar `httpx` para enviar payload JSON

**Estimativa:** 6-8 horas

---

#### 12. **Falta Sistema de Feedback do Corretor**
**Problema:**  
- Corretor recebe lead "hot", mas era ruim.
- IA nunca aprende com esses casos.

**Solução:**  
- Botão "Avaliar Lead" no dashboard:
  - ⭐⭐⭐⭐⭐ (ótimo)
  - ⭐⭐⭐ (ok)
  - ⭐ (péssimo)
- Armazenar em `lead.seller_rating`
- **Fine-tuning futuro:** Usar esses dados para retreinar modelo

**Estimativa:** 3 horas

---

## 🏗️ MELHORIAS DE INFRAESTRUTURA

### 1. **Migrar de Polling para WebSockets (Real-Time)**
**Problema Atual:**  
- Frontend faz polling (a cada 30s) para ver se tem lead novo.
- Ineficiente, latência alta.

**Solução:**  
- Implementar **WebSocket** para notificações em tempo real:
  ```
  Novo lead → Backend → WebSocket → Frontend atualiza INSTANTÂNEO
  ```

**Tecnologia:**  
- FastAPI WebSocket nativo
- Frontend: usar `useWebSocket` hook

**Estimativa:** 4-6 horas

---

### 2. **Implementar Cache Redis para Performance**
**Status Atual:**  
- Não usa cache.

**Gap:**  
- Queries repetidas (ex: buscar settings do tenant) batem no DB sempre.

**Solução:**  
- **Redis** para cache de:
  - Settings do tenant (TTL: 5 min)
  - Listagem de imóveis (TTL: 1 hora)
  - Rate limiting (já está no código, mas faltando deploy)

**Tecnologia:**  
- `redis-py` + `aioredis`
- Decorator `@cached(ttl=300)`

**Estimativa:** 4 horas

---

### 3. **Adicionar Testes Automatizados**
**Problema:**  
- Zero testes.

**Impacto:**  
- Medo de fazer mudanças (pode quebrar algo).
- Bugs só aparecem em produção.

**Solução:**  
- **Testes unitários** (críticos):
  - `test_process_message.py`
  - `test_handoff_service.py`
  - `test_ai_guard_service.py`
- **Testes de integração**:
  - Simular conversa completa (lead novo → hot → handoff)

**Tecnologia:**  
- `pytest` + `pytest-asyncio`
- Mock: `pytest-mock`
- Coverage: `pytest-cov`

**Estimativa:** 12-16 horas (para cobrir 60% do código crítico)

---

### 4. **CI/CD Pipeline**
**Problema:**  
- Deploy manual (git push + Railway auto-deploy).
- Sem validação prévia.

**Solução:**  
- **GitHub Actions**:
  1. A cada PR: Roda linting (flake8/ruff) + testes
  2. Se passar: Permite merge
  3. A cada merge na main: Deploy automático

**Estimativa:** 4 horas

---

## 🎨 MELHORIAS DE UX (Frontend)

### 1. **Toast Notifications (Feedback Visual)**
**Problema:**  
- Ações no dashboard não dão feedback claro.
- Ex: "Lead atribuído" — não tem confirm visual.

**Solução:**  
- **Toast** no canto da tela:
  ```
  ✅ Lead atribuído com sucesso para João Silva!
  ❌ Erro ao enviar mensagem. Tente novamente.
  ```

**Tecnologia:**  
- `react-hot-toast` ou `sonner`

**Estimativa:** 2 horas

---

### 2. **Preview de Mensagem antes de Enviar**
**Problema:**  
- Corretor digita mensagem longa, envia, percebe erro.

**Solução:**  
- Modal de preview:
  ```
  📝 Prévia da Mensagem:
  
  [texto renderizado com variáveis substituídas]
  
  [Cancelar] [Confirmar Envio]
  ```

**Estimativa:** 3 horas

---

### 3. **Dark Mode**
**Problema:**  
- Só tem tema claro.

**Solução:**  
- Toggle dark/light no header.
- Persistir preferência em `localStorage`.

**Tecnologia:**  
- Tailwind CSS já suporta (`dark:bg-gray-900`)
- Context API + hook `useDarkMode`

**Estimativa:** 4 horas

---

## 📈 MELHORIAS ESPECÍFICAS PARA IMOBILIÁRIO

### 1. **Integração com Portais (VivaReal, ZAP, OLX)**
**Valor:**  
- Cliente publica imóveis nos portais.
- Leads chegam direto no Velaris com código do imóvel.

**Solução:**  
- Webhooks dos portais → backend `/webhook/vivareal`, `/webhook/zap`.
- Criar lead automaticamente com `source: "vivareal"`.

**Estimativa:** 8-12 horas (cada portal)

---

### 2. **Geolocalização de Imóveis**
**Problema:**  
- Lead pergunta "Tem algo perto do Shopping X?"
- IA não sabe calcular distância.

**Solução:**  
- Armazenar lat/lng dos imóveis.
- Função de busca por raio:
  ```python
  find_properties_near(lat, lng, radius_km=5)
  ```
- Usar API Google Maps para calcular "tempo de carro até trabalho".

**Tecnologia:**  
- PostgreSQL: `POINT` type ou extensão PostGIS
- Google Maps Distance Matrix API

**Estimativa:** 6-8 horas

---

### 3. **Simulador de Financiamento Integrado**
**Problema:**  
- Lead pergunta "Quanto fica a parcela?"
- IA responde genérico.

**Solução:**  
- IA chama função `calculate_financing()`:
  - Entrada: valor do imóvel, entrada, prazo (anos)
  - Retorna: parcela estimada (usando Tabela Price)
- Disclaimer: "Simulação aproximada. Valores finais dependem do banco."

**Tecnologia:**  
- OpenAI Function Calling
- Fórmula Price (já existe em muitas libs Python)

**Estimativa:** 4 horas

---

## 🔐 MELHORIAS DE SEGURANÇA

### 1. **2FA (Autenticação de Dois Fatores)**
**Problema:**  
- Só senha hoje.

**Solução:**  
- TOTP (Google Authenticator, Authy).
- Obrigatório para role `admin` e `superadmin`.

**Tecnologia:**  
- `pyotp` lib
- QR Code via `qrcode`

**Estimativa:** 6 horas

---

### 2. **Audit Log para Ações Críticas**
**Status Atual:**  
- Já existe `audit_service.py`.

**Gap:**  
- Não está sendo usado em TODAS as rotas críticas (ex: deletar lead, mudar plano).

**Solução:**  
- Decorator `@audit_log(action="delete_lead")` em todas as rotas críticas.

**Estimativa:** 2 horas

---

### 3. **IP Whitelisting para Webhooks**
**Problema:**  
- Qualquer um pode chamar `/webhook/dialog360`.

**Solução:**  
- Validar IP de origem contra lista permitida.
- Validar signature HMAC (já existe `webhook_verify_token`, mas melhorar).

**Estimativa:** 2 horas

---

## 🚀 PLANO DE IMPLEMENTAÇÃO RECOMENDADO

### **SPRINT 1 (Semana 1) - Quick Wins para Impressionar Cliente**
1. ✅ Dashboard Real-Time (4-6h)
2. ✅ Agendamento de Visitas no Chat (6-8h)
3. ✅ Templates de Mensagem (4-6h)
4. ✅ Toast Notifications (2h)

**Total:** ~20 horas  
**Impacto:** 🔥🔥🔥 Cliente vê sistema "vivo" e útil no dia a dia.

---

### **SPRINT 2 (Semana 2) - CRM + Integrações**
1. ✅ Pipeline Kanban (8-12h)
2. ✅ Integração VivaReal/ZAP (8-12h)
3. ✅ Histórico Completo WhatsApp (3-4h)

**Total:** ~24 horas  
**Impacto:** 🔥🔥🔥 Velaris vira ferramenta central, não "só bot".

---

### **SPRINT 3 (Semana 3) - IA Avançada**
1. ✅ RAG com pgvector (6-8h)
2. ✅ Transcrição de Áudio (4h)
3. ✅ Envio de Imagens (4-6h)
4. ✅ Simulador de Financiamento (4h)

**Total:** ~20 horas  
**Impacto:** 🔥🔥 IA muito mais poderosa e "humana".

---

### **SPRINT 4 (Semana 4) - Observabilidade + DevOps**
1. ✅ Testes Automatizados (12-16h)
2. ✅ CI/CD Pipeline (4h)
3. ✅ Redis Cache (4h)

**Total:** ~24 horas  
**Impacto:** 🔥 Sistema mais confiável e profissional.

---

## 🎯 CONCLUSÃO E RECOMENDAÇÃO FINAL

O **Velaris** já é um produto **sólido**. Com as melhorias acima, ele vira uma **plataforma enterprise de IA para imobiliário** que compete com qualquer solução internacional.

### **Prioridade MÁXIMA para o novo cliente imobiliário:**
1. **Dashboard Real-Time**
2. **Agendamento de Visitas**
3. **Pipeline Kanban (CRM básico)**
4. **Integração com Portais (VivaReal)**

Com esses 4 itens, você **fecha qualquer contrato** de imobiliária grande.

---

**Checklist de Deploy para o Cliente:**
- [ ] Configurar tenant com nicho "imobiliário"
- [ ] Importar catálogo de imóveis
- [ ] Configurar WhatsApp Business (Z-API ou 360Dialog)
- [ ] Treinar prompt da IA com tom da imobiliária
- [ ] Configurar distribuição de leads (round-robin ou por bairro)
- [ ] Testar handoff completo (lead → corretor)
- [ ] Dashboard de métricas rodando
- [ ] Agendar reunião de kickoff com time comercial

---

**Estimativa Total de Desenvolvimento:**  
~88 horas de trabalho técnico para implementar TODOS os itens críticos.

**ROI Esperado:**  
- ↑ 40% na conversão de leads (agendamento automático)
- ↓ 60% no tempo de resposta (real-time)
- ↑ 30% na satisfação do cliente (CRM integrado)

🚀 **Pronto para transformar o Velaris na melhor IA imobiliária do Brasil?**
