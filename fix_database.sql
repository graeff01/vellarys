BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'leads' AND column_name = 'attended_by') THEN
        ALTER TABLE leads ADD COLUMN attended_by VARCHAR(20) DEFAULT 'ai';
        RAISE NOTICE '✅ attended_by criado';
    ELSE
        RAISE NOTICE 'ℹ️ attended_by já existe';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'leads' AND column_name = 'seller_took_over_at') THEN
        ALTER TABLE leads ADD COLUMN seller_took_over_at TIMESTAMPTZ;
        RAISE NOTICE '✅ seller_took_over_at criado';
    ELSE
        RAISE NOTICE 'ℹ️ seller_took_over_at já existe';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'messages' AND column_name = 'sender_type') THEN
        ALTER TABLE messages ADD COLUMN sender_type VARCHAR(20);
        RAISE NOTICE '✅ sender_type criado';
    ELSE
        RAISE NOTICE 'ℹ️ sender_type já existe';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'messages' AND column_name = 'sender_user_id') THEN
        ALTER TABLE messages ADD COLUMN sender_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
        RAISE NOTICE '✅ sender_user_id criado';
    ELSE
        RAISE NOTICE 'ℹ️ sender_user_id já existe';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'sellers' AND column_name = 'user_id') THEN
        ALTER TABLE sellers ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
        RAISE NOTICE '✅ user_id criado em sellers';
    ELSE
        RAISE NOTICE 'ℹ️ user_id já existe em sellers';
    END IF;
END $$;

UPDATE messages SET sender_type = CASE WHEN role = 'assistant' THEN 'ai' WHEN role = 'system' THEN 'system' ELSE NULL END WHERE sender_type IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'corretor' AND enumtypid = 'userrole'::regtype) THEN
        ALTER TYPE userrole ADD VALUE 'corretor';
        RAISE NOTICE '✅ Enum corretor adicionado';
    ELSE
        RAISE NOTICE 'ℹ️ Enum corretor já existe';
    END IF;
EXCEPTION WHEN duplicate_object THEN RAISE NOTICE 'ℹ️ Enum corretor já existe';
END $$;

COMMIT;

SELECT 'SUCESSO! Todas as colunas foram criadas!' as resultado;
