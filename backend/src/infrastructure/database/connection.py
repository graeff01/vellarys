"""Gerencia conexão com PostgreSQL."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text
from src.config import get_settings

settings = get_settings()

database_url = settings.database_url

if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,        # Configurável via env
    max_overflow=settings.db_max_overflow,  # Configurável via env
    pool_recycle=settings.db_pool_recycle,  # Recicla conexões velhas
    pool_timeout=settings.db_pool_timeout,  # Timeout para obter conexão
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    from src.domain.entities import Base
    print("🔍 [DB] Iniciando sincronização robusta do banco de dados...")
    async with engine.begin() as conn:
        # 1. Cria as tabelas que não existem
        await conn.run_sync(Base.metadata.create_all)
        print("✅ [DB] Tabelas base verificadas.")
        
        # 2. Sincroniza colunas extras da tabela products (fix UndefinedColumnError)
        products_columns = [
            ("latitude", "DOUBLE PRECISION"),
            ("longitude", "DOUBLE PRECISION"),
            ("pdf_url", "VARCHAR(500)"),
            ("folder_url", "VARCHAR(500)")
        ]
        
        for col_name, col_type in products_columns:
            try:
                await conn.execute(text(f"ALTER TABLE products ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"⚠️ [DB] Erro ao sincronizar coluna '{col_name}' em products: {e}")
        
        # 3. Sincroniza colunas extras da tabela leads
        leads_columns = [
            ("reengagement_attempts", "INTEGER DEFAULT 0"),
            ("last_reengagement_at", "TIMESTAMP WITH TIME ZONE"),
            ("reengagement_status", "VARCHAR(20) DEFAULT 'none'"),
            ("last_activity_at", "TIMESTAMP WITH TIME ZONE"),
            ("conversation_summary", "TEXT"),
            ("summary", "TEXT"),
            ("propensity_score", "INTEGER DEFAULT 0")
        ]
        
        for col_name, col_type in leads_columns:
            try:
                await conn.execute(text(f"ALTER TABLE leads ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception as e:
                print(f"⚠️ [DB] Erro ao sincronizar coluna '{col_name}' em leads: {e}")

    print("✅ [DB] Sincronização de colunas concluída com sucesso.")
