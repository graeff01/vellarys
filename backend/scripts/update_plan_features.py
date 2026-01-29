#!/usr/bin/env python3
"""
Script para atualizar features dos planos com as novas funcionalidades.

Adiciona:
- copilot_enabled (apenas Premium/Enterprise)
- simulator_enabled (todos os planos)
- reports_enabled (todos os planos)
- export_enabled (todos os planos)
"""

import asyncio
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.domain.entities.plan import Plan

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL não configurado")
    sys.exit(1)

# Converter postgresql:// para postgresql+asyncpg://
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def update_plan_features():
    """Atualiza features dos planos."""

    print("\n" + "="*80)
    print("🔧 ATUALIZAÇÃO DE FEATURES DOS PLANOS")
    print("="*80)

    async with AsyncSessionLocal() as session:
        # Buscar todos os planos
        stmt = select(Plan)
        result = await session.execute(stmt)
        plans = result.scalars().all()

        if not plans:
            print("⚠️  Nenhum plano encontrado")
            return

        print(f"\n📋 Encontrados {len(plans)} planos")

        for plan in plans:
            print(f"\n🔍 Processando plano: {plan.name} (ID: {plan.id})")

            # Buscar features atuais (JSONB)
            current_features = plan.features or {}
            updated = False

            # Features que TODOS os planos devem ter
            all_plans_features = {
                "simulator_enabled": True,
                "reports_enabled": True,
                "export_enabled": True,
            }

            # Features apenas para Premium/Enterprise
            premium_features = {
                "copilot_enabled": True,
            }

            # Adicionar features para todos os planos
            for key, value in all_plans_features.items():
                if key not in current_features:
                    current_features[key] = value
                    print(f"   ✅ Adicionado: {key} = {value}")
                    updated = True

            # Adicionar copilot apenas para Premium/Enterprise
            is_premium = plan.name.lower() in ['premium', 'enterprise', 'vellarys premium']
            if is_premium:
                for key, value in premium_features.items():
                    if key not in current_features:
                        current_features[key] = value
                        print(f"   ✅ Adicionado: {key} = {value} (plano premium)")
                        updated = True
            else:
                # Garantir que Starter NÃO tem copilot
                if 'copilot_enabled' not in current_features:
                    current_features['copilot_enabled'] = False
                    print(f"   ℹ️  Adicionado: copilot_enabled = False (plano básico)")
                    updated = True

            # Desbloquear export (remover lock)
            if current_features.get('security_export_lock_enabled', False):
                current_features['security_export_lock_enabled'] = False
                print(f"   🔓 Desbloqueado: security_export_lock_enabled = False")
                updated = True

            if updated:
                plan.features = current_features
                session.add(plan)
                print(f"   💾 Salvando alterações...")
            else:
                print(f"   ✅ Plano já está atualizado")

        await session.commit()
        print("\n" + "="*80)
        print("✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*80)

        # Mostrar resumo
        print("\n📊 RESUMO DAS FEATURES POR PLANO:")
        for plan in plans:
            print(f"\n   {plan.name}:")
            features = plan.features or {}
            print(f"      - simulator_enabled: {features.get('simulator_enabled', False)}")
            print(f"      - copilot_enabled: {features.get('copilot_enabled', False)}")
            print(f"      - reports_enabled: {features.get('reports_enabled', False)}")
            print(f"      - export_enabled: {features.get('export_enabled', False)}")
            print(f"      - export_lock: {features.get('security_export_lock_enabled', False)}")


async def main():
    try:
        await update_plan_features()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
