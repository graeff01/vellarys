-- ============================================================================
-- FIX: Adiciona colunas faltantes do CRM Inbox
-- ============================================================================
-- Execute este script diretamente no banco de produção via Railway CLI

-- 1. Adiciona coluna attended_by na tabela leads
ALTER TABLE leads
ADD COLUMN IF NOT EXISTS attended_by VARCHAR(20) DEFAULT 'ai';

-- 2. Adiciona coluna seller_took_over_at na tabela leads
ALTER TABLE leads
ADD COLUMN IF NOT EXISTS seller_took_over_at TIMESTAMPTZ;

-- 3. Adiciona coluna sender_type na tabela messages
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS sender_type VARCHAR(20);

-- 4. Adiciona coluna sender_user_id na tabela messages
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS sender_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

-- 5. Adiciona coluna user_id na tabela sellers
ALTER TABLE sellers
ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

-- 6. Backfill sender_type para mensagens existentes
UPDATE messages
SET sender_type = CASE
    WHEN role = 'assistant' THEN 'ai'
    WHEN role = 'system' THEN 'system'
    ELSE NULL
END
WHERE sender_type IS NULL;

-- 7. Adiciona enum 'corretor' ao UserRole (se não existir)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'corretor' AND enumtypid = 'userrole'::regtype) THEN
        ALTER TYPE userrole ADD VALUE 'corretor';
    END IF;
END
$$;

-- Verificação
SELECT 'attended_by' as column_name, COUNT(*) as rows_with_value FROM leads WHERE attended_by IS NOT NULL
UNION ALL
SELECT 'sender_type', COUNT(*) FROM messages WHERE sender_type IS NOT NULL
UNION ALL
SELECT 'user_id (sellers)', COUNT(*) FROM sellers WHERE user_id IS NOT NULL;
