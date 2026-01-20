"""
ROTAS: DATA SOURCES (Fontes de Dados)
=====================================

CRUD para gerenciar fontes de dados configuráveis por tenant.
Permite que cada cliente configure de onde a IA busca informações.
"""

import logging
from typing import Optional, List, Any, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from slugify import slugify
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.infrastructure.database import get_db
from src.domain.entities import User, Tenant, DataSource, DataSourceType
from src.api.dependencies import get_current_user, get_current_tenant
from src.infrastructure.services.encryption_service import (
    encrypt_credentials,
    decrypt_credentials,
    mask_credentials,
)
from src.infrastructure.data_sources import DataSourceFactory, DataSourceConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-sources", tags=["Data Sources"])


# ==========================================
# SCHEMAS (Pydantic)
# ==========================================

class DataSourceCreate(BaseModel):
    """Schema para criar uma fonte de dados."""
    name: str = Field(..., min_length=2, max_length=200)
    type: str = Field(..., pattern="^(portal_api|custom_api|webhook|manual)$")
    description: Optional[str] = None
    active: bool = True
    priority: int = Field(default=0, ge=0, le=100)
    config: Dict[str, Any] = Field(default_factory=dict)
    credentials: Optional[Dict[str, Any]] = None
    field_mapping: Optional[Dict[str, str]] = None
    cache_ttl_seconds: int = Field(default=300, ge=0, le=86400)
    cache_strategy: str = Field(default="memory", pattern="^(memory|redis|none)$")


class DataSourceUpdate(BaseModel):
    """Schema para atualizar uma fonte de dados."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    config: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None
    field_mapping: Optional[Dict[str, str]] = None
    cache_ttl_seconds: Optional[int] = Field(None, ge=0, le=86400)
    cache_strategy: Optional[str] = Field(None, pattern="^(memory|redis|none)$")


class DataSourceResponse(BaseModel):
    """Schema de resposta."""
    id: int
    tenant_id: int
    name: str
    slug: str
    description: Optional[str]
    type: str
    active: bool
    priority: int
    config: Dict[str, Any]
    has_credentials: bool
    field_mapping: Optional[Dict[str, str]]
    cache_ttl_seconds: int
    cache_strategy: str
    last_sync_at: Optional[datetime]
    last_sync_status: Optional[str]
    last_sync_count: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DataSourceTestResult(BaseModel):
    """Resultado do teste de conexão."""
    success: bool
    message: str
    details: Dict[str, Any]


class DataSourceSyncResult(BaseModel):
    """Resultado da sincronização."""
    success: bool
    count: int
    errors: List[Dict[str, Any]]


# ==========================================
# HELPERS
# ==========================================

def source_to_response(source: DataSource) -> Dict[str, Any]:
    """Converte DataSource para response dict."""
    return {
        "id": source.id,
        "tenant_id": source.tenant_id,
        "name": source.name,
        "slug": source.slug,
        "description": source.description,
        "type": source.type,
        "active": source.active,
        "priority": source.priority,
        "config": source.config or {},
        "has_credentials": bool(source.credentials_encrypted),
        "field_mapping": source.field_mapping,
        "cache_ttl_seconds": source.cache_ttl_seconds,
        "cache_strategy": source.cache_strategy,
        "last_sync_at": source.last_sync_at,
        "last_sync_status": source.last_sync_status,
        "last_sync_count": source.last_sync_count,
        "last_error": source.last_error,
        "created_at": source.created_at,
        "updated_at": source.updated_at,
    }


# ==========================================
# ENDPOINTS: TIPOS
# ==========================================

@router.get("/types")
async def list_data_source_types():
    """
    Lista tipos de data source disponíveis.

    Retorna informações sobre cada tipo suportado.
    """
    return {
        "types": [
            {
                "id": "portal_api",
                "name": "Portal API",
                "description": "API JSON de portal imobiliário (ex: portalinvestimento.com)",
                "icon": "globe",
                "config_fields": ["base_url", "regions", "url_pattern", "timeout", "fallback_file"],
            },
            {
                "id": "custom_api",
                "name": "API Personalizada",
                "description": "Qualquer API REST com autenticação configurável",
                "icon": "code",
                "config_fields": ["endpoint", "method", "auth_type", "response_path", "code_field"],
            },
            {
                "id": "webhook",
                "name": "Webhook",
                "description": "Recebe dados via POST do sistema do cliente",
                "icon": "webhook",
                "config_fields": ["secret_key", "expected_format"],
            },
            {
                "id": "manual",
                "name": "Manual",
                "description": "Usa apenas produtos cadastrados no sistema",
                "icon": "database",
                "config_fields": [],
            },
        ]
    }


# ==========================================
# ENDPOINTS: CRUD
# ==========================================

@router.get("")
async def list_data_sources(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    active_only: bool = False,
):
    """
    Lista todas as fontes de dados do tenant.
    """
    query = select(DataSource).where(DataSource.tenant_id == tenant.id)

    if active_only:
        query = query.where(DataSource.active == True)

    query = query.order_by(DataSource.priority.desc(), DataSource.name)

    result = await db.execute(query)
    sources = result.scalars().all()

    return {
        "data_sources": [source_to_response(s) for s in sources],
        "total": len(sources)
    }


@router.post("")
async def create_data_source(
    payload: DataSourceCreate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Cria uma nova fonte de dados.
    """
    # Gera slug
    slug = slugify(payload.name)

    # Verifica duplicata
    existing = await db.execute(
        select(DataSource)
        .where(DataSource.tenant_id == tenant.id)
        .where(DataSource.slug == slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Já existe uma fonte de dados com este nome"
        )

    # Criptografa credenciais se fornecidas
    encrypted_creds = None
    if payload.credentials:
        encrypted_creds = encrypt_credentials(payload.credentials)

    # Cria fonte
    source = DataSource(
        tenant_id=tenant.id,
        name=payload.name,
        slug=slug,
        description=payload.description,
        type=payload.type,
        active=payload.active,
        priority=payload.priority,
        config=payload.config,
        credentials_encrypted=encrypted_creds,
        field_mapping=payload.field_mapping,
        cache_ttl_seconds=payload.cache_ttl_seconds,
        cache_strategy=payload.cache_strategy,
    )

    db.add(source)
    await db.commit()
    await db.refresh(source)

    logger.info(
        f"[DataSource] Criado: {source.id} ({source.type}) "
        f"para tenant {tenant.id}"
    )

    return {
        "success": True,
        "data_source": source_to_response(source)
    }


@router.get("/{source_id}")
async def get_data_source(
    source_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtém detalhes de uma fonte de dados.
    """
    result = await db.execute(
        select(DataSource)
        .where(DataSource.id == source_id)
        .where(DataSource.tenant_id == tenant.id)
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Fonte de dados não encontrada")

    return source_to_response(source)


@router.patch("/{source_id}")
async def update_data_source(
    source_id: int,
    payload: DataSourceUpdate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza uma fonte de dados.
    """
    result = await db.execute(
        select(DataSource)
        .where(DataSource.id == source_id)
        .where(DataSource.tenant_id == tenant.id)
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Fonte de dados não encontrada")

    # Atualiza campos
    update_data = payload.model_dump(exclude_unset=True)

    # Trata credenciais separadamente
    if "credentials" in update_data:
        creds = update_data.pop("credentials")
        if creds:
            source.credentials_encrypted = encrypt_credentials(creds)
        else:
            source.credentials_encrypted = None
        flag_modified(source, "credentials_encrypted")

    # Atualiza outros campos
    for key, value in update_data.items():
        if hasattr(source, key):
            setattr(source, key, value)

    # Marca config como modificado se foi alterado
    if "config" in update_data:
        flag_modified(source, "config")
    if "field_mapping" in update_data:
        flag_modified(source, "field_mapping")

    # Limpa cache do factory
    DataSourceFactory.clear_cache(source_id)

    await db.commit()
    await db.refresh(source)

    logger.info(f"[DataSource] Atualizado: {source.id}")

    return {
        "success": True,
        "data_source": source_to_response(source)
    }


@router.delete("/{source_id}")
async def delete_data_source(
    source_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove uma fonte de dados.
    """
    result = await db.execute(
        select(DataSource)
        .where(DataSource.id == source_id)
        .where(DataSource.tenant_id == tenant.id)
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Fonte de dados não encontrada")

    await db.delete(source)
    await db.commit()

    # Limpa cache
    DataSourceFactory.clear_cache(source_id)

    logger.info(f"[DataSource] Removido: {source_id}")

    return {"success": True, "message": "Fonte de dados removida"}


# ==========================================
# ENDPOINTS: OPERAÇÕES
# ==========================================

@router.post("/{source_id}/test")
async def test_data_source(
    source_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Testa conexão com a fonte de dados.
    """
    result = await db.execute(
        select(DataSource)
        .where(DataSource.id == source_id)
        .where(DataSource.tenant_id == tenant.id)
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Fonte de dados não encontrada")

    # Descriptografa credenciais
    credentials = {}
    if source.credentials_encrypted:
        credentials = decrypt_credentials(source.credentials_encrypted)

    # Cria config
    config = DataSourceConfig(
        source_id=source.id,
        tenant_id=source.tenant_id,
        type=source.type,
        config=source.config or {},
        credentials=credentials,
        field_mapping=source.field_mapping or {},
        cache_ttl=source.cache_ttl_seconds,
    )

    try:
        # Obtém provider (força nova instância)
        provider = DataSourceFactory.get_provider(config, force_new=True)

        # Se for manual, injeta sessão de banco
        if source.type == "manual":
            provider.set_db_session(db)

        # Testa conexão
        test_result = await provider.test_connection()

        return DataSourceTestResult(**test_result)

    except Exception as e:
        logger.error(f"[DataSource] Erro no teste: {e}")
        return DataSourceTestResult(
            success=False,
            message=str(e),
            details={}
        )


@router.post("/{source_id}/sync")
async def sync_data_source(
    source_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Inicia sincronização da fonte de dados (em background).
    """
    result = await db.execute(
        select(DataSource)
        .where(DataSource.id == source_id)
        .where(DataSource.tenant_id == tenant.id)
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Fonte de dados não encontrada")

    # Adiciona task em background
    background_tasks.add_task(
        run_data_source_sync,
        source_id=source.id,
        tenant_id=tenant.id,
    )

    return {
        "success": True,
        "message": "Sincronização iniciada em segundo plano",
        "source_id": source.id
    }


async def run_data_source_sync(source_id: int, tenant_id: int):
    """
    Task de background para sincronizar data source.
    """
    from src.infrastructure.database import async_session_factory

    logger.info(f"[DataSource] Iniciando sync: {source_id}")

    async with async_session_factory() as db:
        try:
            # Busca source
            result = await db.execute(
                select(DataSource).where(DataSource.id == source_id)
            )
            source = result.scalar_one_or_none()

            if not source:
                logger.error(f"[DataSource] Source não encontrado: {source_id}")
                return

            # Descriptografa credenciais
            credentials = {}
            if source.credentials_encrypted:
                credentials = decrypt_credentials(source.credentials_encrypted)

            # Cria config
            config = DataSourceConfig(
                source_id=source.id,
                tenant_id=source.tenant_id,
                type=source.type,
                config=source.config or {},
                credentials=credentials,
                field_mapping=source.field_mapping or {},
                cache_ttl=source.cache_ttl_seconds,
            )

            # Obtém provider
            provider = DataSourceFactory.get_provider(config, force_new=True)

            # Se for manual, injeta sessão
            if source.type == "manual":
                provider.set_db_session(db)

            # Executa sync
            sync_result = await provider.sync_all()

            # Atualiza status
            source.last_sync_at = datetime.utcnow()
            source.last_sync_status = "success" if sync_result["success"] else "failed"
            source.last_sync_count = sync_result.get("count", 0)
            source.last_error = None if sync_result["success"] else str(sync_result.get("errors", []))

            flag_modified(source, "last_sync_at")
            await db.commit()

            logger.info(
                f"[DataSource] Sync concluído: {source_id}, "
                f"count={sync_result.get('count', 0)}"
            )

        except Exception as e:
            logger.error(f"[DataSource] Erro no sync: {e}")

            # Atualiza status de erro
            try:
                result = await db.execute(
                    select(DataSource).where(DataSource.id == source_id)
                )
                source = result.scalar_one_or_none()
                if source:
                    source.last_sync_at = datetime.utcnow()
                    source.last_sync_status = "failed"
                    source.last_error = str(e)
                    await db.commit()
            except:
                pass


# ==========================================
# ENDPOINT: LOOKUP (para debug/teste)
# ==========================================

@router.get("/{source_id}/lookup/{code}")
async def lookup_property(
    source_id: int,
    code: str,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Busca um imóvel/produto pelo código usando uma fonte específica.

    Útil para debug e teste de configurações.
    """
    result = await db.execute(
        select(DataSource)
        .where(DataSource.id == source_id)
        .where(DataSource.tenant_id == tenant.id)
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Fonte de dados não encontrada")

    # Descriptografa credenciais
    credentials = {}
    if source.credentials_encrypted:
        credentials = decrypt_credentials(source.credentials_encrypted)

    # Cria config
    config = DataSourceConfig(
        source_id=source.id,
        tenant_id=source.tenant_id,
        type=source.type,
        config=source.config or {},
        credentials=credentials,
        field_mapping=source.field_mapping or {},
        cache_ttl=source.cache_ttl_seconds,
    )

    try:
        provider = DataSourceFactory.get_provider(config)

        if source.type == "manual":
            provider.set_db_session(db)

        property_result = await provider.lookup_by_code(code)

        if property_result:
            return {
                "success": True,
                "property": {
                    "code": property_result.code,
                    "title": property_result.title,
                    "type": property_result.type,
                    "region": property_result.region,
                    "price": property_result.price_formatted,
                    "bedrooms": property_result.bedrooms,
                    "bathrooms": property_result.bathrooms,
                    "parking": property_result.parking,
                    "area": property_result.area,
                    "description": property_result.description,
                    "link": property_result.link,
                }
            }
        else:
            return {
                "success": False,
                "message": f"Código {code} não encontrado"
            }

    except Exception as e:
        logger.error(f"[DataSource] Erro no lookup: {e}")
        return {
            "success": False,
            "message": str(e)
        }
