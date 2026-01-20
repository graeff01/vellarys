"""
ROTAS: CONFIGURAÇÕES (VERSÃO CORRIGIDA)
========================================

Endpoints para o gestor configurar o tenant.
Inclui a nova seção de Identidade Empresarial.

CORREÇÕES:
- Removida dependência de entidade Niche (usa lista fixa)
- Forçada detecção de mudanças no campo JSON
- Adicionados logs para debug
- flag_modified para garantir persistência
"""

import logging
import copy
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel, Field
from typing import Optional

from src.infrastructure.database import get_db
from src.domain.entities import Tenant, User
from src.api.dependencies import get_current_user, get_current_tenant

logger = logging.getLogger(__name__)

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
    # FOLLOW-UP AUTOMÁTICO (NOVO)
    # =========================================================================
    "follow_up": {
        "enabled": False,  # Desabilitado por padrão (gestor ativa)
        
        # Tempo de inatividade para disparar follow-up (em horas)
        "inactivity_hours": 24,
        
        # Máximo de tentativas de follow-up
        "max_attempts": 3,
        
        # Intervalo entre follow-ups (em horas)
        "interval_hours": 24,
        
        # Respeitar horário comercial?
        "respect_business_hours": True,
        
        # Mensagens personalizadas por tentativa
        "messages": {
            "attempt_1": "Oi {nome}! Vi que você se interessou por {interesse}. Posso te ajudar com mais alguma informação? 😊",
            "attempt_2": "Oi {nome}! Ainda está procurando {interesse}? Estou aqui se precisar!",
            "attempt_3": "{nome}, vou encerrar nosso atendimento por aqui. Se precisar, é só chamar novamente! 👋",
        },
        
        # Status de lead que NÃO recebem follow-up
        "exclude_statuses": ["converted", "lost", "handed_off"],
        
        # Qualificações que NÃO recebem follow-up
        "exclude_qualifications": [],
        
        # Horário permitido para envio (se não respeitar business_hours)
        "allowed_hours": {
            "start": "08:00",
            "end": "20:00",
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

    # =========================================================================
    # VOICE-FIRST / RESPOSTA EM ÁUDIO (NOVO)
    # =========================================================================
    "voice_response": {
        # Se ativado, quando o cliente enviar ÁUDIO, a IA responde com ÁUDIO
        "enabled": False,

        # Voz do OpenAI TTS a usar
        # Opções: nova (feminina jovem), shimmer (feminina suave),
        #         alloy (neutra), echo (masculina), onyx (masculina grave), fable (britânica)
        "voice": "nova",

        # Velocidade da fala (0.25 a 4.0, padrão 1.0)
        "speed": 1.0,

        # Se True, SEMPRE responde com áudio (mesmo se cliente mandou texto)
        # Se False, só responde áudio quando cliente manda áudio
        "always_audio": False,

        # Mensagem máxima para converter em áudio (caracteres)
        # Mensagens maiores são enviadas como texto
        "max_chars_for_audio": 500,

        # Nome da persona de voz (exibido no admin)
        "persona_name": "Ana",
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

# Opções de voz para Voice-First (OpenAI TTS)
VOICE_OPTIONS = [
    {
        "id": "nova",
        "name": "Nova",
        "description": "Feminina, jovem e acolhedora",
        "gender": "female",
        "recommended": True,
        "preview_text": "Olá! Sou a Ana, sua assistente virtual. Como posso ajudar?",
    },
    {
        "id": "shimmer",
        "name": "Shimmer",
        "description": "Feminina, suave e profissional",
        "gender": "female",
        "recommended": False,
        "preview_text": "Olá! Estou aqui para ajudar você a encontrar o imóvel ideal.",
    },
    {
        "id": "alloy",
        "name": "Alloy",
        "description": "Neutra, equilibrada e versátil",
        "gender": "neutral",
        "recommended": False,
        "preview_text": "Olá! Como posso ajudar você hoje?",
    },
    {
        "id": "echo",
        "name": "Echo",
        "description": "Masculina, grave e confiante",
        "gender": "male",
        "recommended": False,
        "preview_text": "Olá! Sou o assistente virtual. Em que posso ajudar?",
    },
    {
        "id": "onyx",
        "name": "Onyx",
        "description": "Masculina, profunda e séria",
        "gender": "male",
        "recommended": False,
        "preview_text": "Olá! Estou aqui para ajudar com suas dúvidas.",
    },
    {
        "id": "fable",
        "name": "Fable",
        "description": "Expressiva, articulada e dinâmica",
        "gender": "neutral",
        "recommended": False,
        "preview_text": "Olá! Que bom falar com você! Como posso ajudar?",
    },
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


# =============================================================================
# NICHOS DISPONÍVEIS (lista fixa, sem dependência de banco)
# =============================================================================

AVAILABLE_NICHES = [
    {"id": "services", "name": "Serviços", "description": "Prestação de serviços em geral", "icon": "🔧"},
    {"id": "retail", "name": "Varejo", "description": "Lojas e comércio", "icon": "🛒"},
    {"id": "health", "name": "Saúde", "description": "Clínicas e consultórios", "icon": "🏥"},
    {"id": "healthcare", "name": "Saúde", "description": "Clínicas e consultórios", "icon": "🏥"},
    {"id": "beauty", "name": "Beleza", "description": "Salões, estética e bem-estar", "icon": "💇"},
    {"id": "food", "name": "Alimentação", "description": "Restaurantes e delivery", "icon": "🍽️"},
    {"id": "education", "name": "Educação", "description": "Escolas e cursos", "icon": "📚"},
    {"id": "realestate", "name": "Imobiliário", "description": "Imóveis e corretagem", "icon": "🏠"},
    {"id": "automotive", "name": "Automotivo", "description": "Veículos e oficinas", "icon": "🚗"},
    {"id": "fashion", "name": "Moda", "description": "Roupas e acessórios", "icon": "👗"},
    {"id": "events", "name": "Eventos", "description": "Festas e celebrações", "icon": "🎉"},
    {"id": "tech", "name": "Tecnologia", "description": "Software e TI", "icon": "💻"},
    {"id": "legal", "name": "Jurídico", "description": "Advocacia e consultoria", "icon": "⚖️"},
    {"id": "fitness", "name": "Fitness", "description": "Academias e personal", "icon": "💪"},
    {"id": "pet", "name": "Pet", "description": "Pet shops e veterinárias", "icon": "🐕"},
    {"id": "other", "name": "Outro", "description": "Outros segmentos", "icon": "📦"},
]


def get_available_niches() -> list[dict]:
    """Retorna lista de nichos disponíveis."""
    return AVAILABLE_NICHES


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
    target_tenant_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna configurações atuais do tenant.
    Faz migração automática se necessário.
    
    Superadmin pode passar target_tenant_id para gerenciar outro cliente.
    """
    
    # Se for superadmin e tiver target_tenant_id, troca o tenant de contexto
    if target_tenant_id and user.role == "superadmin":
        logger.info(f"Superadmin {user.email} gerenciando settings do tenant_id {target_tenant_id}")
        result = await db.execute(select(Tenant).where(Tenant.id == target_tenant_id))
        target_tenant = result.scalar_one_or_none()
        if not target_tenant:
            raise HTTPException(404, "Tenant alvo não encontrado")
        tenant = target_tenant

    logger.info(f"Carregando settings para tenant {tenant.slug}")
    
    # Migra configurações antigas se necessário
    raw_settings = tenant.settings or {}
    migrated_settings = migrate_legacy_settings(raw_settings)
    
    # Merge com defaults para garantir todos os campos
    settings = deep_merge(DEFAULT_SETTINGS, migrated_settings)
    
    # Garante que company_name tenha valor
    if not settings["basic"].get("company_name"):
        settings["basic"]["company_name"] = tenant.name
    
    # Usa lista fixa de nichos (sem dependência de banco)
    available_niches = get_available_niches()
    
    logger.info(f"Settings carregados: {list(settings.keys())}")
    
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
            "voice_options": VOICE_OPTIONS,  # Voice-First
        },
    }


@router.patch("")
async def update_settings(
    payload: dict,
    target_tenant_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza configurações do tenant.
    Aceita atualizações parciais em qualquer nível.
    
    Superadmin pode passar target_tenant_id para gerenciar outro cliente.
    
    IMPORTANTE: Usa flag_modified para garantir que SQLAlchemy
    detecte mudanças em campos JSON/JSONB.
    """
    
    # Se for superadmin e tiver target_tenant_id, troca o tenant de contexto
    if target_tenant_id and user.role == "superadmin":
        logger.info(f"Superadmin {user.email} salvando settings do tenant_id {target_tenant_id}")
        result = await db.execute(select(Tenant).where(Tenant.id == target_tenant_id))
        target_tenant = result.scalar_one_or_none()
        if not target_tenant:
            raise HTTPException(404, "Tenant alvo não encontrado")
        tenant = target_tenant

    logger.info(f"Atualizando settings para tenant {tenant.slug}")
    logger.info(f"Payload recebido: {list(payload.keys())}")
    
    try:
        # Migra configurações antigas se necessário
        raw_settings = tenant.settings or {}
        current_settings = migrate_legacy_settings(raw_settings)
        current_settings = deep_merge(DEFAULT_SETTINGS, current_settings)
        
        # IMPORTANTE: Fazer deep copy para garantir que é um novo objeto
        new_settings = copy.deepcopy(current_settings)
        
        # Atualiza nome do tenant se enviado
        if "tenant_name" in payload and payload["tenant_name"]:
            tenant.name = payload["tenant_name"]
            logger.info(f"Nome do tenant atualizado para: {tenant.name}")
        
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
            "follow_up",
            "messages",
            "voice_response",  # Voice-First
        ]
        
        # Merge das seções
        for section in allowed_sections:
            if section in payload:
                logger.info(f"Atualizando seção: {section}")
                if isinstance(payload[section], dict) and section in new_settings:
                    new_settings[section] = deep_merge(
                        new_settings[section],
                        payload[section]
                    )
                else:
                    new_settings[section] = payload[section]
        
        # CRÍTICO: Atribui novo objeto e marca como modificado
        tenant.settings = new_settings
        flag_modified(tenant, "settings")
        
        logger.info(f"Settings atualizados, fazendo commit...")
        
        await db.commit()
        await db.refresh(tenant)
        
        logger.info(f"Commit realizado com sucesso!")
        logger.info(f"Identity salva: {tenant.settings.get('identity', {}).get('description', 'vazio')[:50]}")
        
        return {
            "success": True,
            "message": "Configurações atualizadas com sucesso",
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "plan": tenant.plan,
            },
            "settings": tenant.settings,
        }
        
    except Exception as e:
        logger.error(f"Erro ao salvar settings: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(500, f"Erro ao salvar: {str(e)}")


@router.get("/identity")
async def get_identity_settings(
    target_tenant_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna apenas as configurações de identidade empresarial.
    Útil para o painel simplificado.
    """
    if target_tenant_id and user.role == "superadmin":
        result = await db.execute(select(Tenant).where(Tenant.id == target_tenant_id))
        target_tenant = result.scalar_one_or_none()
        if not target_tenant:
            raise HTTPException(404, "Tenant alvo não encontrado")
        tenant = target_tenant

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
    target_tenant_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza apenas as configurações de identidade empresarial.
    """
    if target_tenant_id and user.role == "superadmin":
        result = await db.execute(select(Tenant).where(Tenant.id == target_tenant_id))
        target_tenant = result.scalar_one_or_none()
        if not target_tenant:
            raise HTTPException(404, "Tenant alvo não encontrado")
        tenant = target_tenant

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
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(tenant, "settings")
    
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
async def list_niches():
    """
    Lista todos os nichos disponíveis.
    """
    return get_available_niches()


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