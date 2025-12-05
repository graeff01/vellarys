"""
ROTAS: CONFIGURAÇÕES
=====================

Endpoints para o gestor configurar o tenant.
Inclui a nova seção de Identidade Empresarial.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional

from src.infrastructure.database import get_db
from src.domain.entities import Tenant, User, Niche
from src.api.dependencies import get_current_user, get_current_tenant

router = APIRouter(prefix="/settings", tags=["Configurações"])


# =============================================================================
# CONFIGURAÇÕES PADRÃO
# =============================================================================

DEFAULT_SETTINGS = {
    # =========================================================================
    # IDENTIDADE EMPRESARIAL (NOVO)
    # =========================================================================
    "identity": {
        # Descrição da empresa (texto livre, 2-4 linhas)
        "description": "",
        
        # Produtos/Serviços oferecidos (lista de strings)
        "products_services": [],
        
        # O que a empresa NÃO faz (lista - evita erro da IA)
        "not_offered": [],
        
        # Tom de voz detalhado
        "tone_style": {
            "tone": "cordial",  # formal, cordial, informal, tecnico
            "personality_traits": [],  # Ex: ["acolhedor", "objetivo", "consultivo"]
            "communication_style": "",  # Descrição livre do estilo
            "avoid_phrases": [],  # Frases/palavras a evitar
            "use_phrases": [],  # Frases/palavras preferidas
        },
        
        # Público-alvo
        "target_audience": {
            "description": "",  # Ex: "Mulheres 25-45, classe A/B"
            "segments": [],  # Ex: ["premium", "primeira_compra", "investidor"]
            "pain_points": [],  # Dores do cliente que a empresa resolve
        },
        
        # Regras de negócio para a IA
        "business_rules": [],  # Ex: ["Não passar valores", "Sempre pedir data"]
        
        # Diferenciais e valores da marca
        "differentials": [],  # Ex: ["Atendimento 24h", "Garantia estendida"]
        
        # Palavras-chave do negócio (dicionário semântico)
        "keywords": [],  # Ex: ["implante", "prótese", "clareamento"]
        
        # Perguntas obrigatórias na qualificação
        "required_questions": [],
        
        # Informações que SEMPRE devem ser coletadas
        "required_info": [],  # Ex: ["nome", "telefone", "cidade", "data_preferencia"]
        
        # Contexto adicional livre
        "additional_context": "",
    },
    
    # =========================================================================
    # CONFIGURAÇÕES BÁSICAS (existente, reorganizado)
    # =========================================================================
    "basic": {
        "niche": "services",
        "company_name": "",
    },
    
    # =========================================================================
    # PERSONALIZAÇÃO DA IA (existente, reorganizado)
    # =========================================================================
    "ai_behavior": {
        "custom_questions": [],
        "custom_rules": [],
        "greeting_message": "",
        "farewell_message": "",
    },
    
    # =========================================================================
    # HANDOFF / TRANSFERÊNCIA (existente)
    # =========================================================================
    "handoff": {
        "enabled": True,
        "manager_whatsapp": "",
        "manager_name": "",
        "triggers": [],
        "max_messages_before_handoff": 15,
        "transfer_message": "",  # Mensagem quando transfere
    },
    
    # =========================================================================
    # HORÁRIO DE ATENDIMENTO (existente)
    # =========================================================================
    "business_hours": {
        "enabled": False,
        "timezone": "America/Sao_Paulo",
        "schedule": {
            "monday": {"open": "08:00", "close": "18:00", "enabled": True},
            "tuesday": {"open": "08:00", "close": "18:00", "enabled": True},
            "wednesday": {"open": "08:00", "close": "18:00", "enabled": True},
            "thursday": {"open": "08:00", "close": "18:00", "enabled": True},
            "friday": {"open": "08:00", "close": "18:00", "enabled": True},
            "saturday": {"open": "08:00", "close": "12:00", "enabled": False},
            "sunday": {"open": "", "close": "", "enabled": False},
        },
        "out_of_hours_message": "Olá! No momento estamos fora do horário de atendimento. Retornaremos em breve!",
        "out_of_hours_behavior": "message_only",  # message_only, collect_info, redirect
    },
    
    # =========================================================================
    # FAQ / BASE DE CONHECIMENTO (existente)
    # =========================================================================
    "faq": {
        "enabled": True,
        "items": [],
    },
    
    # =========================================================================
    # ESCOPO DA IA (existente, aprimorado)
    # =========================================================================
    "scope": {
        "enabled": True,
        "description": "",
        "allowed_topics": [],  # Tópicos permitidos
        "blocked_topics": [],  # Tópicos bloqueados
        "out_of_scope_message": "Desculpe, não tenho informações sobre isso. Posso ajudar com dúvidas sobre nossos produtos e serviços!",
    },
    
    # =========================================================================
    # DISTRIBUIÇÃO DE LEADS (existente)
    # =========================================================================
    "distribution": {
        "method": "round_robin",
        "fallback": "manager",
        "respect_daily_limit": True,
        "respect_availability": True,
        "notify_manager_copy": False,
        "last_seller_index": 0,
    },
    
    # =========================================================================
    # GUARDRAILS / PROTEÇÕES (novo)
    # =========================================================================
    "guardrails": {
        "price_guard": {
            "enabled": True,
            "behavior": "redirect",  # redirect, collect_first, allow
            "message": "Para valores, preciso entender melhor sua necessidade. Pode me contar mais?",
        },
        "competitor_guard": {
            "enabled": False,
            "competitors": [],
            "behavior": "neutral",  # neutral, redirect, highlight_differentials
        },
        "scope_guard": {
            "enabled": True,
            "strictness": "medium",  # low, medium, high
        },
        "insist_guard": {
            "enabled": True,
            "max_attempts": 3,
            "escalate_after": True,
        },
    },
    
    # =========================================================================
    # MENSAGENS PADRÃO PERSONALIZÁVEIS (novo)
    # =========================================================================
    "messages": {
        "greeting": "",
        "farewell": "",
        "out_of_hours": "",
        "out_of_scope": "",
        "handoff_notice": "",
        "qualification_complete": "",
        "waiting_response": "",
    },
}


# =============================================================================
# OPÇÕES DE CONFIGURAÇÃO
# =============================================================================

TONE_OPTIONS = [
    {
        "id": "formal",
        "name": "Formal",
        "description": "Profissional, direto e corporativo",
        "icon": "👔",
        "examples": ["Prezado(a)", "Agradeço o contato", "Fico à disposição"],
    },
    {
        "id": "cordial",
        "name": "Cordial",
        "description": "Amigável, educado e acolhedor",
        "icon": "😊",
        "examples": ["Olá!", "Fico feliz em ajudar", "Conte comigo"],
    },
    {
        "id": "informal",
        "name": "Informal",
        "description": "Descontraído, próximo e casual",
        "icon": "🤙",
        "examples": ["Oi!", "Show!", "Bora lá"],
    },
    {
        "id": "tecnico",
        "name": "Técnico",
        "description": "Preciso, detalhado e especializado",
        "icon": "🔬",
        "examples": ["Tecnicamente", "De acordo com", "Especificamente"],
    },
]

PERSONALITY_TRAITS = [
    {"id": "acolhedor", "name": "Acolhedor", "description": "Faz o cliente se sentir bem-vindo"},
    {"id": "objetivo", "name": "Objetivo", "description": "Vai direto ao ponto"},
    {"id": "consultivo", "name": "Consultivo", "description": "Orienta e aconselha"},
    {"id": "entusiasmado", "name": "Entusiasmado", "description": "Demonstra empolgação"},
    {"id": "paciente", "name": "Paciente", "description": "Explica com calma"},
    {"id": "profissional", "name": "Profissional", "description": "Mantém formalidade"},
    {"id": "empático", "name": "Empático", "description": "Demonstra compreensão"},
    {"id": "proativo", "name": "Proativo", "description": "Antecipa necessidades"},
]

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

REQUIRED_INFO_OPTIONS = [
    {"id": "nome", "name": "Nome", "description": "Nome do cliente"},
    {"id": "telefone", "name": "Telefone", "description": "Telefone de contato"},
    {"id": "email", "name": "E-mail", "description": "E-mail do cliente"},
    {"id": "cidade", "name": "Cidade", "description": "Cidade do cliente"},
    {"id": "bairro", "name": "Bairro", "description": "Bairro do cliente"},
    {"id": "data_preferencia", "name": "Data de Preferência", "description": "Data preferida para atendimento"},
    {"id": "horario_preferencia", "name": "Horário de Preferência", "description": "Horário preferido"},
    {"id": "orcamento", "name": "Orçamento", "description": "Faixa de orçamento"},
    {"id": "urgencia", "name": "Urgência", "description": "Nível de urgência"},
    {"id": "como_conheceu", "name": "Como Conheceu", "description": "Como conheceu a empresa"},
]


# =============================================================================
# HELPERS
# =============================================================================

def deep_merge(base: dict, override: dict) -> dict:
    """
    Merge profundo de dicionários.
    Mantém estrutura do base e sobrescreve com valores do override.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


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


def migrate_legacy_settings(settings: dict) -> dict:
    """
    Migra configurações do formato antigo para o novo.
    Mantém compatibilidade com tenants existentes.
    """
    if not settings:
        return {}
    
    # Se já está no novo formato, retorna
    if "identity" in settings:
        return settings
    
    # Migração do formato antigo
    migrated = {}
    
    # Basic
    migrated["basic"] = {
        "niche": settings.get("niche", "services"),
        "company_name": settings.get("company_name", ""),
    }
    
    # Identity (novo, valores vazios)
    migrated["identity"] = DEFAULT_SETTINGS["identity"].copy()
    migrated["identity"]["tone_style"]["tone"] = settings.get("tone", "cordial")
    
    # AI Behavior
    migrated["ai_behavior"] = {
        "custom_questions": settings.get("custom_questions", []),
        "custom_rules": settings.get("custom_rules", []),
        "greeting_message": "",
        "farewell_message": "",
    }
    
    # Handoff
    migrated["handoff"] = {
        "enabled": settings.get("handoff_enabled", True),
        "manager_whatsapp": settings.get("manager_whatsapp", ""),
        "manager_name": settings.get("manager_name", ""),
        "triggers": settings.get("handoff_triggers", []),
        "max_messages_before_handoff": settings.get("max_messages_before_handoff", 15),
        "transfer_message": "",
    }
    
    # Business Hours
    migrated["business_hours"] = {
        "enabled": settings.get("business_hours_enabled", False),
        "timezone": "America/Sao_Paulo",
        "schedule": settings.get("business_hours", DEFAULT_SETTINGS["business_hours"]["schedule"]),
        "out_of_hours_message": settings.get("out_of_hours_message", ""),
        "out_of_hours_behavior": "message_only",
    }
    
    # FAQ
    migrated["faq"] = {
        "enabled": settings.get("faq_enabled", True),
        "items": settings.get("faq_items", []),
    }
    
    # Scope
    migrated["scope"] = {
        "enabled": settings.get("scope_enabled", True),
        "description": settings.get("scope_description", ""),
        "allowed_topics": [],
        "blocked_topics": [],
        "out_of_scope_message": settings.get("out_of_scope_message", ""),
    }
    
    # Distribution
    migrated["distribution"] = settings.get("distribution", DEFAULT_SETTINGS["distribution"])
    
    # Guardrails (novo)
    migrated["guardrails"] = DEFAULT_SETTINGS["guardrails"].copy()
    
    # Messages (novo)
    migrated["messages"] = DEFAULT_SETTINGS["messages"].copy()
    
    return migrated


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("")
async def get_settings(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna configurações atuais do tenant.
    Faz migração automática se necessário.
    """
    # Migra configurações antigas se necessário
    raw_settings = tenant.settings or {}
    migrated_settings = migrate_legacy_settings(raw_settings)
    
    # Merge com defaults para garantir todos os campos
    settings = deep_merge(DEFAULT_SETTINGS, migrated_settings)
    
    # Garante que company_name tenha valor
    if not settings["basic"].get("company_name"):
        settings["basic"]["company_name"] = tenant.name
    
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
        "options": {
            "niches": available_niches,
            "tones": TONE_OPTIONS,
            "personality_traits": PERSONALITY_TRAITS,
            "distribution_methods": DISTRIBUTION_METHODS,
            "fallback_options": FALLBACK_OPTIONS,
            "required_info_options": REQUIRED_INFO_OPTIONS,
        },
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
    Aceita atualizações parciais em qualquer nível.
    """
    # Migra configurações antigas se necessário
    raw_settings = tenant.settings or {}
    current_settings = migrate_legacy_settings(raw_settings)
    current_settings = deep_merge(DEFAULT_SETTINGS, current_settings)
    
    # Atualiza nome do tenant se enviado
    if "tenant_name" in payload and payload["tenant_name"]:
        tenant.name = payload["tenant_name"]
        del payload["tenant_name"]
    
    # Seções permitidas
    allowed_sections = [
        "identity",
        "basic",
        "ai_behavior",
        "handoff",
        "business_hours",
        "faq",
        "scope",
        "distribution",
        "guardrails",
        "messages",
    ]
    
    # Merge das seções
    for section in allowed_sections:
        if section in payload:
            if isinstance(payload[section], dict) and section in current_settings:
                current_settings[section] = deep_merge(
                    current_settings[section],
                    payload[section]
                )
            else:
                current_settings[section] = payload[section]
    
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


@router.get("/identity")
async def get_identity_settings(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    Retorna apenas as configurações de identidade empresarial.
    Útil para o painel simplificado.
    """
    raw_settings = tenant.settings or {}
    migrated_settings = migrate_legacy_settings(raw_settings)
    settings = deep_merge(DEFAULT_SETTINGS, migrated_settings)
    
    return {
        "identity": settings.get("identity", DEFAULT_SETTINGS["identity"]),
        "basic": settings.get("basic", DEFAULT_SETTINGS["basic"]),
        "options": {
            "tones": TONE_OPTIONS,
            "personality_traits": PERSONALITY_TRAITS,
            "required_info_options": REQUIRED_INFO_OPTIONS,
        },
    }


@router.patch("/identity")
async def update_identity_settings(
    payload: dict,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza apenas as configurações de identidade empresarial.
    """
    raw_settings = tenant.settings or {}
    current_settings = migrate_legacy_settings(raw_settings)
    current_settings = deep_merge(DEFAULT_SETTINGS, current_settings)
    
    # Atualiza identity
    if "identity" in payload:
        current_settings["identity"] = deep_merge(
            current_settings.get("identity", {}),
            payload["identity"]
        )
    
    # Atualiza basic
    if "basic" in payload:
        current_settings["basic"] = deep_merge(
            current_settings.get("basic", {}),
            payload["basic"]
        )
    
    tenant.settings = current_settings
    
    await db.commit()
    await db.refresh(tenant)
    
    return {
        "success": True,
        "message": "Identidade empresarial atualizada",
        "identity": current_settings["identity"],
        "basic": current_settings["basic"],
    }


@router.get("/ai-context")
async def get_ai_context(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna o contexto compilado para a IA.
    Útil para debug e para o motor de IA.
    """
    raw_settings = tenant.settings or {}
    migrated_settings = migrate_legacy_settings(raw_settings)
    settings = deep_merge(DEFAULT_SETTINGS, migrated_settings)
    
    identity = settings.get("identity", {})
    basic = settings.get("basic", {})
    
    # Compila contexto para a IA
    context = {
        "empresa": {
            "nome": basic.get("company_name") or tenant.name,
            "nicho": basic.get("niche"),
            "descricao": identity.get("description", ""),
        },
        "produtos_servicos": identity.get("products_services", []),
        "nao_oferecemos": identity.get("not_offered", []),
        "tom_comunicacao": {
            "tom": identity.get("tone_style", {}).get("tone", "cordial"),
            "personalidade": identity.get("tone_style", {}).get("personality_traits", []),
            "estilo": identity.get("tone_style", {}).get("communication_style", ""),
            "evitar": identity.get("tone_style", {}).get("avoid_phrases", []),
            "usar": identity.get("tone_style", {}).get("use_phrases", []),
        },
        "publico_alvo": identity.get("target_audience", {}),
        "regras_negocio": identity.get("business_rules", []),
        "diferenciais": identity.get("differentials", []),
        "palavras_chave": identity.get("keywords", []),
        "perguntas_obrigatorias": identity.get("required_questions", []),
        "informacoes_coletar": identity.get("required_info", []),
        "contexto_adicional": identity.get("additional_context", ""),
        "escopo": settings.get("scope", {}),
        "faq": settings.get("faq", {}).get("items", []),
        "guardrails": settings.get("guardrails", {}),
    }
    
    return context


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


@router.get("/tone-options")
async def get_tone_options():
    """
    Retorna opções de tom de voz disponíveis.
    """
    return {
        "tones": TONE_OPTIONS,
        "personality_traits": PERSONALITY_TRAITS,
    }