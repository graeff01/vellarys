import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Base ORM
Base = declarative_base()

# Engine assíncrona
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# Inicialização do banco (criar tabelas)
async def init_db():
    print("🔍 [DB] Iniciando sincronização do banco de dados...")
    async with engine.begin() as conn:
        # 1. Cria as tabelas que não existem
        await conn.run_sync(Base.metadata.create_all)
        print("✅ [DB] Tabelas base verificadas.")
        
        # 2. Sincroniza colunas extras da tabela products (fix UndefinedColumnError)
        # Usamos ADD COLUMN IF NOT EXISTS (Postgres 9.6+)
        products_columns = [
            ("latitude", "DOUBLE PRECISION"),
            ("longitude", "DOUBLE PRECISION"),
            ("pdf_url", "VARCHAR(500)"),
            ("folder_url", "VARCHAR(500)")
        ]
        
        for col_name, col_type in products_columns:
            try:
                # O Postgres suporta ADD COLUMN IF NOT EXISTS
                await conn.execute(text(f"ALTER TABLE products ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"⚠️ [DB] Erro ao sincronizar coluna '{col_name}' em products: {e}")
        
        # 3. Sincroniza colunas extras da tabela leads (reengajamento)
        leads_columns = [
            ("reengagement_attempts", "INTEGER DEFAULT 0"),
            ("last_reengagement_at", "TIMESTAMP WITH TIME ZONE"),
            ("reengagement_status", "VARCHAR(20) DEFAULT 'none'"),
            ("last_activity_at", "TIMESTAMP WITH TIME ZONE")
        ]
        
        for col_name, col_type in leads_columns:
            try:
                await conn.execute(text(f"ALTER TABLE leads ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"⚠️ [DB] Erro ao sincronizar coluna '{col_name}' em leads: {e}")

    print("✅ [DB] Sincronização de colunas concluída.")
