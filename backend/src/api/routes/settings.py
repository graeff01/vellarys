"""
ROTAS: CONFIGURAÇÕES
=====================

Endpoints para o gestor configurar o tenant.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Tenant, User, Niche
from src.api.dependencies import get_current_user, get_current_tenant

router = APIRouter(prefix="/settings", tags=["Configurações"])


# Configurações padrão
DEFAULT_SETTINGS = {
    # Básico
    "niche": "services",
    "company_name": "",
    "tone": "cordial",
    
    # Personalização
    "custom_questions": [],
    "custom_rules": [],
    
    # Handoff
    "manager_whatsapp": "",
    "manager_name": "",
    "handoff_enabled": True,
    "handoff_triggers": [],
    "max_messages_before_handoff": 15,
    
    # Horário de atendimento
    "business_hours_enabled": False,
    "business_hours": {
        "monday": {"open": "08:00", "close": "18:00", "enabled": True},
        "tuesday": {"open": "08:00", "close": "18:00", "enabled": True},
        "wednesday": {"open": "08:00", "close": "18:00", "enabled": True},
        "thursday": {"open": "08:00", "close": "18:00", "enabled": True},
        "friday": {"open": "08:00", "close": "18:00", "enabled": True},
        "saturday": {"open": "08:00", "close": "12:00", "enabled": False},
        "sunday": {"open": "", "close": "", "enabled": False},
    },
    "out_of_hours_message": "Olá! No momento estamos fora do horário de atendimento. Retornaremos em breve!",
    
    # FAQ / Catálogo
    "faq_enabled": True,
    "faq_items": [],
    
    # Escopo da IA
    "scope_enabled": True,
    "scope_description": "",
    "out_of_scope_message": "Desculpe, não tenho informações sobre isso. Posso ajudar com dúvidas sobre nossos produtos e serviços!",
    
    # Distribuição de Leads
    "distribution": {
        "method": "round_robin",  # round_robin, by_city, by_specialty, by_city_specialty, by_priority, least_busy, manual
        "fallback": "manager",  # manager, round_robin, queue
        "respect_daily_limit": True,
        "respect_availability": True,
        "notify_manager_copy": False,
        "last_seller_index": 0,
    },
}


# Métodos de distribuição disponíveis
DISTRIBUTION_METHODS = [
    {
        "id": "round_robin",
        "name": "Rodízio",
        "description": "Distribui leads igualmente entre todos os vendedores",
        "icon": "🔄",
    },
    {
        "id": "by_city",
        "name": "Por Cidade",
        "description": "Lead vai para o vendedor que atende a cidade dele",
        "icon": "📍",
    },
    {
        "id": "by_specialty",
        "name": "Por Especialidade",
        "description": "Lead vai para o vendedor com a especialidade certa",
        "icon": "🎯",
    },
    {
        "id": "by_city_specialty",
        "name": "Cidade + Especialidade",
        "description": "Combina cidade e especialidade para encontrar o melhor vendedor",
        "icon": "📍🎯",
    },
    {
        "id": "by_priority",
        "name": "Por Prioridade",
        "description": "Vendedores com maior prioridade recebem mais leads",
        "icon": "⭐",
    },
    {
        "id": "least_busy",
        "name": "Menos Ocupado",
        "description": "Lead vai para o vendedor com menos leads no dia",
        "icon": "⚖️",
    },
    {
        "id": "manual",
        "name": "Manual",
        "description": "Gestor decide manualmente para quem enviar cada lead",
        "icon": "✋",
    },
]

FALLBACK_OPTIONS = [
    {
        "id": "manager",
        "name": "Enviar para Gestor",
        "description": "Se não encontrar vendedor, envia para o gestor decidir",
    },
    {
        "id": "round_robin",
        "name": "Rodízio Geral",
        "description": "Se não encontrar vendedor específico, distribui entre todos",
    },
    {
        "id": "queue",
        "name": "Fila de Espera",
        "description": "Lead fica na fila até um vendedor ficar disponível",
    },
]


async def get_niches_from_db(db: AsyncSession) -> list[dict]:
    """
    Busca nichos ativos do banco de dados.
    """
    result = await db.execute(
        select(Niche)
        .where(Niche.active == True)
        .order_by(Niche.name)
    )
    niches = result.scalars().all()
    
    return [
        {
            "id": niche.slug,
            "name": niche.name,
            "description": niche.description or "",
            "icon": niche.icon or "📦",
        }
        for niche in niches
    ]


@router.get("")
async def get_settings(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna configurações atuais do tenant.
    """
    # Merge com defaults para garantir que todos os campos existam
    settings = {**DEFAULT_SETTINGS, **(tenant.settings or {})}
    
    # Garante que distribution existe
    if "distribution" not in settings:
        settings["distribution"] = DEFAULT_SETTINGS["distribution"]
    else:
        settings["distribution"] = {
            **DEFAULT_SETTINGS["distribution"],
            **settings.get("distribution", {}),
        }
    
    # Garante que company_name tenha valor
    if not settings.get("company_name"):
        settings["company_name"] = tenant.name
    
    # Busca nichos do banco de dados
    available_niches = await get_niches_from_db(db)
    
    return {
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan,
        },
        "settings": settings,
        "available_niches": available_niches,
        "distribution_methods": DISTRIBUTION_METHODS,
        "fallback_options": FALLBACK_OPTIONS,
    }


@router.patch("")
async def update_settings(
    payload: dict,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza configurações do tenant.
    """
    
    # Campos permitidos
    allowed_settings = [
        # Básico
        "niche", "company_name", "tone",
        # Personalização
        "custom_questions", "custom_rules",
        # Handoff
        "manager_whatsapp", "manager_name",
        "handoff_enabled", "handoff_triggers",
        "max_messages_before_handoff",
        # Horário
        "business_hours_enabled", "business_hours", "out_of_hours_message",
        # FAQ
        "faq_enabled", "faq_items",
        # Escopo
        "scope_enabled", "scope_description", "out_of_scope_message",
        # Distribuição
        "distribution",
    ]
    
    # Atualiza nome do tenant se enviado
    if "name" in payload and payload["name"]:
        tenant.name = payload["name"]
    
    # Merge settings
    current_settings = {**DEFAULT_SETTINGS, **(tenant.settings or {})}
    
    for key in allowed_settings:
        if key in payload:
            if key == "distribution":
                # Merge distribuição
                current_distribution = current_settings.get("distribution", {})
                new_distribution = payload.get("distribution", {})
                current_settings["distribution"] = {
                    **DEFAULT_SETTINGS["distribution"],
                    **current_distribution,
                    **new_distribution,
                }
            else:
                current_settings[key] = payload[key]
    
    tenant.settings = current_settings
    
    await db.commit()
    await db.refresh(tenant)
    
    return {
        "success": True,
        "message": "Configurações atualizadas",
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan,
        },
        "settings": tenant.settings,
    }


@router.get("/niches")
async def list_niches(
    db: AsyncSession = Depends(get_db),
):
    """
    Lista todos os nichos disponíveis (do banco de dados).
    """
    return await get_niches_from_db(db)


@router.get("/distribution-options")
async def get_distribution_options(
    user: User = Depends(get_current_user),
):
    """
    Retorna opções de distribuição disponíveis.
    """
    return {
        "methods": DISTRIBUTION_METHODS,
        "fallbacks": FALLBACK_OPTIONS,
    }