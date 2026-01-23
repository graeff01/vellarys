# 🚀 CRM INBOX - Implementação Completa

## 📋 VISÃO GERAL

Sistema de **Inbox para Corretores** que permite atendimento via painel CRM ao invés de WhatsApp pessoal.

### **Diferença dos Modos**

| Aspecto | WhatsApp Pessoal (Legado) | CRM Inbox (Novo) |
|---------|---------------------------|------------------|
| **Onde corretor atende** | WhatsApp pessoal | Painel CRM |
| **Como corretor responde** | Pelo próprio celular | Via interface web |
| **WhatsApp usado** | Pessoal do corretor | Da empresa |
| **Login necessário** | ❌ Não | ✅ Sim |
| **Controle centralizado** | ❌ Não | ✅ Sim |
| **IA para quando** | Ao transferir | Quando corretor assume |

---

## 🏗️ ARQUITETURA

### **Componentes Criados/Modificados**

#### 1. **Database (4 Migrations)**
- `20260124_add_seller_user_link.py` - Vincula Seller → User
- `20260124_add_handoff_control.py` - Controle de quem atende (attended_by)
- `20260124_add_message_sender_type.py` - Rastreamento de mensagens
- `20260124_add_handoff_mode_config.py` - Configuração do modo

#### 2. **Models**
- **Seller**: Campo `user_id` (FK para users)
- **Lead**: Campos `attended_by`, `seller_took_over_at`
- **Message**: Campos `sender_type`, `sender_user_id`
- **UserRole**: Novo valor `SELLER = "corretor"`

#### 3. **API Endpoints**

**Inbox do Corretor** (`/api/v1/seller/inbox/`):
- `GET /leads` - Lista leads atribuídos
- `GET /leads/{id}/messages` - Histórico de conversa
- `POST /leads/{id}/take-over` - Assumir conversa
- `POST /leads/{id}/send-message` - Enviar mensagem
- `POST /leads/{id}/return-to-ai` - Devolver para IA
- `POST /admin/link-seller-user` - Vincular corretor a usuário

**Configuração** (`/api/v1/tenants/{slug}/`):
- `POST /handoff-mode` - Configurar modo (crm_inbox ou whatsapp_pessoal)
- `GET /handoff-mode` - Ver modo atual

#### 4. **Lógica de Negócio**
- `process_message.py` - IA para quando `attended_by == "seller"`
- `handoff_service.py` - Respeita `handoff_mode` nas notificações

---

## 🔄 FLUXO COMPLETO

### **Modo CRM Inbox**

```
1. Lead envia mensagem no WhatsApp
   ↓
2. IA atende e qualifica automaticamente
   ↓
3. Sistema atribui lead ao corretor
   (lead.attended_by = "ai" por padrão)
   ↓
4. Corretor recebe notificação no dashboard
   (NÃO no WhatsApp pessoal!)
   ↓
5. Corretor faz login no CRM
   ↓
6. Corretor vê lead no inbox
   ↓
7. Corretor clica "Assumir Conversa"
   → lead.attended_by = "seller"
   → lead.seller_took_over_at = NOW()
   ↓
8. Corretor responde pelo CRM
   → Mensagem enviada via WhatsApp DA EMPRESA
   → sender_type = "seller"
   → sender_user_id = ID do corretor
   ↓
9. Lead responde
   → IA NÃO RESPONDE MAIS (verifica attended_by)
   → Mensagem salva normalmente
   ↓
10. Corretor continua atendendo via CRM
```

### **Modo WhatsApp Pessoal (Legado)**

```
1. Lead envia mensagem
   ↓
2. IA atende e qualifica
   ↓
3. Sistema atribui e transfere lead
   ↓
4. Corretor recebe no WhatsApp PESSOAL
   ↓
5. Corretor responde pelo próprio celular
   ↓
6. IA para de responder (lead transferido)
```

---

## 🔧 CONFIGURAÇÃO

### **1. Ativar Modo CRM Inbox**

```bash
curl -X POST http://localhost:8000/api/v1/tenants/SEU_SLUG/handoff-mode \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "handoff_mode": "crm_inbox"
  }'
```

### **2. Criar Usuário Corretor**

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pedro Corretor",
    "email": "pedro@exemplo.com",
    "password": "senha123",
    "role": "corretor",
    "tenant_id": 1
  }'
```

### **3. Vincular Corretor ao Usuário**

```bash
curl -X POST http://localhost:8000/api/v1/seller/inbox/admin/link-seller-user \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "seller_id": 1,
    "user_id": 5
  }'
```

---

## 📡 API REFERENCE

### **Seller Inbox Endpoints**

#### `GET /api/v1/seller/inbox/leads`
Lista leads atribuídos ao corretor logado.

**Query Params:**
- `status_filter`: string (opcional) - Filtrar por status
- `attended_filter`: "ai" | "seller" | "all" (opcional)

**Response:**
```json
[
  {
    "id": 123,
    "name": "João Silva",
    "phone": "11999999999",
    "status": "qualificado",
    "qualification": "quente",
    "attended_by": "ai",
    "unread_messages": 3,
    "last_message_at": "2026-01-24T10:30:00Z",
    "last_message_preview": "Gostaria de agendar visita...",
    "city": "São Paulo",
    "interest": "Apartamento 2 quartos",
    "budget": "R$ 500.000",
    "is_taken_over": false,
    "seller_took_over_at": null
  }
]
```

#### `GET /api/v1/seller/inbox/leads/{lead_id}/messages`
Retorna histórico completo de mensagens.

**Response:**
```json
[
  {
    "id": 1,
    "role": "user",
    "content": "Olá, tenho interesse",
    "created_at": "2026-01-24T10:00:00Z",
    "sender_type": null,
    "sender_user_id": null,
    "sender_name": "Cliente"
  },
  {
    "id": 2,
    "role": "assistant",
    "content": "Olá! Que bom receber...",
    "created_at": "2026-01-24T10:00:05Z",
    "sender_type": "ai",
    "sender_user_id": null,
    "sender_name": "Assistente IA"
  }
]
```

#### `POST /api/v1/seller/inbox/leads/{lead_id}/take-over`
Corretor assume a conversa. IA para de responder.

**Response:**
```json
{
  "success": true,
  "message": "Conversa assumida com sucesso!",
  "lead_id": 123,
  "attended_by": "seller",
  "took_over_at": "2026-01-24T11:00:00Z"
}
```

**Efeitos:**
- `lead.attended_by = "seller"`
- `lead.seller_took_over_at = NOW()`
- `lead.status = "handed_off"`
- Mensagem de sistema adicionada ao histórico

#### `POST /api/v1/seller/inbox/leads/{lead_id}/send-message`
Envia mensagem como corretor.

**Body:**
```json
{
  "content": "Olá João! Aqui é o corretor Pedro..."
}
```

**Requisito:** Corretor deve ter assumido a conversa antes.

**Response:**
```json
{
  "success": true,
  "message": "Mensagem enviada com sucesso",
  "message_id": 456,
  "sent_at": "2026-01-24T11:05:00Z"
}
```

**Efeitos:**
- Mensagem salva com `sender_type = "seller"` e `sender_user_id = <corretor_id>`
- Enviada via WhatsApp da empresa para o lead
- `lead.last_message_at` atualizado

#### `POST /api/v1/seller/inbox/leads/{lead_id}/return-to-ai`
Devolve lead para a IA.

**Response:**
```json
{
  "success": true,
  "message": "Lead devolvido para a IA",
  "attended_by": "ai"
}
```

**Quando usar:**
- Corretor não conseguiu contato
- Lead pediu para voltar depois
- Quer que IA continue nutrindo

---

### **Configuration Endpoints**

#### `POST /api/v1/tenants/{slug}/handoff-mode`
Configura modo de handoff.

**Body:**
```json
{
  "handoff_mode": "crm_inbox"
}
```

**Valores possíveis:**
- `"crm_inbox"` - Modo CRM (novo)
- `"whatsapp_pessoal"` - Modo legado

**Permissão:** Apenas ADMIN, MANAGER ou SUPERADMIN

#### `GET /api/v1/tenants/{slug}/handoff-mode`
Retorna modo atual.

**Response:**
```json
{
  "success": true,
  "handoff_mode": "crm_inbox",
  "message": "Modo CRM Inbox: Corretores atendem via painel"
}
```

---

## 🗄️ DATABASE SCHEMA

### **Novos Campos**

#### **sellers**
```sql
user_id INTEGER NULLABLE,  -- FK para users.id
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
```

#### **leads**
```sql
attended_by VARCHAR(20) DEFAULT 'ai',  -- "ai", "seller", "manager"
seller_took_over_at TIMESTAMP WITH TIME ZONE NULLABLE
```

#### **messages**
```sql
sender_type VARCHAR(20) NULLABLE,  -- "ai", "seller", "manager", "system"
sender_user_id INTEGER NULLABLE,   -- FK para users.id
FOREIGN KEY (sender_user_id) REFERENCES users(id) ON DELETE SET NULL
```

#### **tenants.settings**
```json
{
  "handoff_mode": "crm_inbox" | "whatsapp_pessoal"
}
```

---

## 🔐 AUTENTICAÇÃO E PERMISSÕES

### **Roles**
- `SELLER = "corretor"` - Acesso ao inbox, pode atender leads

### **Endpoints e Permissões**

| Endpoint | Permissão Necessária |
|----------|---------------------|
| `GET /seller/inbox/leads` | `role = "corretor"` |
| `POST /seller/inbox/leads/{id}/take-over` | `role = "corretor"` + lead atribuído |
| `POST /seller/inbox/leads/{id}/send-message` | `role = "corretor"` + conversa assumida |
| `POST /seller/inbox/admin/link-seller-user` | `role IN ["admin", "gestor", "superadmin"]` |
| `POST /tenants/{slug}/handoff-mode` | `role IN ["admin", "gestor", "superadmin"]` |

---

## 🧪 TESTES

### **Teste 1: Fluxo Completo CRM Inbox**

```bash
# 1. Ativar modo
curl -X POST localhost:8000/api/v1/tenants/demo/handoff-mode \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"handoff_mode": "crm_inbox"}'

# 2. Criar usuário corretor
curl -X POST localhost:8000/api/v1/auth/register \
  -d '{
    "name": "Pedro Corretor",
    "email": "pedro@demo.com",
    "password": "senha123",
    "role": "corretor",
    "tenant_id": 1
  }'

# 3. Vincular corretor a usuário
curl -X POST localhost:8000/api/v1/seller/inbox/admin/link-seller-user \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"seller_id": 1, "user_id": 5}'

# 4. Lead entra (via webhook ou simulação)

# 5. Corretor faz login
curl -X POST localhost:8000/api/v1/auth/login \
  -d '{
    "email": "pedro@demo.com",
    "password": "senha123"
  }'

# Recebe token do corretor
export SELLER_TOKEN="..."

# 6. Corretor lista leads
curl localhost:8000/api/v1/seller/inbox/leads \
  -H "Authorization: Bearer $SELLER_TOKEN"

# 7. Corretor assume conversa
curl -X POST localhost:8000/api/v1/seller/inbox/leads/123/take-over \
  -H "Authorization: Bearer $SELLER_TOKEN"

# 8. Corretor envia mensagem
curl -X POST localhost:8000/api/v1/seller/inbox/leads/123/send-message \
  -H "Authorization: Bearer $SELLER_TOKEN" \
  -d '{"content": "Olá! Aqui é o Pedro..."}'

# 9. Lead responde → IA NÃO responde mais
```

### **Teste 2: Verificar IA Não Responde**

```bash
# Após corretor assumir (step 7 acima)

# Lead envia mensagem (webhook)
# Verificar logs:
docker-compose logs backend | grep "corretor_atendendo"

# Deve aparecer:
# ⚠️ Lead 123 sendo atendido por corretor no CRM! IA não responde.
```

### **Teste 3: Backward Compatibility**

```bash
# Voltar para modo legado
curl -X POST localhost:8000/api/v1/tenants/demo/handoff-mode \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"handoff_mode": "whatsapp_pessoal"}'

# Lead entra → IA qualifica → Enviado para WhatsApp pessoal do corretor
# (comportamento antigo preservado)
```

---

## 📊 MONITORAMENTO

### **Logs Importantes**

```bash
# Ver modo de handoff
docker-compose logs backend | grep "Modo de handoff"

# Ver quando corretor assume
docker-compose logs backend | grep "assumiu o atendimento"

# Ver quando IA para de responder
docker-compose logs backend | grep "corretor_atendendo"

# Ver notificações enviadas
docker-compose logs backend | grep "CRM INBOX\|WHATSAPP PESSOAL"
```

### **Queries Úteis**

```sql
-- Ver modo configurado
SELECT slug, settings->'handoff_mode' as modo
FROM tenants
WHERE active = true;

-- Ver corretores com login
SELECT s.id, s.name, s.user_id, u.email
FROM sellers s
LEFT JOIN users u ON s.user_id = u.id
WHERE s.active = true;

-- Ver leads sendo atendidos por corretor
SELECT id, name, phone, attended_by, seller_took_over_at
FROM leads
WHERE attended_by = 'seller';

-- Ver mensagens de corretores
SELECT m.id, m.content, m.sender_type, u.name as sender_name
FROM messages m
LEFT JOIN users u ON m.sender_user_id = u.id
WHERE m.sender_type = 'seller';
```

---

## ⚠️ IMPORTANTE

### **Não Quebra Sistema Existente**
- Todos os tenants ficam com `handoff_mode = "whatsapp_pessoal"` por padrão
- Modo CRM Inbox é **opt-in** (precisa ativar)
- Corretores sem `user_id` continuam funcionando normalmente no modo legado

### **Campos Nullables**
- `Seller.user_id` - Corretor pode existir sem login
- `Lead.attended_by` - Default é `"ai"`
- `Message.sender_type` - Mensagens antigas continuam sem sender_type

### **Migrations Idempotentes**
- Usam `IF NOT EXISTS` / `column_exists()`
- Podem rodar múltiplas vezes sem erro
- Backfill automático de dados quando necessário

---

## 🚀 PRÓXIMOS PASSOS

1. **Frontend**: Tela de inbox para corretores
2. **Push Notifications**: Notificar corretor em tempo real
3. **Mobile App**: App para corretores atenderem via celular
4. **Métricas**: Dashboard de performance por corretor
5. **Auto-Assignment**: Regras inteligentes de distribuição
6. **SLA Tracking**: Monitorar tempo de resposta dos corretores

---

## 📚 REFERÊNCIAS

- Migrations: `/backend/alembic/versions/20260124_*.py`
- API: `/backend/src/api/routes/seller_inbox.py`
- Models: `/backend/src/domain/entities/{seller,models,enums}.py`
- Lógica IA: `/backend/src/application/use_cases/process_message.py:927-949`
- Handoff: `/backend/src/infrastructure/services/handoff_service.py:353-471`

---

**Implementado por:** Claude Sonnet 4.5
**Data:** 24/01/2026
**Versão:** 1.0.0
