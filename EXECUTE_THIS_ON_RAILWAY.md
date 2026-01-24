# 🚨 FIX RÁPIDO: Execute no Railway PostgreSQL

Se o backend continuar falhando com "column does not exist", execute este SQL diretamente no banco do Railway:

## 📋 Passo a Passo

### 1. Acesse o Railway
- Vá em https://railway.app
- Entre no projeto Velaris
- Clique no serviço **PostgreSQL**

### 2. Abra o Query Editor
- Clique em **Data**
- Clique em **Query**

### 3. Cole e Execute Este SQL

```sql
-- FIX RÁPIDO: Adiciona todas as colunas faltantes
-- Execute TODO este bloco de uma vez

BEGIN;

-- 1. Adiciona coluna attended_by
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'leads' AND column_name = 'attended_by'
    ) THEN
        ALTER TABLE leads ADD COLUMN attended_by VARCHAR(20) DEFAULT 'ai';
        RAISE NOTICE 'Coluna attended_by criada';
    ELSE
        RAISE NOTICE 'Coluna attended_by já existe';
    END IF;
END $$;

-- 2. Adiciona coluna seller_took_over_at
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'leads' AND column_name = 'seller_took_over_at'
    ) THEN
        ALTER TABLE leads ADD COLUMN seller_took_over_at TIMESTAMPTZ;
        RAISE NOTICE 'Coluna seller_took_over_at criada';
    ELSE
        RAISE NOTICE 'Coluna seller_took_over_at já existe';
    END IF;
END $$;

-- 3. Adiciona coluna sender_type
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'sender_type'
    ) THEN
        ALTER TABLE messages ADD COLUMN sender_type VARCHAR(20);
        RAISE NOTICE 'Coluna sender_type criada';
    ELSE
        RAISE NOTICE 'Coluna sender_type já existe';
    END IF;
END $$;

-- 4. Adiciona coluna sender_user_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'sender_user_id'
    ) THEN
        ALTER TABLE messages ADD COLUMN sender_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
        RAISE NOTICE 'Coluna sender_user_id criada';
    ELSE
        RAISE NOTICE 'Coluna sender_user_id já existe';
    END IF;
END $$;

-- 5. Adiciona coluna user_id em sellers
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sellers' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE sellers ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
        RAISE NOTICE 'Coluna user_id criada';
    ELSE
        RAISE NOTICE 'Coluna user_id já existe';
    END IF;
END $$;

-- 6. Backfill sender_type
UPDATE messages
SET sender_type = CASE
    WHEN role = 'assistant' THEN 'ai'
    WHEN role = 'system' THEN 'system'
    ELSE NULL
END
WHERE sender_type IS NULL;

-- 7. Adiciona enum 'corretor' (se não existir)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'corretor'
        AND enumtypid = 'userrole'::regtype
    ) THEN
        ALTER TYPE userrole ADD VALUE 'corretor';
        RAISE NOTICE 'Enum corretor adicionado';
    ELSE
        RAISE NOTICE 'Enum corretor já existe';
    END IF;
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'Enum corretor já existe (duplicate)';
END $$;

COMMIT;

-- Verificação
SELECT
    'leads.attended_by' as coluna,
    COUNT(*) as total_rows,
    COUNT(attended_by) as rows_with_value
FROM leads
UNION ALL
SELECT
    'messages.sender_type',
    COUNT(*),
    COUNT(sender_type)
FROM messages
UNION ALL
SELECT
    'sellers.user_id',
    COUNT(*),
    COUNT(user_id)
FROM sellers;
```

### 4. Clique em "Run Query"

Você deve ver mensagens como:
```
NOTICE: Coluna attended_by criada
NOTICE: Coluna seller_took_over_at criada
NOTICE: Coluna sender_type criada
NOTICE: Coluna sender_user_id criada
NOTICE: Coluna user_id criada
NOTICE: Enum corretor adicionado
```

### 5. Reinicie o Backend
- Volte para o serviço **backend**
- Clique em **⋮** (três pontos)
- Clique em **Restart**

---

## ✅ Depois do Fix

O backend deve subir sem erros e você poderá:

1. ✅ Criar vendedores com conta de usuário
2. ✅ Ativar modo CRM Inbox
3. ✅ Fazer login como corretor
4. ✅ Acessar /dashboard/inbox

---

## 🔍 Verificação

Para confirmar que deu certo, execute esta query:

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name IN ('leads', 'messages', 'sellers')
  AND column_name IN ('attended_by', 'seller_took_over_at', 'sender_type', 'sender_user_id', 'user_id')
ORDER BY table_name, column_name;
```

Deve retornar 5 linhas mostrando todas as colunas criadas.

---

**Tempo estimado:** 2 minutos
**Dificuldade:** Fácil (só copiar e colar)
