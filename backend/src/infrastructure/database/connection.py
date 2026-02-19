"""Gerencia conexão com PostgreSQL."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
    pool_size=settings.db_pool_size,        # Configurável via env (padrão: 10)
    max_overflow=settings.db_max_overflow,  # Configurável via env (padrão: 20)
    pool_recycle=settings.db_pool_recycle,  # Recicla conexões velhas (padrão: 1800s)
    pool_timeout=settings.db_pool_timeout,  # Timeout para obter conexão (padrão: 10s)

    # ✅ SEGURANÇA NÍVEL EMPRESARIAL:
    # - statement_timeout: Cancela queries que levam > 60s (previne deadlocks)
    # - application_name: Identifica a aplicação nas logs do Postgres
    # NOTA: asyncpg usa server_settings (não connect_args direto)
    connect_args={
        "server_settings": {
            "application_name": "vellarys_api",
            "statement_timeout": "60000",  # 60 segundos em milissegundos
        }
    }
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
    print("[DB] Iniciando verificação do banco de dados...")
    async with engine.begin() as conn:
        # Cria as tabelas que não existem (baseado nos models SQLAlchemy)
        # NOTA: Para alterações em tabelas existentes, use Alembic migrations.
        await conn.run_sync(Base.metadata.create_all)
    print("[DB] Tabelas verificadas com sucesso.")
