from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

# URL do banco de dados de teste, lida a partir das variáveis de ambiente
TEST_DATABASE_URL = os.environ.get("DATABASE_URL")

# Cria a engine do banco de dados de teste
engine = create_async_engine(TEST_DATABASE_URL, echo=True)

# Cria uma sessionmaker para o banco de teste
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependência que fornece uma sessão de banco de dados para os testes.
    """
    async with TestingSessionLocal() as session:
        yield session

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Override da dependência get_db para ser usada nos testes, garantindo
    que a sessão de teste seja usada pela aplicação.
    """
    async with TestingSessionLocal() as session:
        yield session
