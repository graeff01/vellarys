import asyncio
import logging
from sqlalchemy import text
from src.infrastructure.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def sync_products_table():
    """
    Adiciona colunas faltantes na tabela products para evitar erros de UndefinedColumn.
    """
    columns_to_add = [
        ("latitude", "DOUBLE PRECISION"),
        ("longitude", "DOUBLE PRECISION"),
        ("pdf_url", "VARCHAR(500)"),
        ("folder_url", "VARCHAR(500)")
    ]
    
    async with engine.begin() as conn:
        logger.info("🛠️ Verificando colunas na tabela 'products'...")
        
        for col_name, col_type in columns_to_add:
            try:
                # Tenta adicionar a coluna
                await conn.execute(text(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}"))
                logger.info(f"✅ Coluna '{col_name}' adicionada com sucesso.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"ℹ️ Coluna '{col_name}' já existe.")
                else:
                    logger.error(f"❌ Erro ao adicionar coluna '{col_name}': {e}")

if __name__ == "__main__":
    asyncio.run(sync_products_table())
