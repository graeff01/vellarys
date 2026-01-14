import asyncio
import logging
from sqlalchemy import text
from src.infrastructure.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def sync_db():
    """
    Adiciona colunas faltantes nas tabelas para evitar erros de UndefinedColumn.
    """
    async with engine.begin() as conn:
        # Colunas Products
        products_columns = [
            ("latitude", "DOUBLE PRECISION"),
            ("longitude", "DOUBLE PRECISION"),
            ("pdf_url", "VARCHAR(500)"),
            ("folder_url", "VARCHAR(500)")
        ]
        
        logger.info("🛠️ Sincronizando tabela 'products'...")
        for col_name, col_type in products_columns:
            try:
                await conn.execute(text(f"ALTER TABLE products ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                logger.info(f"✅ Coluna '{col_name}' verificada.")
            except Exception as e:
                logger.error(f"❌ Erro em products.{col_name}: {e}")

        # Colunas Leads
        leads_columns = [
            ("reengagement_attempts", "INTEGER DEFAULT 0"),
            ("last_reengagement_at", "TIMESTAMP WITH TIME ZONE"),
            ("reengagement_status", "VARCHAR(20) DEFAULT 'none'"),
            ("last_activity_at", "TIMESTAMP WITH TIME ZONE")
        ]
        
        logger.info("🛠️ Sincronizando tabela 'leads'...")
        for col_name, col_type in leads_columns:
            try:
                await conn.execute(text(f"ALTER TABLE leads ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                logger.info(f"✅ Coluna '{col_name}' verificada.")
            except Exception as e:
                logger.error(f"❌ Erro em leads.{col_name}: {e}")

if __name__ == "__main__":
    asyncio.run(sync_db())
