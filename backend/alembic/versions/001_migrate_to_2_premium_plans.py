"""
Migration: Reestruturação para 2 Planos B2B Premium
====================================================

Remove plano "Essencial" e atualiza Professional/Enterprise
com novos valores e features.

Revision ID: migrate_to_2_premium_plans
Revises: 
Create Date: 2026-01-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'migrate_to_2_premium_plans'
down_revision = None  # Ajustar para a última migration
branch_labels = None
depends_on = None


def upgrade():
    """
    1. Atualiza planos existentes (Professional e Enterprise)
    2. Migra clientes do plano "Essencial" para "Professional"
    3. Deleta plano "Essencial"
    """
    
    # Conectar ao banco
    conn = op.get_bind()
    
    # ========================================================================
    # 1. ATUALIZAR PLANO PROFESSIONAL
    # ========================================================================
    
    professional_features = {
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
    }
    
    professional_limits = {
        "leads_per_month": 2000,
        "messages_per_month": 20000,
        "sellers": 15,
        "ai_tokens_per_month": 1000000,
    }
    
    conn.execute(
        sa.text("""
            UPDATE plans 
            SET 
                name = 'Professional',
                description = 'Tudo que você precisa para crescer',
                price_monthly = 897.00,
                price_yearly = 8970.00,
                limits = :limits,
                features = :features,
                sort_order = 1,
                is_featured = true,
                updated_at = :updated_at
            WHERE slug = 'professional'
        """),
        {
            "limits": sa.JSON(professional_limits),
            "features": sa.JSON(professional_features),
            "updated_at": datetime.utcnow()
        }
    )
    
    # ========================================================================
    # 2. ATUALIZAR PLANO ENTERPRISE
    # ========================================================================
    
    enterprise_features = {
        # Core Business (tudo do Professional)
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
    }
    
    enterprise_limits = {
        "leads_per_month": -1,  # Ilimitado
        "messages_per_month": -1,  # Ilimitado
        "sellers": -1,  # Ilimitado
        "ai_tokens_per_month": 3000000,
    }
    
    conn.execute(
        sa.text("""
            UPDATE plans 
            SET 
                name = 'Enterprise',
                description = 'Liberdade total + Máxima automação',
                price_monthly = 1997.00,
                price_yearly = 19970.00,
                limits = :limits,
                features = :features,
                sort_order = 2,
                is_featured = false,
                updated_at = :updated_at
            WHERE slug = 'enterprise'
        """),
        {
            "limits": sa.JSON(enterprise_limits),
            "features": sa.JSON(enterprise_features),
            "updated_at": datetime.utcnow()
        }
    )
    
    # ========================================================================
    # 3. MIGRAR CLIENTES DO PLANO "ESSENCIAL" PARA "PROFESSIONAL"
    # ========================================================================
    
    # Buscar ID do plano Essencial
    result = conn.execute(
        sa.text("SELECT id FROM plans WHERE slug = 'essencial'")
    )
    essencial_plan = result.fetchone()
    
    if essencial_plan:
        essencial_id = essencial_plan[0]
        
        # Buscar ID do plano Professional
        result = conn.execute(
            sa.text("SELECT id FROM plans WHERE slug = 'professional'")
        )
        professional_plan = result.fetchone()
        
        if professional_plan:
            professional_id = professional_plan[0]
            
            # Migrar assinaturas
            conn.execute(
                sa.text("""
                    UPDATE tenant_subscriptions 
                    SET 
                        plan_id = :new_plan_id,
                        updated_at = :updated_at
                    WHERE plan_id = :old_plan_id
                """),
                {
                    "new_plan_id": professional_id,
                    "old_plan_id": essencial_id,
                    "updated_at": datetime.utcnow()
                }
            )
            
            print(f"✅ Clientes migrados de Essencial para Professional")
        
        # Deletar plano Essencial
        conn.execute(
            sa.text("DELETE FROM plans WHERE slug = 'essencial'")
        )
        print(f"✅ Plano Essencial removido")
    
    print("✅ Migration concluída com sucesso!")


def downgrade():
    """
    Reverte para estrutura de 3 planos (não recomendado)
    """
    
    conn = op.get_bind()
    
    # Recriar plano Essencial
    essencial_features = {
        "ai_qualification": True,
        "whatsapp_integration": True,
        "web_chat": True,
        "push_notifications": True,
        "basic_reports": True,
        "lead_export": True,
        "appointment_booking": False,
        "calendar_integration": False,
    }
    
    essencial_limits = {
        "leads_per_month": 300,
        "messages_per_month": 3000,
        "sellers": 3,
        "ai_tokens_per_month": 150000,
    }
    
    conn.execute(
        sa.text("""
            INSERT INTO plans (slug, name, description, price_monthly, price_yearly, limits, features, sort_order, is_featured, active, created_at, updated_at)
            VALUES ('essencial', 'Essencial', 'Para imobiliárias iniciando com IA', 297.00, 2970.00, :limits, :features, 1, false, true, :created_at, :updated_at)
        """),
        {
            "limits": sa.JSON(essencial_limits),
            "features": sa.JSON(essencial_features),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    )
    
    # Reverter preços do Professional
    conn.execute(
        sa.text("""
            UPDATE plans 
            SET 
                price_monthly = 697.00,
                price_yearly = 6970.00,
                sort_order = 2,
                updated_at = :updated_at
            WHERE slug = 'professional'
        """),
        {"updated_at": datetime.utcnow()}
    )
    
    # Reverter preços do Enterprise
    conn.execute(
        sa.text("""
            UPDATE plans 
            SET 
                price_monthly = 1497.00,
                price_yearly = 14970.00,
                sort_order = 3,
                updated_at = :updated_at
            WHERE slug = 'enterprise'
        """),
        {"updated_at": datetime.utcnow()}
    )
    
    print("✅ Downgrade concluído")
