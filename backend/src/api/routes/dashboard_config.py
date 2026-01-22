"""
ROTAS: DASHBOARD CONFIG
========================

Endpoints para configuração personalizada do dashboard.
Permite que gestores customizem seus widgets e layout.

Endpoints:
- GET /dashboard/config - Busca configuração atual
- PUT /dashboard/config - Atualiza configuração
- GET /dashboard/widgets - Lista widgets disponíveis
- POST /dashboard/config/reset - Restaura padrão
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import User
from src.domain.entities.dashboard_config import (
    DashboardConfig,
    WIDGET_TYPES,
    DEFAULT_DASHBOARD_WIDGETS,
    SALES_WIDGETS_TEMPLATE,
)
from src.api.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard Config"])


# =============================================
# SCHEMAS
# =============================================

class WidgetConfigSchema(BaseModel):
    """Schema de configuração de um widget."""
    id: str
    type: str
    enabled: bool = True
    position: int = 0
    size: str = "full"  # full, half, third, two_thirds
    settings: dict = Field(default_factory=dict)

    # Grid layout fields (react-grid-layout)
    i: Optional[str] = None  # ID único para o grid
    x: Optional[int] = None  # Posição X (coluna)
    y: Optional[int] = None  # Posição Y (linha)
    w: Optional[int] = None  # Largura em colunas
    h: Optional[int] = None  # Altura em rows
    minW: Optional[int] = None
    maxW: Optional[int] = None
    minH: Optional[int] = None
    maxH: Optional[int] = None
    static: Optional[bool] = None  # Widget fixo (não arrastável)


class DashboardConfigSchema(BaseModel):
    """Schema da configuração do dashboard."""
    widgets: List[WidgetConfigSchema]
    settings: dict = Field(default_factory=dict)
    layout_version: str = "v1"  # "v1" = position/size, "v2" = grid layout


class WidgetTypeSchema(BaseModel):
    """Schema de tipo de widget disponível."""
    id: str
    name: str
    description: str
    category: str
    default_size: str
    icon: str


class DashboardConfigResponse(BaseModel):
    """Resposta da configuração do dashboard."""
    id: Optional[int] = None
    widgets: List[dict]
    settings: dict
    is_default: bool = False
    layout_version: str = "v1"  # "v1" = position/size, "v2" = grid layout


# =============================================
# ENDPOINTS
# =============================================

@router.get("/config", response_model=DashboardConfigResponse)
async def get_dashboard_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Busca configuração do dashboard do usuário.

    Se não existir configuração personalizada, retorna o template padrão.
    """
    try:
        tenant_id = current_user.tenant_id
        user_id = current_user.id

        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        # Busca configuração do usuário específico
        result = await db.execute(
            select(DashboardConfig)
            .where(
                and_(
                    DashboardConfig.tenant_id == tenant_id,
                    DashboardConfig.user_id == user_id,
                    DashboardConfig.is_active == True
                )
            )
            .order_by(DashboardConfig.updated_at.desc())
            .limit(1)
        )
        config = result.scalar_one_or_none()

        # Se não encontrou do usuário, tenta do tenant (config global)
        if not config:
            result = await db.execute(
                select(DashboardConfig)
                .where(
                    and_(
                        DashboardConfig.tenant_id == tenant_id,
                        DashboardConfig.user_id.is_(None),
                        DashboardConfig.is_active == True
                    )
                )
                .order_by(DashboardConfig.updated_at.desc())
                .limit(1)
            )
            config = result.scalar_one_or_none()

        if config:
            # Detecta versão do layout
            layout_version = (config.settings or {}).get("layout_version", "v1")
            return DashboardConfigResponse(
                id=config.id,
                widgets=config.widgets,
                settings=config.settings or {},
                is_default=False,
                layout_version=layout_version
            )

        # Retorna template padrão com todos os widgets disponíveis
        all_widgets = DEFAULT_DASHBOARD_WIDGETS + SALES_WIDGETS_TEMPLATE
        return DashboardConfigResponse(
            id=None,
            widgets=all_widgets,
            settings={},
            is_default=True,
            layout_version="v1"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro buscando config dashboard: {e}", exc_info=True)
        # Fallback para template padrão
        all_widgets = DEFAULT_DASHBOARD_WIDGETS + SALES_WIDGETS_TEMPLATE
        return DashboardConfigResponse(
            id=None,
            widgets=all_widgets,
            settings={},
            is_default=True,
            layout_version="v1"
        )


@router.put("/config", response_model=DashboardConfigResponse)
async def update_dashboard_config(
    config_data: DashboardConfigSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza configuração do dashboard do usuário.

    Se não existir, cria uma nova.
    """
    try:
        tenant_id = current_user.tenant_id
        user_id = current_user.id

        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        # Valida widgets
        valid_types = set(WIDGET_TYPES.keys())
        for widget in config_data.widgets:
            if widget.type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de widget inválido: {widget.type}"
                )

        # Busca configuração existente
        result = await db.execute(
            select(DashboardConfig)
            .where(
                and_(
                    DashboardConfig.tenant_id == tenant_id,
                    DashboardConfig.user_id == user_id,
                    DashboardConfig.is_active == True
                )
            )
            .limit(1)
        )
        config = result.scalar_one_or_none()

        widgets_data = [w.model_dump(exclude_none=True) for w in config_data.widgets]

        # Salva layout_version nas settings
        settings_data = config_data.settings.copy() if config_data.settings else {}
        settings_data["layout_version"] = config_data.layout_version

        if config:
            # Atualiza existente
            config.widgets = widgets_data
            config.settings = settings_data
            config.updated_at = datetime.now(timezone.utc)
        else:
            # Cria nova
            config = DashboardConfig(
                tenant_id=tenant_id,
                user_id=user_id,
                name="Principal",
                is_active=True,
                widgets=widgets_data,
                settings=settings_data,
            )
            db.add(config)

        await db.commit()
        await db.refresh(config)

        logger.info(f"✅ Dashboard config salva (user={user_id}, tenant={tenant_id}, version={config_data.layout_version})")

        return DashboardConfigResponse(
            id=config.id,
            widgets=config.widgets,
            settings=config.settings or {},
            is_default=False,
            layout_version=config_data.layout_version
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro salvando config dashboard: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao salvar configuração")


@router.get("/widgets", response_model=List[WidgetTypeSchema])
async def list_available_widgets(
    current_user: User = Depends(get_current_user),
):
    """
    Lista todos os tipos de widgets disponíveis.

    Retorna metadata de cada widget para o frontend.
    """
    widgets = []
    for widget_id, widget_data in WIDGET_TYPES.items():
        widgets.append(WidgetTypeSchema(
            id=widget_id,
            name=widget_data["name"],
            description=widget_data["description"],
            category=widget_data["category"],
            default_size=widget_data["default_size"],
            icon=widget_data["icon"],
        ))

    # Ordena por categoria
    category_order = {"alertas": 0, "metricas": 1, "vendas": 2, "sistema": 3}
    widgets.sort(key=lambda w: (category_order.get(w.category, 99), w.name))

    return widgets


@router.post("/config/reset", response_model=DashboardConfigResponse)
async def reset_dashboard_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Restaura configuração do dashboard para o padrão.

    Remove configuração personalizada do usuário.
    """
    try:
        tenant_id = current_user.tenant_id
        user_id = current_user.id

        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        # Busca e desativa configuração existente
        result = await db.execute(
            select(DashboardConfig)
            .where(
                and_(
                    DashboardConfig.tenant_id == tenant_id,
                    DashboardConfig.user_id == user_id,
                    DashboardConfig.is_active == True
                )
            )
        )
        configs = result.scalars().all()

        for config in configs:
            config.is_active = False

        await db.commit()

        logger.info(f"🔄 Dashboard config resetada (user={user_id})")

        # Retorna template padrão
        all_widgets = DEFAULT_DASHBOARD_WIDGETS + SALES_WIDGETS_TEMPLATE
        return DashboardConfigResponse(
            id=None,
            widgets=all_widgets,
            settings={},
            is_default=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro resetando config dashboard: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao resetar configuração")
