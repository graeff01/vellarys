import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Lead, Tenant, User
from src.api.main import app
from src.infrastructure.database import get_db, Base
from tests.utils import get_test_db, override_get_db

# Aplica o override do banco de dados para o ambiente de teste
app.dependency_overrides[get_db] = override_get_db

# Fixture para criar um cliente HTTP assíncrono para a API
@pytest.fixture
async def async_client() -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

# Fixture para criar um tenant e um usuário admin para os testes
@pytest.fixture(scope="function")
async def setup_tenant_and_user(async_client: AsyncClient):
    # Cria o tenant
    tenant_response = await async_client.post("/api/v1/tenants", json={
        "name": "Test Tenant",
        "slug": "test-tenant-leads"
    })
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    # Cria o usuário admin
    user_response = await async_client.post(f"/api/v1/tenants/{tenant_id}/users", json={
        "name": "Admin User",
        "email": "admin@test.com",
        "password": "password123",
        "role": "admin"
    })
    assert user_response.status_code == 201

    # Faz o login para obter o token
    login_response = await async_client.post("/api/v1/auth/token", data={
        "username": "admin@test.com",
        "password": "password123"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    return tenant_id, token

@pytest.mark.asyncio
async def test_create_lead_successfully(async_client: AsyncClient, setup_tenant_and_user):
    """
    Testa a criação de um lead com sucesso através do endpoint /api/v1/leads.
    Verifica se a resposta é 201 e se o lead é salvo corretamente no banco.
    """
    tenant_id, token = setup_tenant_and_user
    headers = {"Authorization": f"Bearer {token}"}

    lead_data = {
        "name": "John Doe",
        "phone": "1234567890",
        "email": "john.doe@example.com",
        "source": "website"
    }

    # 1. Ação: Cria o lead via API
    response = await async_client.post("/api/v1/leads", json=lead_data, headers=headers)

    # 2. Verificação: Resposta da API
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["name"] == lead_data["name"]
    assert response_data["phone"] == lead_data["phone"]
    assert "id" in response_data

    # 3. Verificação: Banco de Dados
    async for db in get_test_db():
        session: AsyncSession = db
        result = await session.execute(select(Lead).where(Lead.id == response_data["id"]))
        created_lead = result.scalars().first()

        assert created_lead is not None
        assert created_lead.name == "John Doe"
        assert created_lead.tenant_id == tenant_id
        assert created_lead.source == "website"
