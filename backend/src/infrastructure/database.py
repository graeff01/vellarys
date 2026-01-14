from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from src.config import get_settings

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
    async with engine.begin() as conn:
        # Cria as tabelas que não existem
        await conn.run_sync(Base.metadata.create_all)
        
        # Sincroniza colunas extras da tabela products (fix UndefinedColumnError)
        columns_to_add = [
            ("latitude", "DOUBLE PRECISION"),
            ("longitude", "DOUBLE PRECISION"),
            ("pdf_url", "VARCHAR(500)"),
            ("folder_url", "VARCHAR(500)")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                await conn.execute(text(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}"))
                print(f"✅ Coluna '{col_name}' sincronizada na tabela products.")
            except Exception as e:
                # Ignora se a coluna já existe
                if "already exists" not in str(e).lower():
                    print(f"⚠️ Erro ao sincronizar coluna '{col_name}': {e}")
