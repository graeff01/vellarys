import asyncio
import os
from sqlalchemy import text
from src.infrastructure.database import async_session, engine

async def fix_database():
    print("🚀 Iniciando correção do banco de dados...")
    
    async with async_session() as session:
        try:
            # 1. Adicionar coluna propensity_score na tabela leads
            print("🔧 Adicionando coluna 'propensity_score' à tabela 'leads'...")
            # Usamos try/except para o caso da coluna já existir
            await session.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS propensity_score INTEGER DEFAULT 0"))
            
            # 2. Garantir que outras tabelas novas existam (caso o create_all do main não tenha rodado)
            # O main.py já chama init_db() que faz create_all
            
            await session.commit()
            print("✅ Coluna 'propensity_score' adicionada com sucesso!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Erro ao atualizar banco: {e}")
            
    await engine.dispose()

if __name__ == "__main__":
    # Carrega env se necessário (src.config já faz isso)
    asyncio.run(fix_database())
