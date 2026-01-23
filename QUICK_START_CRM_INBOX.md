# 🚀 Quick Start - CRM Inbox

## ⚡ COMEÇAR AGORA (3 passos)

### 1️⃣ Reiniciar Backend (Rodar Migrations)

```bash
cd /Users/macbook/Documents/vellarys
docker-compose restart backend

# OU rebuild completo
docker-compose down
docker-compose up -d --build backend
```

**Verificar se migrations rodaram:**
```bash
docker-compose logs backend | grep -i migration
```

Deve aparecer:
```
✅ Campo user_id adicionado à tabela sellers
✅ Campo attended_by adicionado à tabela leads
✅ Campo sender_type adicionado à tabela messages
✅ Configuração handoff_mode='whatsapp_pessoal' adicionada aos tenants existentes
```

---

### 2️⃣ Ativar Modo CRM Inbox

**Pelo frontend (recomendado):**
- Login como ADMIN
- Ir em Configurações > Integra Conversões
- Trocar "Modo de Handoff" para "CRM Inbox"
- Salvar

**Ou via API:**
```bash
export ADMIN_TOKEN="seu_token_admin"
export TENANT_SLUG="seu_tenant_slug"

curl -X POST "http://localhost:8000/api/v1/tenants/${TENANT_SLUG}/handoff-mode" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{"handoff_mode": "crm_inbox"}'
```

Resposta esperada:
```json
{
  "success": true,
  "handoff_mode": "crm_inbox",
  "message": "✅ Modo CRM Inbox ativado! Agora os corretores podem atender via painel do CRM..."
}
```

---

### 3️⃣ Criar e Vincular Corretor

#### **Opção A: Criar Novo Usuário Corretor**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pedro Corretor",
    "email": "pedro@exemplo.com",
    "password": "senha123",
    "role": "corretor",
    "tenant_id": 1
  }'
```

#### **Opção B: Transformar Usuário Existente em Corretor**

Via SQL:
```sql
UPDATE users
SET role = 'corretor'
WHERE email = 'usuario@exemplo.com';
```

#### **Vincular Corretor ao Seller**

```bash
curl -X POST "http://localhost:8000/api/v1/seller/inbox/admin/link-seller-user" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "seller_id": 1,
    "user_id": 5
  }'
```

Resposta esperada:
```json
{
  "success": true,
  "message": "Corretor Pedro vinculado ao usuário Pedro Corretor",
  "seller_id": 1,
  "user_id": 5
}
```

---

## ✅ TESTAR O FLUXO

### **1. Lead Entra e IA Qualifica**
- Envie mensagem via WhatsApp (ou webhook de teste)
- IA atende automaticamente e qualifica o lead

### **2. Corretor Faz Login no CRM**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "pedro@exemplo.com",
    "password": "senha123"
  }'
```

Guarde o token:
```bash
export SELLER_TOKEN="token_retornado"
```

### **3. Verificar Se Inbox Está Disponível**
```bash
curl "http://localhost:8000/api/v1/seller/info/check-inbox-available" \
  -H "Authorization: Bearer ${SELLER_TOKEN}"
```

Deve retornar:
```json
{
  "available": true,
  "reason": "CRM Inbox habilitado e corretor vinculado",
  "handoff_mode": "crm_inbox",
  "seller_id": 1,
  "seller_name": "Pedro Corretor"
}
```

### **4. Ver Informações Completas do Corretor**
```bash
curl "http://localhost:8000/api/v1/seller/info/me" \
  -H "Authorization: Bearer ${SELLER_TOKEN}"
```

### **5. Listar Leads Atribuídos**
```bash
curl "http://localhost:8000/api/v1/seller/inbox/leads" \
  -H "Authorization: Bearer ${SELLER_TOKEN}"
```

### **6. Ver Conversa de um Lead**
```bash
curl "http://localhost:8000/api/v1/seller/inbox/leads/123/messages" \
  -H "Authorization: Bearer ${SELLER_TOKEN}"
```

### **7. Assumir Conversa** ⚡
```bash
curl -X POST "http://localhost:8000/api/v1/seller/inbox/leads/123/take-over" \
  -H "Authorization: Bearer ${SELLER_TOKEN}"
```

**Efeito:** IA para de responder para este lead!

### **8. Enviar Mensagem Como Corretor**
```bash
curl -X POST "http://localhost:8000/api/v1/seller/inbox/leads/123/send-message" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${SELLER_TOKEN}" \
  -d '{
    "content": "Olá! Aqui é o Pedro, corretor. Vi seu interesse em imóveis. Como posso ajudar?"
  }'
```

Mensagem é enviada via **WhatsApp da empresa** para o lead.

### **9. Lead Responde**
Lead envia mensagem → **IA NÃO RESPONDE MAIS**

Verificar logs:
```bash
docker-compose logs backend | grep "corretor_atendendo"
```

Deve aparecer:
```
⚠️ Lead 123 sendo atendido por corretor no CRM! IA não responde.
```

✅ **SUCESSO!** O corretor agora controla a conversa via CRM.

---

## 📊 VERIFICAÇÕES

### **Verificar Modo Ativo**
```bash
curl "http://localhost:8000/api/v1/tenants/${TENANT_SLUG}/handoff-mode" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

### **Ver Corretores Vinculados** (SQL)
```sql
SELECT
  s.id as seller_id,
  s.name as seller_name,
  s.user_id,
  u.email as user_email,
  u.role as user_role
FROM sellers s
LEFT JOIN users u ON s.user_id = u.id
WHERE s.active = true;
```

### **Ver Leads Sendo Atendidos por Corretor** (SQL)
```sql
SELECT
  l.id,
  l.name,
  l.phone,
  l.attended_by,
  l.seller_took_over_at,
  s.name as seller_name
FROM leads l
LEFT JOIN sellers s ON l.assigned_seller_id = s.id
WHERE l.attended_by = 'seller';
```

### **Ver Mensagens de Corretores** (SQL)
```sql
SELECT
  m.id,
  m.content,
  m.sender_type,
  m.created_at,
  u.name as sender_name,
  l.name as lead_name
FROM messages m
LEFT JOIN users u ON m.sender_user_id = u.id
LEFT JOIN leads l ON m.lead_id = l.id
WHERE m.sender_type = 'seller'
ORDER BY m.created_at DESC
LIMIT 10;
```

---

## 🔧 TROUBLESHOOTING

### **Problema: Inbox não aparece**

**Verificar:**
1. Modo CRM Inbox está ativado?
   ```bash
   curl "http://localhost:8000/api/v1/tenants/${TENANT_SLUG}/handoff-mode" \
     -H "Authorization: Bearer ${ADMIN_TOKEN}"
   ```

2. Usuário tem role "corretor"?
   ```sql
   SELECT email, role FROM users WHERE email = 'pedro@exemplo.com';
   ```

3. Corretor está vinculado ao seller?
   ```sql
   SELECT * FROM sellers WHERE user_id = 5;
   ```

### **Problema: IA continua respondendo**

**Verificar:**
1. Corretor assumiu a conversa?
   ```sql
   SELECT attended_by FROM leads WHERE id = 123;
   ```
   Deve ser `"seller"`, não `"ai"`.

2. Logs do backend:
   ```bash
   docker-compose logs backend | tail -100
   ```

### **Problema: Não consigo enviar mensagem**

**Erro:** "Você precisa assumir a conversa antes de enviar mensagens"

**Solução:** Chamar endpoint `/take-over` primeiro:
```bash
curl -X POST "http://localhost:8000/api/v1/seller/inbox/leads/123/take-over" \
  -H "Authorization: Bearer ${SELLER_TOKEN}"
```

### **Problema: Migrations não rodaram**

```bash
# Entrar no container
docker-compose exec backend bash

# Rodar manualmente
alembic upgrade head

# Ver revisão atual
alembic current

# Ver histórico
alembic history
```

---

## 🎯 ENDPOINTS ÚTEIS

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/seller/info/me` | GET | Info do corretor |
| `/api/v1/seller/info/check-inbox-available` | GET | Verificar disponibilidade |
| `/api/v1/seller/inbox/leads` | GET | Listar leads |
| `/api/v1/seller/inbox/leads/{id}/messages` | GET | Ver conversa |
| `/api/v1/seller/inbox/leads/{id}/take-over` | POST | Assumir conversa |
| `/api/v1/seller/inbox/leads/{id}/send-message` | POST | Enviar mensagem |
| `/api/v1/seller/inbox/leads/{id}/return-to-ai` | POST | Devolver para IA |
| `/api/v1/tenants/{slug}/handoff-mode` | GET/POST | Ver/Configurar modo |

---

## 📚 DOCUMENTAÇÃO COMPLETA

Para detalhes técnicos completos, veja:
- **[CRM_INBOX_IMPLEMENTATION.md](./CRM_INBOX_IMPLEMENTATION.md)** - Documentação técnica completa
- Migrations: `/backend/alembic/versions/20260124_*.py`
- API: `/backend/src/api/routes/seller_inbox.py`

---

**Dúvidas?** Veja os logs:
```bash
docker-compose logs -f backend
```

**Tudo funcionando?** 🎉 Agora é só construir o frontend!
