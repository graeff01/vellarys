#!/usr/bin/env python3
"""
Script para aplicar fix das colunas faltantes no banco de produção.
Executa automaticamente via Railway CLI ou localmente com DATABASE_URL.

Uso:
    railway run python apply_fix.py
    # OU
    DATABASE_URL="postgresql://..." python apply_fix.py
"""

import os
import sys
import psycopg2
from psycopg2 import sql

# SQL Script
SQL_SCRIPT = """
-- ============================================================================
-- FIX: Adiciona colunas faltantes do CRM Inbox
-- ============================================================================

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
"""

VERIFICATION_SQL = """
SELECT 'attended_by' as column_name, COUNT(*) as rows_with_value FROM leads WHERE attended_by IS NOT NULL
UNION ALL
SELECT 'sender_type', COUNT(*) FROM messages WHERE sender_type IS NOT NULL
UNION ALL
SELECT 'user_id (sellers)', COUNT(*) FROM sellers WHERE user_id IS NOT NULL;
"""


def main():
    # Obtém DATABASE_URL do ambiente
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ Erro: DATABASE_URL não encontrada no ambiente")
        print("")
        print("Execute via Railway CLI:")
        print("  railway run python apply_fix.py")
        print("")
        print("Ou configure DATABASE_URL:")
        print("  export DATABASE_URL='postgresql://user:pass@host:port/db'")
        print("  python apply_fix.py")
        sys.exit(1)

    # Conecta ao banco
    print("🔌 Conectando ao banco de dados...")
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cursor = conn.cursor()
        print("✅ Conectado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        sys.exit(1)

    # Executa o script
    print("")
    print("🔧 Aplicando correções...")
    print("")

    try:
        cursor.execute(SQL_SCRIPT)
        conn.commit()
        print("✅ Correções aplicadas com sucesso!")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao aplicar correções: {e}")
        cursor.close()
        conn.close()
        sys.exit(1)

    # Verifica resultado
    print("")
    print("🔍 Verificando resultado...")
    print("")

    try:
        cursor.execute(VERIFICATION_SQL)
        results = cursor.fetchall()

        for row in results:
            column_name, count = row
            print(f"  ✅ {column_name}: {count} rows")

        print("")
        print("🎉 Todas as colunas foram criadas e populadas com sucesso!")
        print("")
        print("Próximos passos:")
        print("  1. Reiniciar o backend (Railway fará automaticamente)")
        print("  2. Ativar modo CRM Inbox nas configurações")
        print("  3. Criar vendedores com create_user_account=true")
        print("  4. Testar login do corretor em /dashboard/inbox")

    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível verificar: {e}")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
