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

    # =========================================================================
    # MODO DE HANDOFF (crm_inbox ou whatsapp_pessoal)
    # =========================================================================
    "handoff_mode": "whatsapp_pessoal",

    # =========================================================================
    # FEATURE FLAGS (CENTRO DE CONTROLE DO GESTOR)
    # =========================================================================
    "features": {
        # Core Features (TODAS as features devem estar aqui)
        "calendar_enabled": True,
        "templates_enabled": True,
        "notes_enabled": True,
        "attachments_enabled": True,

        # Communication
        "sse_enabled": True,
        "search_enabled": True,

        # Advanced Features
        "metrics_enabled": True,
        "archive_enabled": True,
        "voice_response_enabled": True,
        "ai_auto_handoff_enabled": True,
        "ai_sentiment_alerts_enabled": True,

        # Security & Control
        "security_ghost_mode_enabled": True,
        "security_export_lock_enabled": False,  # False = exportação liberada
        "distrib_auto_assign_enabled": True,

        # Experimental Features
        "ai_guard_enabled": True,
        "reengagement_enabled": True,
        "knowledge_base_enabled": True,
    },
}

# =============================================================================
# ⭐ MAPEAMENTO DE FUNCIONALIDADES POR PLANO
# =============================================================================
#
# 🟢 STARTER (Essencial) - Para começar a usar o sistema
#    → Funcionalidades básicas de atendimento
#    → Sem IA avançada, sem relatórios, sem exportação
#
# 🔵 PREMIUM (Profissional) - Para escalar o negócio
#    → Tudo do Starter + Analytics + IA + Exportação
#    → Ideal para empresas em crescimento
#
# 🟣 ENTERPRISE (Completo) - Poder total
#    → TODAS as funcionalidades liberadas
#    → IA avançada, automações, API, base de conhecimento
#    → Para operações de alta escala
#
# =============================================================================

PLAN_FEATURES = {
    # =========================================================================
    # 🟢 STARTER - Plano Essencial (Básico)
    # =========================================================================
    "starter": {
        # ✅ Core - Funcionalidades básicas
        "calendar_enabled": True,
        "templates_enabled": True,
        "notes_enabled": True,
        "attachments_enabled": True,

        # ✅ Comunicação básica
        "sse_enabled": True,
        "search_enabled": True,

        # ❌ Advanced - Não disponível
        "metrics_enabled": False,
        "archive_enabled": False,
        "voice_response_enabled": False,
        "ai_auto_handoff_enabled": False,
        "ai_sentiment_alerts_enabled": False,

        # 🔒 Security - Apenas export lock ativo (bloqueado)
        "security_ghost_mode_enabled": False,
        "security_export_lock_enabled": True,  # BLOQUEADO no starter
        "distrib_auto_assign_enabled": False,

        # ❌ Experimental - Não disponível
        "ai_guard_enabled": False,
        "reengagement_enabled": False,
        "knowledge_base_enabled": False,

        # ✅ Inteligência - Parcialmente disponível
        "copilot_enabled": False,        # Apenas Premium+
        "simulator_enabled": True,       # TODOS os planos
        "reports_enabled": True,         # TODOS os planos
        "export_enabled": True,          # TODOS os planos
    },

    # =========================================================================
    # 🔵 PREMIUM - Plano Profissional (Intermediário)
    # =========================================================================
    "premium": {
        # ✅ Core - Completo
        "calendar_enabled": True,
        "templates_enabled": True,
        "notes_enabled": True,
        "attachments_enabled": True,

        # ✅ Comunicação
        "sse_enabled": True,
        "search_enabled": True,

        # ✅ Advanced - Tudo liberado
        "metrics_enabled": True,
        "archive_enabled": True,
        "voice_response_enabled": True,
        "ai_auto_handoff_enabled": True,
        "ai_sentiment_alerts_enabled": True,

        # ✅ Security - Tudo liberado
        "security_ghost_mode_enabled": True,
        "security_export_lock_enabled": False,  # LIBERADO no premium
        "distrib_auto_assign_enabled": True,

        # ❌ Experimental - Não disponível (só no enterprise)
        "ai_guard_enabled": False,
        "reengagement_enabled": False,
        "knowledge_base_enabled": False,

        # ✅ Inteligência - TUDO liberado
        "copilot_enabled": True,         # Premium+
        "simulator_enabled": True,       # TODOS os planos
        "reports_enabled": True,         # TODOS os planos
        "export_enabled": True,          # TODOS os planos
    },

    # =========================================================================
    # 🟣 ENTERPRISE - Plano Completo (TUDO)
    # =========================================================================
    "enterprise": {
        # ✅ Core - Completo
        "calendar_enabled": True,
        "templates_enabled": True,
        "notes_enabled": True,
        "attachments_enabled": True,

        # ✅ Comunicação
        "sse_enabled": True,
        "search_enabled": True,

        # ✅ Advanced - Completo
        "metrics_enabled": True,
        "archive_enabled": True,
        "voice_response_enabled": True,
        "ai_auto_handoff_enabled": True,
        "ai_sentiment_alerts_enabled": True,

        # ✅ Security - Completo
        "security_ghost_mode_enabled": True,
        "security_export_lock_enabled": False,  # LIBERADO
        "distrib_auto_assign_enabled": True,

        # ✅ Experimental - TUDO LIBERADO 🚀
        "ai_guard_enabled": True,
        "reengagement_enabled": True,
        "knowledge_base_enabled": True,  # Mesmo "Coming Soon", está no plano

        # ✅ Inteligência - TUDO liberado
        "copilot_enabled": True,         # Premium+
        "simulator_enabled": True,       # TODOS os planos
        "reports_enabled": True,         # TODOS os planos
        "export_enabled": True,          # TODOS os planos
    }
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

# Opções de voz para Voice-First (OpenAI + Google)
VOICE_OPTIONS = [
    # ========== VOZES BRASILEIRAS (Google Cloud) ==========
    {
        "id": "camila",
        "name": "Camila 🇧🇷",
        "description": "Feminina, brasileira e natural (Recomendada)",
        "gender": "female",
        "recommended": True,
        "provider": "google",
        "preview_text": "Olá! Tudo bem? Sou a Camila, sua assistente virtual brasileira. Estou aqui para te ajudar com o que precisar. Pode me contar, o que você está procurando?",
    },
    {
        "id": "vitoria",
        "name": "Vitória 🇧🇷",
        "description": "Feminina, brasileira e jovem",
        "gender": "female",
        "recommended": False,
        "provider": "google",
        "preview_text": "Oi! Que bom ter você por aqui! Sou a Vitória e vou te ajudar a encontrar exatamente o que você procura. Vamos começar?",
    },
    {
        "id": "ricardo",
        "name": "Ricardo 🇧🇷",
        "description": "Masculina, brasileiro e profissional",
        "gender": "male",
        "recommended": False,
        "provider": "google",
        "preview_text": "E aí! Tudo certo? Sou o Ricardo, assistente virtual, e estou aqui pra te dar uma mão no que você precisar. Me conta, em que posso ajudar?",
    },
    # ========== VOZES INTERNACIONAIS (OpenAI) ==========
    {
        "id": "nova",
        "name": "Nova",
        "description": "Feminina, jovem e natural",
        "gender": "female",
        "recommended": False,
        "provider": "openai",
        "preview_text": "Olá! Tudo bem? Sou a sua assistente virtual e estou aqui para te ajudar com o que precisar. Pode me contar, o que você está procurando?",
    },
    {
        "id": "shimmer",
        "name": "Shimmer",
        "description": "Feminina, calorosa e acolhedora",
        "gender": "female",
        "recommended": False,
        "provider": "openai",
        "preview_text": "Oi! Que bom ter você por aqui! Sou a assistente virtual e vou te ajudar a encontrar exatamente o que você procura. Vamos começar?",
    },
    {
        "id": "alloy",
        "name": "Alloy",
        "description": "Neutra, clara e amigável",
        "gender": "neutral",
        "recommended": False,
        "provider": "openai",
        "preview_text": "Olá! É um prazer falar com você. Estou aqui para tirar suas dúvidas e te ajudar no que for preciso. Como posso te auxiliar hoje?",
    },
    {
        "id": "echo",
        "name": "Echo",
        "description": "Masculina, confiante e amigável",
        "gender": "male",
        "recommended": False,
        "provider": "openai",
        "preview_text": "E aí! Tudo certo? Sou o assistente virtual e estou aqui pra te dar uma mão no que você precisar. Me conta, em que posso ajudar?",
    },
    {
        "id": "onyx",
        "name": "Onyx",
        "description": "Masculina, séria e profissional",
        "gender": "male",
        "recommended": False,
        "provider": "openai",
        "preview_text": "Olá. Sou o assistente virtual responsável por atendê-lo. Estou à disposição para esclarecer suas dúvidas. Qual é sua necessidade?",
    },
    {
        "id": "fable",
        "name": "Fable",
        "description": "Expressiva, dinâmica e entusiasmada",
        "gender": "neutral",
        "recommended": False,
        "provider": "openai",
        "preview_text": "Oi! Que legal você estar aqui! Sou a assistente virtual e estou super animada para te ajudar! Me conta tudo, o que você precisa hoje?",
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
        "services_status": {
            "resend_configured": bool(get_settings().resend_api_key),
            "openai_configured": bool(get_settings().openai_api_key),
        },
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

        # 🆕 Atualiza handoff_mode (CRM Inbox ou WhatsApp Pessoal)
        if "handoff_mode" in payload:
            if payload["handoff_mode"] not in ["crm_inbox", "whatsapp_pessoal"]:
                raise HTTPException(
                    status_code=400,
                    detail="handoff_mode deve ser 'crm_inbox' ou 'whatsapp_pessoal'",
                )
            new_settings["handoff_mode"] = payload["handoff_mode"]
            logger.info(f"handoff_mode atualizado para: {payload['handoff_mode']}")

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


@router.get("/voice-preview/{voice_id}")
async def get_voice_preview(
    voice_id: str,
    user: User = Depends(get_current_user),
):
    """
    Gera preview de áudio da voz selecionada.
    Detecta automaticamente o provedor (OpenAI ou Google).
    Retorna base64 do áudio MP3.
    """
    from src.infrastructure.services.tts_service import get_tts_service
    from src.infrastructure.services.google_tts_service import get_google_tts_service
    import base64

    # Busca informações da voz
    preview_text = "Olá! Esta é uma demonstração da voz selecionada."
    provider = "openai"  # Padrão

    for voice_opt in VOICE_OPTIONS:
        if voice_opt["id"] == voice_id:
            preview_text = voice_opt.get("preview_text", preview_text)
            provider = voice_opt.get("provider", "openai")
            break

    try:
        # Seleciona o provedor correto
        if provider == "google":
            logger.info(f"🇧🇷 Usando Google TTS para voz '{voice_id}'")
            tts = get_google_tts_service()
            audio_bytes = await tts.generate_audio_bytes(
                text=preview_text,
                voice=voice_id,
                speed=0.95,
            )
        else:
            logger.info(f"🌐 Usando OpenAI TTS para voz '{voice_id}'")
            tts = get_tts_service()
            audio_bytes = await tts.generate_audio_bytes(
                text=preview_text,
                voice=voice_id,
                speed=0.95,
                output_format="mp3"
            )

        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            return {
                "success": True,
                "audio_base64": audio_b64,
                "mime_type": "audio/mpeg",
                "voice_id": voice_id,
                "provider": provider,
                "text": preview_text,
            }
        else:
            raise HTTPException(status_code=500, detail="Erro ao gerar áudio")

    except Exception as e:
        logger.error(f"❌ Erro ao gerar preview de voz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RAG - REINDEXAÇÃO DE FAQ
# =============================================================================

@router.post("/faq/reindex")
async def reindex_faq(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-indexa o FAQ na base de embeddings para busca semântica (RAG).

    Deve ser chamado após atualizar o FAQ para que as mudanças
    sejam refletidas nas respostas da IA.

    Returns:
        Estatísticas da indexação: created, updated, skipped, failed
    """
    from src.infrastructure.services.knowledge_rag_service import index_faq_items

    try:
        # Obtém FAQ dos settings
        faq_config = tenant.settings.get("faq", {}) if tenant.settings else {}
        faq_items = faq_config.get("items", [])

        if not faq_items:
            return {
                "success": True,
                "message": "Nenhum FAQ para indexar",
                "stats": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
            }

        # Indexa FAQ
        stats = await index_faq_items(
            db=db,
            tenant_id=tenant.id,
            faq_items=faq_items,
            clear_existing=False,  # Não remove itens antigos
        )

        return {
            "success": True,
            "message": f"FAQ re-indexado com sucesso ({stats['created']} criados, {stats['updated']} atualizados)",
            "stats": stats,
            "total_items": len(faq_items),
        }

    except Exception as e:
        logger.error(f"❌ Erro ao re-indexar FAQ: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao re-indexar FAQ: {str(e)}")


@router.get("/faq/index-status")
async def get_faq_index_status(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna status da indexação de FAQ/base de conhecimento.
    """
    from src.infrastructure.services.knowledge_rag_service import get_index_stats

    try:
        stats = await get_index_stats(db, tenant.id)

        # Conta FAQs nos settings
        faq_config = tenant.settings.get("faq", {}) if tenant.settings else {}
        faq_items = faq_config.get("items", [])

        return {
            "success": True,
            "faq_in_settings": len(faq_items),
            "indexed": stats,
            "needs_reindex": stats.get("by_type", {}).get("faq", 0) < len(faq_items),
        }

    except Exception as e:
        logger.error(f"❌ Erro ao obter status do índice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# FEATURE FLAGS (CENTRO DE CONTROLE)
# =============================================================================

@router.get("/features")
async def get_features(
    target_tenant_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna feature flags do tenant (Centro de Controle).

    🔴 HIERARQUIA COMPLETA:
    ===============================================
    1. SuperAdmin:
       - Controla TUDO de TODOS os clientes
       - Pode editar features de qualquer cliente via target_tenant_id
       - Pode alterar PLANO de qualquer cliente

    2. Gestor (Admin/Manager):
       - Controla features da PRÓPRIA empresa
       - Pode ATIVAR/DESATIVAR features dentro do plano
       - NÃO pode ativar além do plano contratado

    3. Vendedor:
       - Vê apenas team_features (o que gestor liberou)

    Lógica de Resolução:
    ===============================================
    Final Features = Plan Features (do plano contratado)
                   + Team Features (o que gestor/admin configurou)
    """

    # SuperAdmin pode gerenciar outro tenant
    if target_tenant_id and user.role == "superadmin":
        logger.info(f"🔴 [SUPERADMIN] {user.email} consultando features do tenant_id {target_tenant_id}")
        result = await db.execute(select(Tenant).where(Tenant.id == target_tenant_id))
        target_tenant = result.scalar_one_or_none()
        if not target_tenant:
            raise HTTPException(404, "Cliente não encontrado")
        tenant = target_tenant

    logger.info(f"🎛️ [FEATURES GET] Tenant: {tenant.name} (ID: {tenant.id}) | User Role: {user.role}")

    # 1. Busca features do PLANO
    plan_features = {}
    plan_name = "starter"  # Fallback padrão
    plan_slug_from_db = None

    try:
        from src.domain.entities.tenant_subscription import TenantSubscription
        from sqlalchemy.orm import selectinload

        stmt = select(TenantSubscription).where(
            TenantSubscription.tenant_id == tenant.id
        ).options(selectinload(TenantSubscription.plan))

        result = await db.execute(stmt)
        sub = result.scalar_one_or_none()

        if sub and sub.plan:
            plan_features = sub.plan.features or {}
            plan_slug_from_db = (sub.plan.slug or sub.plan.name or "").lower().strip()
            plan_name = sub.plan.slug or sub.plan.name
            logger.info(f"✅ Features do plano '{plan_name}' carregadas do DB")
    except Exception as e:
        logger.error(f"⚠️ Erro ao buscar plano do banco: {e}")

    # Se as features do DB não usam as chaves esperadas pelo app (ex.: calendar_enabled),
    # fazemos fallback para o mapeamento interno PLAN_FEATURES baseado no slug do plano.
    expected_feature_keys = set(DEFAULT_SETTINGS["features"].keys())
    if plan_features and not (set(plan_features.keys()) & expected_feature_keys):
        logger.warning(
            "⚠️ Features do plano no DB não batem com as chaves esperadas do app. "
            f"Exemplo chaves DB: {list(plan_features.keys())[:8]}"
        )
        plan_features = {}

    # Fallback para PLAN_FEATURES hardcoded se não carregou do banco
    if not plan_features:
        # Normaliza o nome do plano (remove espaços, lowercase)
        plan_slug = (plan_slug_from_db or tenant.plan or "premium").lower().strip()
        plan_slug = plan_slug.replace("_", "-")

        # Aliases comuns vindos do DB / legacy
        plan_slug_aliases = {
            "enterprise-plus": "enterprise",
            "enterprise_plus": "enterprise",
            "essencial": "starter",
            "essential": "starter",
            "starter-plus": "starter",
            "premium-plus": "premium",
            "professional": "premium",
            "pro": "premium",
        }
        plan_slug = plan_slug_aliases.get(plan_slug, plan_slug)

        # Tenta encontrar o plano
        if plan_slug in PLAN_FEATURES:
            plan_features = PLAN_FEATURES[plan_slug]
            plan_name = plan_slug
        else:
            # Se não encontrou, usa premium como padrão (ao invés de starter)
            logger.warning(f"⚠️ Plano '{plan_slug}' não encontrado, usando 'premium' como padrão")
            plan_features = PLAN_FEATURES["premium"]
            plan_name = "premium"

        logger.info(f"ℹ️ Usando PLAN_FEATURES hardcoded para '{plan_name}': {len(plan_features)} features")

    # 2. Overrides do SuperAdmin (Admin Master) - fica separado do controle do gestor
    #    Motivo: gestor não deve "herdar" flags fora do plano em team_features,
    #    senão o PATCH do gestor falha na validação de plano.
    settings = tenant.settings or {}
    feature_overrides = settings.get("feature_overrides", {}) or {}

    # 3. Gestor Team Controls (o que o gestor ativou/desativou)
    team_features_raw = settings.get("team_features", {}) or {}

    # Para gestor/admin, nunca devolvemos "team_features" com chaves fora do plano,
    # porque o frontend salva exatamente `team_features` e isso causaria 403.
    if user.role in ["admin", "gestor"]:
        team_features = {k: v for k, v in team_features_raw.items() if k in plan_features}
    else:
        team_features = team_features_raw

    # 4. Merge Final (plan + overrides + team_features)
    # Ordem: team_features por último para permitir que configurações do time sobrescrevam
    # (ex.: desligar uma feature que estava ligada via override).
    final_features = {**plan_features, **feature_overrides, **team_features}

    return {
        "plan_features": plan_features,
        "overrides": feature_overrides,
        "team_features": team_features,      # Gestor controls
        "final_features": final_features,
        "plan_name": sub.plan.name if 'sub' in locals() and sub and sub.plan else tenant.plan,
        "user_role": user.role,
        "can_edit": user.role in ["admin", "gestor"]  # Apenas gestor pode editar
    }


@router.patch("/features")
async def update_features(
    features: dict,
    target_tenant_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza feature flags (Centro de Controle).

    🔴 HIERARQUIA COMPLETA:
    ===============================================
    1. SuperAdmin:
       - Pode alterar features de QUALQUER cliente
       - Usa target_tenant_id para gerenciar clientes
       - Salva em "team_features" do cliente

    2. Gestor (Admin/Manager):
       - Pode ATIVAR/DESATIVAR features da própria empresa
       - Salva em "team_features"
       - NÃO pode ativar features além do plano

    3. Vendedor:
       - SEM permissão para alterar features
    """

    # ==========================================
    # 1. VALIDAÇÃO DE PERMISSÕES
    # ==========================================
    if user.role not in ["superadmin", "admin", "gestor"]:
        logger.warning(f"⛔ Acesso negado: {user.email} (role: {user.role}) tentou alterar features")
        raise HTTPException(403, "Apenas gestores e administradores podem alterar features")

    # SuperAdmin pode gerenciar outro tenant
    is_managing_other_tenant = False
    if target_tenant_id and user.role == "superadmin":
        logger.info(f"🔴 [SUPERADMIN] {user.email} alterando features do tenant_id {target_tenant_id}")
        result = await db.execute(select(Tenant).where(Tenant.id == target_tenant_id))
        target_tenant = result.scalar_one_or_none()
        if not target_tenant:
            raise HTTPException(404, "Cliente não encontrado")
        tenant = target_tenant
        is_managing_other_tenant = True
    elif target_tenant_id and user.role != "superadmin":
        # Não-superadmin tentando gerenciar outro tenant
        logger.warning(f"⛔ {user.email} tentou gerenciar tenant {target_tenant_id} sem permissão")
        raise HTTPException(403, "Apenas SuperAdmin pode gerenciar outros clientes")

    logger.info(f"🎛️ [FEATURES PATCH] Tenant: {tenant.name} | User: {user.email} (role: {user.role})")

    try:
        # ==========================================
        # 2. VALIDAÇÃO DE FEATURES
        # ==========================================
        valid_features = set(DEFAULT_SETTINGS["features"].keys())
        invalid_keys = set(features.keys()) - valid_features

        if invalid_keys:
            logger.error(f"❌ Features inválidas: {invalid_keys}")
            raise HTTPException(400, f"Features inválidas: {', '.join(invalid_keys)}")

        non_bool_values = [k for k, v in features.items() if not isinstance(v, bool)]
        if non_bool_values:
            logger.error(f"❌ Valores não-booleanos: {non_bool_values}")
            raise HTTPException(400, f"Features devem ser booleanas: {', '.join(non_bool_values)}")

        # ==========================================
        # 3. BUSCAR FEATURES DO PLANO
        # ==========================================
        plan_features = {}
        plan_name = "starter"  # Fallback padrão
        plan_slug_from_db = None

        try:
            from src.domain.entities.tenant_subscription import TenantSubscription
            from sqlalchemy.orm import selectinload

            stmt = select(TenantSubscription).where(
                TenantSubscription.tenant_id == tenant.id
            ).options(selectinload(TenantSubscription.plan))

            result = await db.execute(stmt)
            sub = result.scalar_one_or_none()

            if sub and sub.plan:
                plan_features = sub.plan.features or {}
                plan_slug_from_db = (sub.plan.slug or sub.plan.name or "").lower().strip()
                plan_name = sub.plan.slug or sub.plan.name
                logger.info(f"✅ Features do plano '{plan_name}' carregadas do DB")
        except Exception as e:
            logger.error(f"⚠️ Erro ao buscar plano do banco: {e}")

        expected_feature_keys = set(DEFAULT_SETTINGS["features"].keys())
        if plan_features and not (set(plan_features.keys()) & expected_feature_keys):
            logger.warning(
                "⚠️ Features do plano no DB não batem com as chaves esperadas do app. "
                f"Exemplo chaves DB: {list(plan_features.keys())[:8]}"
            )
            plan_features = {}

        # Fallback para PLAN_FEATURES hardcoded se não carregou do banco
        if not plan_features:
            # Normaliza o nome do plano (remove espaços, lowercase)
            plan_slug = (plan_slug_from_db or tenant.plan or "premium").lower().strip()
            plan_slug = plan_slug.replace("_", "-")

            plan_slug_aliases = {
                "enterprise-plus": "enterprise",
                "enterprise_plus": "enterprise",
                "essencial": "starter",
                "essential": "starter",
                "starter-plus": "starter",
                "premium-plus": "premium",
                "professional": "premium",
                "pro": "premium",
            }
            plan_slug = plan_slug_aliases.get(plan_slug, plan_slug)

            # Tenta encontrar o plano
            if plan_slug in PLAN_FEATURES:
                plan_features = PLAN_FEATURES[plan_slug]
                plan_name = plan_slug
            else:
                # Se não encontrou, usa premium como padrão (ao invés de starter)
                logger.warning(f"⚠️ Plano '{plan_slug}' não encontrado em PLAN_FEATURES, usando 'premium' como padrão")
                plan_features = PLAN_FEATURES["premium"]
                plan_name = "premium"

            logger.info(f"ℹ️ Usando PLAN_FEATURES hardcoded para '{plan_name}': {len(plan_features)} features")

        # ==========================================
        # 4. VALIDAÇÃO: GESTOR NÃO PODE ATIVAR ALÉM DO PLANO
        # ==========================================
        # SuperAdmin pode ativar qualquer feature (via overrides)
        # Gestor/Admin só pode ativar dentro do plano (false sempre permitido)
        if user.role in ["admin", "gestor"] and not is_managing_other_tenant:
            logger.info(f"📋 Validando features do gestor. Plano: {plan_name}")
            logger.info(f"📋 Plan features disponíveis: {list(plan_features.keys())}")
            logger.info(f"📋 Features sendo enviadas: {features}")

            for feature_key, feature_value in features.items():
                plan_allows = plan_features.get(feature_key, False)
                if feature_value and not plan_allows:
                    logger.error(f"⛔ Gestor tentou ativar '{feature_key}' fora do plano '{plan_name}'")
                    logger.error(f"⛔ Feature '{feature_key}' no plano: {plan_allows}")
                    logger.error(f"⛔ Todas features do plano: {plan_features}")
                    raise HTTPException(
                        403,
                        f"Feature '{feature_key}' não disponível no plano {plan_name.upper()}. Entre em contato para fazer upgrade."
                    )

        # ==========================================
        # 5. SALVAR FEATURES
        # ==========================================
        current_settings = copy.deepcopy(tenant.settings or {})

        # SuperAdmin (Admin Master) salva em "feature_overrides" para não conflitar com validação do gestor
        if user.role == "superadmin":
            if "feature_overrides" not in current_settings:
                current_settings["feature_overrides"] = {}
            current_settings["feature_overrides"].update(features)
            logger.info(f"🟣 SuperAdmin feature_overrides atualizado: {features}")

            # Higieniza dados legados: se antes o superadmin gravou fora do plano em team_features,
            # removemos para não quebrar o gestor.
            if "team_features" in current_settings and isinstance(current_settings["team_features"], dict):
                for k in list(features.keys()):
                    if k in current_settings["team_features"]:
                        current_settings["team_features"].pop(k, None)
        else:
            # Gestor/admin salva em "team_features"
            if "team_features" not in current_settings:
                current_settings["team_features"] = {}
            current_settings["team_features"].update(features)
            logger.info(f"🟡 Gestor team_features atualizado: {features}")

        # Commit
        tenant.settings = current_settings
        flag_modified(tenant, "settings")

        await db.commit()
        await db.refresh(tenant)

        logger.info(f"✅ Features salvas com sucesso!")

        return {
            "success": True,
            "message": "Funcionalidades atualizadas com sucesso",
            "features": features
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar features: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(500, f"Erro ao atualizar: {str(e)}")