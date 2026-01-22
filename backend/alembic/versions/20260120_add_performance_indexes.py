"""
Migration: Add Performance Indexes for Scalability
===================================================

Adiciona índices críticos para melhorar performance com múltiplos tenants.

Requisitos:
- PostgreSQL precisa estar rodando
- Executar via Alembic ou manualmente

Revision ID: 20260120_add_performance_indexes
Revises: 20260115_add_conversation_summary
Create Date: 2026-01-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers
revision = '20260120_add_performance_indexes'
down_revision = '20260115_002'  # after pgvector
branch_labels = None
depends_on = None


def upgrade():
    """Adiciona índices de performance."""
    
    # ==========================================================
    # ÍNDICES PARA LEADS
    # ==========================================================
    
    # Índice para busca por telefone (muito usado em webhooks)
    # Partial index - só indexa onde phone não é null
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_leads_phone 
        ON leads(phone) 
        WHERE phone IS NOT NULL
    """))
    
    # Índice para reengajamento (usado pelo scheduler)
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_leads_reengagement 
        ON leads(tenant_id, reengagement_status, last_activity_at)
    """))
    
    # Índice para leads ativos por fonte (relatórios)
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_leads_tenant_source 
        ON leads(tenant_id, source) 
        WHERE status = 'active'
    """))
    
    # ==========================================================
    # ÍNDICES PARA AUDIT LOGS
    # ==========================================================
    
    # Índice para consultas de auditoria (compliance LGPD)
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant_date 
        ON audit_logs(tenant_id, created_at DESC)
    """))
    
    # Índice para busca por ação específica
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_audit_logs_action 
        ON audit_logs(action, created_at DESC)
    """))
    
    # ==========================================================
    # ÍNDICES PARA NOTIFICATIONS
    # ==========================================================
    
    # Partial index para notificações não lidas (mais comum)
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_notifications_unread 
        ON notifications(tenant_id, created_at DESC) 
        WHERE read = false
    """))
    
    # ==========================================================
    # ÍNDICES PARA SELLERS
    # ==========================================================
    
    # Índice para distribuição de leads (round-robin)
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_sellers_active_distribution 
        ON sellers(tenant_id, is_active, current_leads_count) 
        WHERE is_active = true
    """))
    
    # ==========================================================
    # ÍNDICES PARA PRODUCTS
    # ==========================================================
    
    # Índice para busca geolocalizada (se tiver lat/lng)
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_products_location 
        ON products(tenant_id, latitude, longitude) 
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """))
    
    print("✅ Índices de performance criados com sucesso!")


def downgrade():
    """Remove os índices criados."""
    
    op.execute(text("DROP INDEX IF EXISTS ix_leads_phone"))
    op.execute(text("DROP INDEX IF EXISTS ix_leads_reengagement"))
    op.execute(text("DROP INDEX IF EXISTS ix_leads_tenant_source"))
    op.execute(text("DROP INDEX IF EXISTS ix_audit_logs_tenant_date"))
    op.execute(text("DROP INDEX IF EXISTS ix_audit_logs_action"))
    op.execute(text("DROP INDEX IF EXISTS ix_notifications_unread"))
    op.execute(text("DROP INDEX IF EXISTS ix_sellers_active_distribution"))
    op.execute(text("DROP INDEX IF EXISTS ix_products_location"))
    
    print("❌ Índices de performance removidos.")
