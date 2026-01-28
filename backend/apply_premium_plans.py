#!/usr/bin/env python3
"""
Script para aplicar nova estrutura de planos B2B Premium
========================================================

Este script:
1. Cria/atualiza os 2 planos premium (Professional e Enterprise)
2. Migra clientes do plano Essencial para Professional
3. Remove o plano Essencial

Uso:
    python apply_premium_plans.py
"""

import asyncio
import sys
from pathlib import Path

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from src.domain.entities.plan import Plan
from src.domain.entities.tenant_subscription import TenantSubscription
from src.infrastructure.database import get_database_url


async def apply_premium_plans():
    """Aplica nova estrutura de planos B2B Premium"""
    
    # Conectar ao banco
    database_url = get_database_url()
    engine = create_async_engine(database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("\n🚀 Iniciando migração para planos B2B Premium...\n")
        
        # ====================================================================
        # 1. CRIAR/ATUALIZAR PLANO PROFESSIONAL
        # ====================================================================
        
        print("📝 Atualizando plano Professional...")
        
        result = await session.execute(
            select(Plan).where(Plan.slug == "professional")
        )
        professional = result.scalar_one_or_none()
        
        professional_data = {
            "name": "Professional",
            "description": "Tudo que você precisa para crescer",
            "price_monthly": 897.00,
            "price_yearly": 8970.00,
            "sort_order": 1,
            "is_featured": True,
            "active": True,
            "limits": {
                "leads_per_month": 2000,
                "messages_per_month": 20000,
                "sellers": 15,
                "ai_tokens_per_month": 1000000,
            },
            "features": {
                # Core Business
                "ai_qualification": True,
                "whatsapp_integration": True,
                "web_chat": True,
                "messenger_integration": True,
                "push_notifications": True,
                "templates_enabled": True,
                "notes_enabled": True,
                "attachments_enabled": True,
                "search_enabled": True,
                "sse_enabled": True,
                
                # Agendamento Assistido
                "calendar_enabled": True,
                "calendar_integration": True,
                "appointment_booking": True,
                "appointment_mode": "assisted",
                
                # Analytics & IA
                "metrics_enabled": True,
                "reports_enabled": True,
                "basic_reports": True,
                "advanced_reports": True,
                "lead_export": True,
                "archive_enabled": True,
                "reengagement_enabled": True,
                "reengagement_limit": 1,
                "voice_response_enabled": True,
                "semantic_search": True,
                
                # Desabilitado (Enterprise only)
                "ai_guard_enabled": False,
                "knowledge_base_enabled": False,
                "copilot_enabled": False,
                "ai_sentiment_alerts_enabled": False,
                "ai_auto_handoff_enabled": False,
                "api_access_enabled": False,
                "webhooks": False,
                "white_label": False,
                "custom_integrations": False,
                "priority_support": False,
                "account_manager": False,
                "sla_99_5": False,
                "sso_enabled": False,
                "security_ghost_mode_enabled": False,
                "distrib_auto_assign_enabled": False,
                "audit_log_enabled": False,
                "auto_backup": False,
            },
        }
        
        if professional:
            # Atualizar existente
            for key, value in professional_data.items():
                setattr(professional, key, value)
            print("✅ Plano Professional atualizado")
        else:
            # Criar novo
            professional = Plan(slug="professional", **professional_data)
            session.add(professional)
            print("✅ Plano Professional criado")
        
        await session.flush()
        
        # ====================================================================
        # 2. CRIAR/ATUALIZAR PLANO ENTERPRISE
        # ====================================================================
        
        print("\n📝 Atualizando plano Enterprise...")
        
        result = await session.execute(
            select(Plan).where(Plan.slug == "enterprise")
        )
        enterprise = result.scalar_one_or_none()
        
        enterprise_data = {
            "name": "Enterprise",
            "description": "Liberdade total + Máxima automação",
            "price_monthly": 1997.00,
            "price_yearly": 19970.00,
            "sort_order": 2,
            "is_featured": False,
            "active": True,
            "limits": {
                "leads_per_month": -1,  # Ilimitado
                "messages_per_month": -1,  # Ilimitado
                "sellers": -1,  # Ilimitado
                "ai_tokens_per_month": 3000000,
            },
            "features": {
                # Core Business
                "ai_qualification": True,
                "whatsapp_integration": True,
                "web_chat": True,
                "messenger_integration": True,
                "push_notifications": True,
                "templates_enabled": True,
                "notes_enabled": True,
                "attachments_enabled": True,
                "search_enabled": True,
                "sse_enabled": True,
                
                # Agendamento AUTOMÁTICO
                "calendar_enabled": True,
                "calendar_integration": True,
                "appointment_booking": True,
                "appointment_mode": "automatic",
                "appointment_auto_create": True,
                "appointment_reminders": True,
                "calendar_email_invites": True,
                "appointment_rescheduling": True,
                
                # Analytics & IA Avançada
                "metrics_enabled": True,
                "reports_enabled": True,
                "basic_reports": True,
                "advanced_reports": True,
                "lead_export": True,
                "archive_enabled": True,
                "reengagement_enabled": True,
                "reengagement_limit": -1,  # Ilimitado
                "voice_response_enabled": True,
                "semantic_search": True,
                
                # IA Enterprise
                "ai_guard_enabled": True,
                "knowledge_base_enabled": True,
                "copilot_enabled": True,
                "ai_sentiment_alerts_enabled": True,
                "ai_auto_handoff_enabled": True,
                
                # Integrações
                "api_access_enabled": True,
                "webhooks": True,
                "white_label": True,
                "custom_integrations": True,
                "sso_enabled": True,
                
                # Governança & Segurança
                "security_ghost_mode_enabled": True,
                "security_export_lock_enabled": False,
                "distrib_auto_assign_enabled": True,
                "audit_log_enabled": True,
                "auto_backup": True,
                
                # Suporte VIP
                "priority_support": True,
                "account_manager": True,
                "sla_99_5": True,
            },
        }
        
        if enterprise:
            # Atualizar existente
            for key, value in enterprise_data.items():
                setattr(enterprise, key, value)
            print("✅ Plano Enterprise atualizado")
        else:
            # Criar novo
            enterprise = Plan(slug="enterprise", **enterprise_data)
            session.add(enterprise)
            print("✅ Plano Enterprise criado")
        
        await session.flush()
        
        # ====================================================================
        # 3. MIGRAR CLIENTES DO PLANO ESSENCIAL PARA PROFESSIONAL
        # ====================================================================
        
        print("\n📝 Migrando clientes do plano Essencial...")
        
        result = await session.execute(
            select(Plan).where(Plan.slug == "essencial")
        )
        essencial = result.scalar_one_or_none()
        
        if essencial:
            # Buscar assinaturas do plano Essencial
            result = await session.execute(
                select(TenantSubscription).where(TenantSubscription.plan_id == essencial.id)
            )
            subscriptions = result.scalars().all()
            
            if subscriptions:
                # Migrar para Professional
                for sub in subscriptions:
                    sub.plan_id = professional.id
                
                print(f"✅ {len(subscriptions)} clientes migrados de Essencial para Professional")
            else:
                print("ℹ️  Nenhum cliente no plano Essencial")
            
            # Deletar plano Essencial
            await session.delete(essencial)
            print("✅ Plano Essencial removido")
        else:
            print("ℹ️  Plano Essencial não encontrado (já foi removido)")
        
        # ====================================================================
        # 4. COMMIT
        # ====================================================================
        
        await session.commit()
        
        print("\n" + "="*60)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*60)
        print("\n📊 Resumo:")
        print(f"  • Plano Professional: R$ 897/mês (2.000 leads, 15 corretores)")
        print(f"  • Plano Enterprise: R$ 1.997/mês (ilimitado)")
        print(f"  • Plano Essencial: REMOVIDO")
        print("\n")


if __name__ == "__main__":
    asyncio.run(apply_premium_plans())
