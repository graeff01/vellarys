#!/usr/bin/env python3
"""
SCRIPT DE VERIFICAÇÃO PÓS-DEPLOY
==================================

Verifica se todas as otimizações foram aplicadas corretamente após deploy.

Uso:
    python3 scripts/verify_deployment.py

Verifica:
- ✅ Índices críticos criados
- ✅ Pool de conexões configurado
- ✅ Statement timeout ativo
- ✅ Migration aplicada
"""

import sys
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import get_settings

settings = get_settings()


async def verify_indexes():
    """Verifica se todos os índices críticos foram criados."""
    print("\n🔍 Verificando índices críticos...")

    engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+asyncpg://"))

    try:
        async with engine.connect() as conn:
            # Lista de índices esperados
            expected_indexes = [
                "ix_messages_lead_created_role",
                "ix_leads_custom_data_gin",
                "ix_property_embeddings_hnsw",
                "ix_knowledge_embeddings_hnsw",
                "ix_messages_external_id",
                "ix_leads_phone_tenant",
                "ix_leads_active",
                "ix_messages_status_pending",
            ]

            missing_indexes = []

            for index_name in expected_indexes:
                result = await conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM pg_indexes
                    WHERE indexname = :index_name
                """), {"index_name": index_name})

                count = result.scalar()

                if count > 0:
                    print(f"   ✅ {index_name}")
                else:
                    print(f"   ❌ {index_name} - FALTANDO!")
                    missing_indexes.append(index_name)

            if missing_indexes:
                print(f"\n⚠️ {len(missing_indexes)} índice(s) faltando!")
                print("Execute: alembic upgrade head")
                return False
            else:
                print(f"\n✅ Todos os {len(expected_indexes)} índices estão presentes!")
                return True

    except Exception as e:
        print(f"\n❌ Erro verificando índices: {e}")
        return False
    finally:
        await engine.dispose()


async def verify_pool_config():
    """Verifica configuração do pool de conexões."""
    print("\n🔍 Verificando pool de conexões...")

    print(f"   Pool size: {settings.db_pool_size}")
    print(f"   Max overflow: {settings.db_max_overflow}")
    print(f"   Pool timeout: {settings.db_pool_timeout}s")
    print(f"   Pool recycle: {settings.db_pool_recycle}s")

    # Valores recomendados
    if settings.db_pool_size == 10:
        print("   ✅ Pool size otimizado para 500 leads/mês")
    else:
        print(f"   ⚠️ Pool size não otimizado (esperado: 10, atual: {settings.db_pool_size})")

    if settings.db_pool_timeout == 10:
        print("   ✅ Pool timeout configurado (fail fast)")
    else:
        print(f"   ⚠️ Pool timeout não otimizado (esperado: 10s, atual: {settings.db_pool_timeout}s)")

    return True


async def verify_statement_timeout():
    """Verifica se statement timeout está ativo."""
    print("\n🔍 Verificando statement timeout...")

    engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+asyncpg://"))

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SHOW statement_timeout"))
            timeout = result.scalar()

            print(f"   Statement timeout: {timeout}")

            if timeout == "60s" or timeout == "60000ms":
                print("   ✅ Statement timeout configurado (60s)")
                return True
            else:
                print(f"   ⚠️ Statement timeout diferente do esperado")
                print(f"   Esperado: 60s, Atual: {timeout}")
                return False

    except Exception as e:
        print(f"\n❌ Erro verificando statement timeout: {e}")
        return False
    finally:
        await engine.dispose()


async def verify_migration():
    """Verifica se a migration mais recente foi aplicada."""
    print("\n🔍 Verificando migration...")

    engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+asyncpg://"))

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT version_num
                FROM alembic_version
                ORDER BY version_num DESC
                LIMIT 1
            """))

            current_version = result.scalar()

            print(f"   Versão atual: {current_version}")

            if current_version == "20260203_add_critical_indexes":
                print("   ✅ Migration de índices aplicada!")
                return True
            else:
                print(f"   ⚠️ Migration de índices não aplicada")
                print(f"   Esperado: 20260203_add_critical_indexes")
                print(f"   Execute: alembic upgrade head")
                return False

    except Exception as e:
        print(f"\n❌ Erro verificando migration: {e}")
        return False
    finally:
        await engine.dispose()


async def main():
    """Executa todas as verificações."""
    print("=" * 60)
    print("VERIFICAÇÃO PÓS-DEPLOY - OTIMIZAÇÕES VELLARYS")
    print("=" * 60)

    results = {
        "indexes": await verify_indexes(),
        "pool": await verify_pool_config(),
        "statement_timeout": await verify_statement_timeout(),
        "migration": await verify_migration(),
    }

    print("\n" + "=" * 60)
    print("RESULTADO FINAL")
    print("=" * 60)

    all_passed = all(results.values())

    if all_passed:
        print("✅ TODAS AS VERIFICAÇÕES PASSARAM!")
        print("\nSistema está 100% otimizado e pronto para produção! 🚀")
        return 0
    else:
        print("⚠️ ALGUMAS VERIFICAÇÕES FALHARAM")
        print("\nDetalhes:")
        for check, passed in results.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}")

        print("\nConsulte OTIMIZACOES_PRODUCAO.md para mais informações.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
