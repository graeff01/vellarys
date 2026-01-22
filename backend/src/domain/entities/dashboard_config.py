"""
DASHBOARD CONFIG - Configuração personalizada do dashboard por usuário
======================================================================

Permite que cada gestor personalize seu dashboard:
- Quais widgets exibir
- Ordem e tamanho dos widgets
- Configurações específicas de cada widget

Estrutura de widgets:
[
  {"id": "metrics", "type": "metrics", "enabled": true, "position": 0, "size": "full"},
  {"id": "sales_goal", "type": "sales_goal", "enabled": true, "position": 1, "size": "half"},
  ...
]
"""

from sqlalchemy import Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableList, MutableDict
from typing import Optional, List

from .base import Base, TimestampMixin


class DashboardConfig(Base, TimestampMixin):
    """
    Configuração personalizada do dashboard do usuário.

    Cada usuário pode ter sua própria configuração.
    Se não tiver, usa o template padrão.
    """

    __tablename__ = "dashboard_configs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Pode ser por usuário ou por tenant (gestor principal)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True
    )

    # Nome da configuração (para múltiplos layouts)
    name: Mapped[str] = mapped_column(String(100), default="Principal")

    # Se é a configuração ativa
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Lista de widgets configurados
    # Estrutura: [{"id": "...", "type": "...", "enabled": true, "position": 0, "size": "full", "settings": {}}]
    widgets: Mapped[list] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False
    )

    # Configurações globais do dashboard
    # Ex: {"theme": "light", "density": "comfortable", "auto_refresh": true}
    settings: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<DashboardConfig(id={self.id}, user_id={self.user_id}, name={self.name})>"


class SalesGoal(Base, TimestampMixin):
    """
    Meta de vendas do tenant.

    Permite definir metas mensais e acompanhar progresso.
    """

    __tablename__ = "sales_goals"

    id: Mapped[int] = mapped_column(primary_key=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True
    )

    # Período (YYYY-MM)
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # "2026-01"

    # Metas
    revenue_goal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # R$ em centavos
    deals_goal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Número de vendas
    leads_goal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Leads a captar

    # Valores realizados (atualizados manualmente ou via integração)
    revenue_actual: Mapped[int] = mapped_column(Integer, default=0)  # R$ em centavos
    deals_actual: Mapped[int] = mapped_column(Integer, default=0)

    # Configurações adicionais
    # Ex: {"notify_at": [50, 80, 100], "seller_goals": {...}}
    extra_config: Mapped[dict] = mapped_column(
        "config",
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<SalesGoal(id={self.id}, tenant_id={self.tenant_id}, period={self.period})>"

    @property
    def revenue_progress(self) -> float:
        """Retorna progresso da meta de receita em %."""
        if not self.revenue_goal or self.revenue_goal <= 0:
            return 0
        return min((self.revenue_actual / self.revenue_goal) * 100, 100)

    @property
    def deals_progress(self) -> float:
        """Retorna progresso da meta de vendas em %."""
        if not self.deals_goal or self.deals_goal <= 0:
            return 0
        return min((self.deals_actual / self.deals_goal) * 100, 100)


# Widget types disponíveis
WIDGET_TYPES = {
    # Métricas básicas (já existentes)
    "metrics_cards": {
        "name": "Métricas Principais",
        "description": "KPIs de atendimento total, leads quentes e transferidos",
        "category": "metricas",
        "default_size": "full",
        "icon": "BarChart3"
    },
    "qualification_donut": {
        "name": "Qualificação de Leads",
        "description": "Gráfico de pizza com distribuição quente/morno/frio",
        "category": "metricas",
        "default_size": "third",
        "icon": "PieChart"
    },
    "funnel": {
        "name": "Funil de Atendimento",
        "description": "Visualização do funil de conversão",
        "category": "metricas",
        "default_size": "half",
        "icon": "Filter"
    },
    "topics_heatmap": {
        "name": "Interesses e Dúvidas",
        "description": "Nuvem de palavras com tópicos mais frequentes",
        "category": "metricas",
        "default_size": "half",
        "icon": "MessageSquare"
    },
    "impact_velaris": {
        "name": "Impacto Velaris IA",
        "description": "ROI, tempo economizado e velocidade de resposta",
        "category": "metricas",
        "default_size": "two_thirds",
        "icon": "Sparkles"
    },
    "leads_table": {
        "name": "Leads Recentes",
        "description": "Tabela com últimos leads",
        "category": "metricas",
        "default_size": "two_thirds",
        "icon": "Users"
    },
    "plan_usage": {
        "name": "Uso do Plano",
        "description": "Limites e consumo do plano atual",
        "category": "sistema",
        "default_size": "third",
        "icon": "CreditCard"
    },
    "hot_leads_cta": {
        "name": "Alerta Leads Quentes",
        "description": "CTA de destaque para leads quentes aguardando",
        "category": "alertas",
        "default_size": "full",
        "icon": "Flame"
    },

    # Novos widgets de vendas
    "sales_goal": {
        "name": "Meta Mensal",
        "description": "Progresso da meta de vendas do mês",
        "category": "vendas",
        "default_size": "third",
        "icon": "Target"
    },
    "sales_progress": {
        "name": "Progresso de Vendas",
        "description": "Quanto falta para bater a meta",
        "category": "vendas",
        "default_size": "third",
        "icon": "TrendingUp"
    },
    "deals_closed": {
        "name": "Vendas Fechadas",
        "description": "Número de vendas no período",
        "category": "vendas",
        "default_size": "third",
        "icon": "CheckCircle"
    },
    "average_ticket": {
        "name": "Ticket Médio",
        "description": "Valor médio das vendas",
        "category": "vendas",
        "default_size": "third",
        "icon": "DollarSign"
    },
    "month_projection": {
        "name": "Projeção do Mês",
        "description": "Estimativa de fechamento baseada na velocidade atual",
        "category": "vendas",
        "default_size": "third",
        "icon": "TrendingUp"
    },
    "seller_ranking": {
        "name": "Ranking de Vendedores",
        "description": "Top vendedores por conversão ou vendas",
        "category": "vendas",
        "default_size": "half",
        "icon": "Trophy"
    },
    "days_remaining": {
        "name": "Dias Restantes",
        "description": "Urgência visual de dias até fim do mês",
        "category": "vendas",
        "default_size": "third",
        "icon": "Calendar"
    },
    "conversion_rate": {
        "name": "Taxa de Conversão",
        "description": "Percentual de leads convertidos em vendas",
        "category": "vendas",
        "default_size": "third",
        "icon": "Percent"
    },
}

# Template padrão para novos usuários
DEFAULT_DASHBOARD_WIDGETS = [
    {"id": "metrics_cards", "type": "metrics_cards", "enabled": True, "position": 0, "size": "full"},
    {"id": "hot_leads_cta", "type": "hot_leads_cta", "enabled": True, "position": 1, "size": "full"},
    {"id": "impact_velaris", "type": "impact_velaris", "enabled": True, "position": 2, "size": "two_thirds"},
    {"id": "qualification_donut", "type": "qualification_donut", "enabled": True, "position": 3, "size": "third"},
    {"id": "funnel", "type": "funnel", "enabled": True, "position": 4, "size": "half"},
    {"id": "topics_heatmap", "type": "topics_heatmap", "enabled": True, "position": 5, "size": "half"},
    {"id": "plan_usage", "type": "plan_usage", "enabled": True, "position": 6, "size": "third"},
    {"id": "leads_table", "type": "leads_table", "enabled": True, "position": 7, "size": "two_thirds"},
]

# Widgets de vendas (desabilitados por padrão - gestor pode habilitar)
SALES_WIDGETS_TEMPLATE = [
    {"id": "sales_goal", "type": "sales_goal", "enabled": False, "position": 100, "size": "third"},
    {"id": "sales_progress", "type": "sales_progress", "enabled": False, "position": 101, "size": "third"},
    {"id": "deals_closed", "type": "deals_closed", "enabled": False, "position": 102, "size": "third"},
    {"id": "average_ticket", "type": "average_ticket", "enabled": False, "position": 103, "size": "third"},
    {"id": "month_projection", "type": "month_projection", "enabled": False, "position": 104, "size": "third"},
    {"id": "seller_ranking", "type": "seller_ranking", "enabled": False, "position": 105, "size": "half"},
    {"id": "days_remaining", "type": "days_remaining", "enabled": False, "position": 106, "size": "third"},
    {"id": "conversion_rate", "type": "conversion_rate", "enabled": False, "position": 107, "size": "third"},
]
