# 🚀 EXECUTAR MIGRAÇÃO NO RAILWAY - GUIA RÁPIDO

## ⏱️ Tempo Estimado: 2 minutos

---

## 📋 Passo a Passo

### 1. Acesse o Railway
- Vá em https://railway.app
- Entre no projeto **Vellarys**
- Clique no serviço **PostgreSQL**

### 2. Abra o Query Editor
- Clique em **Data**
- Clique em **Query**

### 3. Cole o SQL
- Abra o arquivo [`APPLY_PREMIUM_PLANS_RAILWAY.sql`](file:///Users/macbook/Documents/vellarys/APPLY_PREMIUM_PLANS_RAILWAY.sql)
- **Copie TODO o conteúdo** (Cmd+A, Cmd+C)
- **Cole no Query Editor** do Railway (Cmd+V)

### 4. Execute
- Clique em **Run Query**
- Aguarde a execução (5-10 segundos)

### 5. Verifique o Resultado

Você deve ver uma tabela como esta:

```
slug          | name         | price_monthly | price_yearly | leads_limit | sellers_limit | appointment_mode | has_api | sort_order | is_featured
--------------|--------------|---------------|--------------|-------------|---------------|------------------|---------|------------|------------
professional  | Professional | 897.00        | 8970.00      | 2000        | 15            | assisted         | false   | 1          | true
enterprise    | Enterprise   | 1997.00       | 19970.00     | -1          | -1            | automatic        | true    | 2          | false
```

E outra tabela mostrando clientes por plano:

```
plano         | nome_plano   | total_clientes
--------------|--------------|---------------
professional  | Professional | X
enterprise    | Enterprise   | Y
```

---

## ✅ O que foi feito

- ✅ Plano **Professional** criado/atualizado (R$ 897/mês)
- ✅ Plano **Enterprise** criado/atualizado (R$ 1.997/mês)
- ✅ Clientes do plano "Essencial" migrados para "Professional"
- ✅ Plano "Essencial" removido

---

## 🔄 Próximo Passo (Opcional)

Se quiser **reiniciar o backend** para garantir que está usando os novos planos:

1. Volte para o serviço **backend** no Railway
2. Clique em **⋮** (três pontos)
3. Clique em **Restart**

---

## 🎯 Validação

Para confirmar que tudo funcionou, você pode:

### Via API (se backend estiver rodando):

```bash
# Substituir pela URL do seu Railway
curl https://sua-api.railway.app/api/v1/admin/plans \
  -H "Authorization: Bearer SEU_TOKEN"
```

### Via SQL (no Railway Query Editor):

```sql
-- Ver todos os planos
SELECT slug, name, price_monthly, is_featured
FROM plans
WHERE active = true
ORDER BY sort_order;

-- Ver features do Professional
SELECT features
FROM plans
WHERE slug = 'professional';

-- Ver features do Enterprise
SELECT features
FROM plans
WHERE slug = 'enterprise';
```

---

## ❌ Se algo der errado

### Erro: "column does not exist"
- O SQL está preparado para criar colunas se não existirem
- Execute novamente

### Erro: "duplicate key value"
- Os planos já existem
- Isso é OK, o UPDATE vai funcionar

### Quero reverter
Execute este SQL:

```sql
BEGIN;

-- Recriar plano Essencial
INSERT INTO plans (slug, name, description, price_monthly, price_yearly, limits, features, sort_order, is_featured, active, created_at, updated_at)
VALUES (
    'essencial',
    'Essencial',
    'Para imobiliárias iniciando com IA',
    297.00,
    2970.00,
    '{"leads_per_month": 300, "messages_per_month": 3000, "sellers": 3, "ai_tokens_per_month": 150000}'::jsonb,
    '{"ai_qualification": true, "whatsapp_integration": true, "web_chat": true}'::jsonb,
    1,
    false,
    true,
    NOW(),
    NOW()
);

-- Reverter preços
UPDATE plans SET price_monthly = 697.00, price_yearly = 6970.00 WHERE slug = 'professional';
UPDATE plans SET price_monthly = 1497.00, price_yearly = 14970.00 WHERE slug = 'enterprise';

COMMIT;
```

---

## 📊 Resumo dos Novos Planos

### 🔵 Professional - R$ 897/mês
- 2.000 leads/mês
- 20.000 mensagens/mês
- 15 corretores
- Agendamento **ASSISTIDO** (IA sugere, corretor aprova)
- Reengajamento (1x/semana)
- Dashboard + Relatórios
- Voz humanizada

### 🟣 Enterprise - R$ 1.997/mês
- ∞ **Ilimitado** (leads, mensagens, corretores)
- Agendamento **AUTOMÁTICO** (IA agenda sozinha)
- Reengajamento ilimitado
- **API REST** completa
- **Webhooks**
- **White-Label**
- **AI Guard** + **Knowledge Base** + **Copilot**
- Account Manager dedicado
- SLA 99.5%

---

## 🎉 Pronto!

Após executar o SQL, seus planos B2B Premium estarão ativos e prontos para uso!

**Próximos passos:**
1. ✅ Testar criação de novo cliente
2. ✅ Verificar features no frontend
3. ✅ Notificar clientes existentes sobre upgrade
