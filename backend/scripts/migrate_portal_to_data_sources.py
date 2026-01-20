"""
MIGRATION SCRIPT: Portal para Data Sources
==========================================

Este script migra a configuracao hardcoded do portal de investimento
para o novo sistema de Data Sources configuraveis.

Uso:
    cd backend
    python -m scripts.migrate_portal_to_data_sources

O que faz:
1. Para cada tenant do nicho imobiliario:
   - Cria um DataSource tipo 'portal_api' com a config do portal atual
   - Cria um DataSource tipo 'manual' como fallback

2. Para outros tenants:
   - Cria apenas um DataSource tipo 'manual'
"""

import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuracao atual hardcoded (do property_lookup_service.py)
PORTAL_CONFIG = {
    "base_url": "https://portalinvestimento.com",
    "regions": ["canoas", "poa", "sc", "pb"],
    "url_pattern": "/imoveis/{region}/{region}.json",
    "timeout": 5.0,
    "fallback_file": "data/fallback_canoas.json",
}

DEFAULT_FIELD_MAPPING = {
    "codigo": "code",
    "titulo": "title",
    "tipo": "type",
    "regiao": "region",
    "preco": "price",
    "quartos": "bedrooms",
    "banheiros": "bathrooms",
    "vagas": "parking",
    "metragem": "area",
    "descricao": "description",
}

# Nichos que usam o portal de imoveis
REAL_ESTATE_NICHES = [
    "realestate",
    "real_estate",
    "imobiliaria",
    "imobiliario",
    "imoveis",
]


async def migrate():
    """Executa a migracao."""
    from sqlalchemy import select
    from src.infrastructure.database import async_session
    from src.domain.entities import Tenant, DataSource

    logger.info("=" * 60)
    logger.info("INICIANDO MIGRACAO DE PORTAL PARA DATA SOURCES")
    logger.info("=" * 60)

    async with async_session() as db:
        # Busca todos os tenants ativos
        result = await db.execute(
            select(Tenant).where(Tenant.active == True)
        )
        tenants = result.scalars().all()

        logger.info(f"Encontrados {len(tenants)} tenants ativos")

        created_count = 0
        skipped_count = 0

        for tenant in tenants:
            # Verifica se ja tem data sources
            existing = await db.execute(
                select(DataSource).where(DataSource.tenant_id == tenant.id)
            )
            if existing.scalar_one_or_none():
                logger.info(f"[{tenant.slug}] Ja tem data sources - pulando")
                skipped_count += 1
                continue

            # Determina o nicho
            niche = tenant.settings.get("basic", {}).get("niche", "")
            if not niche:
                niche = tenant.settings.get("niche", "services")

            niche_lower = niche.lower().replace("-", "_").replace(" ", "_")
            is_real_estate = niche_lower in REAL_ESTATE_NICHES

            logger.info(f"[{tenant.slug}] Nicho: {niche} (imobiliario: {is_real_estate})")

            # Cria DataSource para nicho imobiliario
            if is_real_estate:
                portal_source = DataSource(
                    tenant_id=tenant.id,
                    name="Portal de Investimento",
                    slug="portal-investimento",
                    description="Portal padrao de imoveis - portalinvestimento.com",
                    type="portal_api",
                    active=True,
                    priority=10,  # Alta prioridade
                    config=PORTAL_CONFIG.copy(),
                    field_mapping=DEFAULT_FIELD_MAPPING.copy(),
                    cache_ttl_seconds=300,
                    cache_strategy="memory",
                )
                db.add(portal_source)
                logger.info(f"  -> Criado DataSource portal_api")

            # Cria DataSource manual como fallback
            manual_source = DataSource(
                tenant_id=tenant.id,
                name="Produtos Locais",
                slug="produtos-locais",
                description="Produtos cadastrados manualmente no sistema",
                type="manual",
                active=True,
                priority=1,  # Baixa prioridade (fallback)
                config={},
                field_mapping=DEFAULT_FIELD_MAPPING.copy(),
                cache_ttl_seconds=60,
                cache_strategy="none",
            )
            db.add(manual_source)
            logger.info(f"  -> Criado DataSource manual (fallback)")

            created_count += 1

        await db.commit()

        logger.info("")
        logger.info("=" * 60)
        logger.info("MIGRACAO CONCLUIDA!")
        logger.info(f"  Tenants processados: {created_count}")
        logger.info(f"  Tenants pulados (ja tinham): {skipped_count}")
        logger.info("=" * 60)


async def rollback():
    """Remove todos os data sources criados pela migracao."""
    from sqlalchemy import select, delete
    from src.infrastructure.database import async_session
    from src.domain.entities import DataSource

    logger.info("ROLLBACK: Removendo data sources...")

    async with async_session() as db:
        # Remove todos os data sources com slugs conhecidos
        result = await db.execute(
            delete(DataSource).where(
                DataSource.slug.in_(["portal-investimento", "produtos-locais"])
            )
        )

        await db.commit()
        logger.info(f"Removidos {result.rowcount} data sources")


async def status():
    """Mostra status dos data sources existentes."""
    from sqlalchemy import select, func
    from src.infrastructure.database import async_session
    from src.domain.entities import Tenant, DataSource

    logger.info("STATUS DOS DATA SOURCES:")
    logger.info("-" * 40)

    async with async_session() as db:
        # Total de tenants
        result = await db.execute(select(func.count(Tenant.id)))
        total_tenants = result.scalar()

        # Tenants com data sources
        result = await db.execute(
            select(func.count(func.distinct(DataSource.tenant_id)))
        )
        tenants_with_sources = result.scalar()

        # Total de data sources
        result = await db.execute(select(func.count(DataSource.id)))
        total_sources = result.scalar()

        # Por tipo
        result = await db.execute(
            select(DataSource.type, func.count(DataSource.id))
            .group_by(DataSource.type)
        )
        by_type = dict(result.fetchall())

        logger.info(f"Total de tenants: {total_tenants}")
        logger.info(f"Tenants com data sources: {tenants_with_sources}")
        logger.info(f"Total de data sources: {total_sources}")
        logger.info(f"Por tipo: {by_type}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "rollback":
            asyncio.run(rollback())
        elif command == "status":
            asyncio.run(status())
        else:
            print(f"Comando desconhecido: {command}")
            print("Uso: python -m scripts.migrate_portal_to_data_sources [migrate|rollback|status]")
    else:
        asyncio.run(migrate())
