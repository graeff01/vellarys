import pytest
import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.base import Base
from tests.utils import engine, TestingSessionLocal

@pytest.fixture(scope="session")
def event_loop():
    """
    Cria uma instância do event loop para todo o escopo da sessão de testes.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def create_test_tables():
    """
    Fixture para criar as tabelas no banco de dados de teste antes dos testes
    e removê-las depois. O `autouse=True` garante que será executado automaticamente.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield  # Aqui é onde os testes rodam

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture que fornece uma sessão de banco de dados limpa para cada teste.
    """
    async with TestingSessionLocal() as session:
        yield session
