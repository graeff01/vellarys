import asyncio
import sys
import os

# Adiciona o diretório backend ao path para os imports funcionarem
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from src.config import get_settings
from src.domain.entities import Tenant
from src.infrastructure.services.morning_briefing_service import MorningBriefingService

settings = get_settings()

async def test_email_briefing(target_email: str):
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Busca o primeiro tenant disponível
        result = await session.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print("❌ Erro: Nenhum Tenant encontrado no banco de dados.")
            return

        print(f"✅ Tenant encontrado: {tenant.name} ({tenant.slug})")
        print(f"🚀 Disparando briefing para: {target_email}...")

        # 2. Instancia o serviço e envia
        try:
            service = MorningBriefingService(session, tenant)
            await service.generate_and_send(target_email)
            print(f"🎉 Sucesso! Email enviado para {target_email}")
        except Exception as e:
            print(f"❌ Falha ao enviar email: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    email = "douglasggraeff@icloud.com"
    if len(sys.argv) > 1:
        email = sys.argv[1]
    
    asyncio.run(test_email_briefing(email))
