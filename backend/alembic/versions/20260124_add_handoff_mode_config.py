"""add handoff mode configuration

Revision ID: 20260124_handoff_mode
Revises: 20260124_message_sender
Create Date: 2026-01-24

Adiciona configuração handoff_mode em tenant.settings:
- "crm_inbox": Novo fluxo (corretor atende via CRM)
- "whatsapp_pessoal": Fluxo legacy (corretor atende via WhatsApp pessoal)
"""
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260124_handoff_mode'
down_revision = '20260124_message_sender'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Adiciona configuração padrão de handoff_mode.
    """

    # Define handoff_mode padrão como "whatsapp_pessoal" (legacy)
    # para não quebrar o comportamento atual
    op.execute("""
        UPDATE tenants
        SET settings = jsonb_set(
            COALESCE(settings, '{}'::jsonb),
            '{handoff_mode}',
            '"whatsapp_pessoal"'::jsonb
        )
        WHERE settings->>'handoff_mode' IS NULL
    """)

    print("✅ Configuração handoff_mode='whatsapp_pessoal' adicionada aos tenants existentes")


def downgrade() -> None:
    """
    Remove configuração de handoff_mode.
    """
    op.execute("""
        UPDATE tenants
        SET settings = settings - 'handoff_mode'
        WHERE settings ? 'handoff_mode'
    """)

    print("✅ Configuração handoff_mode removida")
