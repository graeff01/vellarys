"""
CASO DE USO: PROCESSAR MENSAGEM (VERSÃO ROBUSTA COM IDENTIDADE EMPRESARIAL)
=====================================================================

Fluxo principal quando um lead envia uma mensagem.
Inclui:
- Memória de contexto (retomar conversa)
- Detecção de sentimento
- Respostas personalizadas
- Segurança completa
- 🔒 PROTEÇÃO ANTI-ALUCINAÇÃO FORTIFICADA
- 🏢 IDENTIDADE EMPRESARIAL COM ESCOPO RÍGIDO
- 🛡️ TRATAMENTO DE ERROS ROBUSTO
"""

import logging
import traceback
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Tenant, Lead, Message, Channel, LeadEvent, Notification
from src.domain.entities.enums import LeadStatus, EventType
from src.domain.prompts import build_system_prompt, get_niche_config
from src.infrastructure.services import (
    chat_completion,
    extract_lead_data,
    qualify_lead,
    generate_lead_summary,
    execute_handoff,
    run_ai_guards_async,
    mark_lead_activity,
)

from src.infrastructure.services.openai_service import (
    detect_sentiment,
    generate_context_aware_response,
    generate_conversation_summary,
    calculate_typing_delay,
)

from src.infrastructure.services.ai_security import (
    build_security_instructions,
    sanitize_response,
    should_handoff as check_ai_handoff,
)

from src.infrastructure.services.security_service import (
    run_security_check,
    get_safe_response_for_threat,
    ThreatLevel,
)
from src.infrastructure.services.message_rate_limiter import (
    check_message_rate_limit,
    get_rate_limit_response,
)
# ✅ IMPORTAÇÃO CORRETA E ÚNICA
from src.infrastructure.services.audit_service import (
    log_message_received,
    log_security_threat,
    log_ai_action,
    log_audit,  # ✅ CERTIFIQUE-SE QUE ESTÁ AQUI
    AuditAction,
    AuditSeverity,
)
from src.infrastructure.services.lgpd_service import (
    detect_lgpd_request,
    get_lgpd_response,
    export_lead_data,
    delete_lead_data,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES E CONFIGURAÇÕES
# =============================================================================

MAX_MESSAGE_LENGTH = 2000  # Caracteres
MAX_CONVERSATION_HISTORY = 30
MAX_RETRIES = 2
FALLBACK_RESPONSES = {
    "error": "Desculpe, estou com uma instabilidade momentânea. Tente novamente em alguns segundos.",
    "out_of_scope": "Desculpe, não posso ajudá-lo com isso. Meu foco é exclusivo em [NEGÓCIO DO CLIENTE].",
    "rate_limit": "Estou recebendo muitas mensagens simultâneas. Tente novamente em alguns minutos.",
    "security": "Por segurança, não posso responder a essa mensagem. Entre em contato com nosso suporte.",}

# =============================================================================
# HELPER: MIGRAR SETTINGS LEGADO PARA NOVO FORMATO
# =============================================================================

def migrate_settings_if_needed(settings: dict) -> dict:
    """
    Migra settings do formato antigo para o novo (com identity).
    Mantém compatibilidade com tenants existentes.
    """
    if not settings:
        return {}
    
    # Se já tem "identity", está no novo formato
    if "identity" in settings:
        return settings
    
    try:
        # Migração do formato antigo
        migrated = dict(settings)  # Copia para não modificar original
        
        # Cria estrutura de identity baseada nos campos antigos
        migrated["identity"] = {
            "description": settings.get("scope_description", ""),
            "products_services": [],
            "not_offered": [],
            "tone_style": {
                "tone": settings.get("tone", "cordial"),
                "personality_traits": [],
                "communication_style": "",
                "avoid_phrases": [],
                "use_phrases": [],
            },
            "target_audience": {
                "description": "",
                "segments": [],
                "pain_points": [],
            },
            "business_rules": settings.get("custom_rules", []),
            "differentials": [],
            "keywords": [],
            "required_questions": settings.get("custom_questions", []),
            "required_info": [],
            "additional_context": "",
        }
        
        # Cria estrutura de basic
        migrated["basic"] = {
            "niche": settings.get("niche", "services"),
            "company_name": settings.get("company_name", ""),
        }
        
        # Cria estrutura de scope
        migrated["scope"] = {
            "enabled": settings.get("scope_enabled", True),
            "description": settings.get("scope_description", ""),
            "allowed_topics": [],
            "blocked_topics": [],
            "out_of_scope_message": settings.get("out_of_scope_message", 
                "Desculpe, não tenho informações sobre isso. Posso ajudar com nossos produtos e serviços!"),
        }
        
        # Cria estrutura de faq
        migrated["faq"] = {
            "enabled": settings.get("faq_enabled", True),
            "items": settings.get("faq_items", []),
        }
        
        return migrated
    except Exception as e:
        logger.error(f"Erro migrando settings: {e}")
        return settings


# =============================================================================
# HELPER: EXTRAIR CONTEXTO DE IA DO TENANT
# =============================================================================

def extract_ai_context(tenant: Tenant) -> dict:
    """
    Extrai e organiza todo o contexto necessário para a IA.
    Retorna dicionário com todos os parâmetros para build_system_prompt.
    """
    try:
        settings = migrate_settings_if_needed(tenant.settings or {})
        
        # Extrai seções
        identity = settings.get("identity", {})
        basic = settings.get("basic", {})
        scope = settings.get("scope", {})
        faq = settings.get("faq", {})
        
        # Determina valores com fallback
        company_name = basic.get("company_name") or settings.get("company_name") or tenant.name
        niche_id = basic.get("niche") or settings.get("niche") or "services"
        tone = identity.get("tone_style", {}).get("tone") or settings.get("tone") or "cordial"
        
        # FAQ items
        faq_items = []
        if faq.get("enabled", True):
            faq_items = faq.get("items", []) or settings.get("faq_items", [])
        
        # Custom questions e rules (do identity ou legado)
        custom_questions = identity.get("required_questions", []) or settings.get("custom_questions", [])
        custom_rules = identity.get("business_rules", []) or settings.get("custom_rules", [])
        
        # Scope description (do scope ou legado)
        scope_description = scope.get("description") or settings.get("scope_description", "")
        
        # Out of scope message (com fallback específico para o negócio)
        default_out_of_scope = (
            f"Desculpe, não posso ajudá-lo com isso. "
            f"A {company_name} trabalha exclusivamente com {scope_description or 'nossos produtos e serviços'}. "
            f"Posso te ajudar com algo relacionado?"
        )
        
        out_of_scope_message = scope.get("out_of_scope_message") or settings.get("out_of_scope_message") or default_out_of_scope
        
        return {
            "company_name": company_name,
            "niche_id": niche_id,
            "tone": tone,
            "identity": identity if identity else None,
            "scope_config": scope if scope else None,
            "faq_items": faq_items,
            "custom_questions": custom_questions,
            "custom_rules": custom_rules,
            "scope_description": scope_description,
            "custom_prompt": settings.get("custom_prompt"),
            # Contexto para segurança e bloqueio
            "ai_scope_description": scope.get("description") or settings.get("ai_scope_description", ""),
            "ai_out_of_scope_message": out_of_scope_message,
            # Configurações de comportamento
            "handoff": settings.get("handoff", {}),
            "guards": settings.get("guards", {}),
            "limits": settings.get("limits", {}),
        }
    except Exception as e:
        logger.error(f"Erro extraindo contexto IA: {e}")
        # Retorna valores padrão mínimos
        return {
            "company_name": tenant.name,
            "niche_id": "services",
            "tone": "cordial",
            "ai_out_of_scope_message": "Desculpe, não posso ajudá-lo com isso.",
            "scope_description": "",
        }


# =============================================================================
# FUNÇÕES AUXILIARES ROBUSTAS
# =============================================================================

async def get_or_create_lead(
    db: AsyncSession,
    tenant: Tenant,
    channel: Channel,
    external_id: str,
    sender_name: str = None,
    sender_phone: str = None,
    source: str = "organico",
    campaign: str = None,
) -> tuple[Lead, bool]:
    """Busca lead existente ou cria um novo com tratamento de erro."""
    try:
        result = await db.execute(
            select(Lead)
            .where(Lead.tenant_id == tenant.id)
            .where(Lead.external_id == external_id)
        )
        lead = result.scalar_one_or_none()
        
        if lead:
            return lead, False
        
        lead = Lead(
            tenant_id=tenant.id,
            channel_id=channel.id if channel else None,
            external_id=external_id,
            name=sender_name,
            phone=sender_phone,
            source=source,
            campaign=campaign,
            status=LeadStatus.NEW.value,
        )
        db.add(lead)
        await db.flush()
        
        event = LeadEvent(
            lead_id=lead.id,
            event_type=EventType.STATUS_CHANGE.value,
            old_value=None,
            new_value=LeadStatus.NEW.value,
            description="Lead criado automaticamente via atendimento"
        )
        db.add(event)
        
        return lead, True
    except Exception as e:
        logger.error(f"Erro ao buscar/criar lead: {e}")
        raise


async def get_conversation_history(
    db: AsyncSession,
    lead_id: int,
    limit: int = MAX_CONVERSATION_HISTORY,
) -> list[dict]:
    """Busca histórico de mensagens do lead com tratamento de erro."""
    try:
        result = await db.execute(
            select(Message)
            .where(Message.lead_id == lead_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(messages)
        ]
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        return []


async def get_last_message_time(db: AsyncSession, lead_id: int) -> Optional[datetime]:
    """Retorna o timestamp da última mensagem do lead."""
    try:
        result = await db.execute(
            select(Message.created_at)
            .where(Message.lead_id == lead_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Erro ao buscar última mensagem: {e}")
        return None


async def count_lead_messages(db: AsyncSession, lead_id: int) -> int:
    """Conta total de mensagens do lead."""
    try:
        result = await db.execute(
            select(func.count(Message.id))
            .where(Message.lead_id == lead_id)
        )
        return result.scalar() or 0
    except Exception as e:
        logger.error(f"Erro ao contar mensagens: {e}")
        return 0


def sanitize_message_content(content: str) -> str:
    """Remove conteúdo potencialmente perigoso ou muito longo."""
    if not content:
        return ""
    
    # Limita tamanho
    content = content[:MAX_MESSAGE_LENGTH]
    
    # Remove caracteres potencialmente problemáticos (simplificado)
    # Em produção, use uma biblioteca de sanitização
    content = content.replace('\0', '')  # Null bytes
    content = content.replace('\r', '')  # Carriage returns
    
    return content.strip()


# =============================================================================
# FUNÇÃO PRINCIPAL: PROCESSAR MENSAGEM (ROBUSTA)
# =============================================================================

async def process_message(
    db: AsyncSession,
    tenant_slug: str,
    channel_type: str,
    external_id: str,
    content: str,
    sender_name: str = None,
    sender_phone: str = None,
    source: str = "organico",
    campaign: str = None,
) -> dict:
    """
    Processa uma mensagem recebida de um lead.
    
    FLUXO INTELIGENTE ROBUSTO:
    1. Sanitização e validação inicial
    2. Rate Limiting
    3. Security Check
    4. LGPD Check
    5. Busca Tenant e Contexto
    6. AI Guards (escopo, FAQ, limites) - BLOQUEIO CRÍTICO
    7. Verificação de handoff triggers
    8. Detecção de sentimento e contexto
    9. Montagem do prompt com IDENTIDADE EMPRESARIAL
    10. Chamada à IA com anti-alucinação
    11. Processamento e retorno seguro
    """
    
    # ==========================================================================
    # 0. SANITIZAÇÃO INICIAL
    # ==========================================================================
    try:
        content = sanitize_message_content(content)
        if not content or len(content.strip()) < 1:
            return {
                "success": False,
                "error": "Mensagem vazia ou inválida",
                "reply": FALLBACK_RESPONSES["error"]
            }
        
        logger.info(f"📥 Processando mensagem: Tenant={tenant_slug}, Sender={sender_phone or external_id}, Len={len(content)}")
        
    except Exception as e:
        logger.error(f"Erro na sanitização: {e}")
        return {
            "success": False,
            "error": "Erro ao processar mensagem",
            "reply": FALLBACK_RESPONSES["error"]
        }
    
    # ==========================================================================
    # 1. RATE LIMITING
    # ==========================================================================
    try:
        rate_limit_result = await check_message_rate_limit(
            phone=sender_phone or external_id,
            tenant_id=None,  # Será preenchido após buscar tenant
        )
        
        if not rate_limit_result.allowed:
            logger.warning(f"Rate limit excedido: {sender_phone or external_id}")
            return {
                "success": True,
                "reply": get_rate_limit_response(),
                "lead_id": None,
                "is_new_lead": False,
                "blocked_reason": "rate_limit",
                "retry_after": rate_limit_result.retry_after_seconds,
            }
    except Exception as e:
        logger.error(f"Erro no rate limiting: {e}")
        # Continua mesmo com erro no rate limit
    
    # ==========================================================================
    # 2. SECURITY CHECK
    # ==========================================================================
    try:
        security_result = run_security_check(
            content=content,
            sender_id=sender_phone or external_id,
            tenant_id=None,  # Será atualizado
        )
        
        if not security_result.is_safe and security_result.should_block:
            logger.warning(f"Mensagem bloqueada por segurança: {security_result.threat_type}")
            
            # Ainda não temos tenant, então retorna resposta genérica
            safe_response = get_safe_response_for_threat(security_result.threat_type)
            
            return {
                "success": True,
                "reply": safe_response,
                "lead_id": None,
                "is_new_lead": False,
                "security_blocked": True,
                "threat_level": security_result.threat_level,
            }
        
        content = security_result.sanitized_content
        
    except Exception as e:
        logger.error(f"Erro no security check: {e}")
        # Continua, mas mantém o conteúdo original
    
    # ==========================================================================
    # 3. BUSCA TENANT E CANAL
    # ==========================================================================
    try:
        result = await db.execute(
            select(Tenant)
            .where(Tenant.slug == tenant_slug)
            .where(Tenant.active == True)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.error(f"Tenant não encontrado: {tenant_slug}")
            return {
                "success": False,
                "error": "Tenant não encontrado ou inativo",
                "reply": FALLBACK_RESPONSES["error"]
            }
        
        # Atualiza tenant_id nos serviços que precisam
        if hasattr(security_result, 'tenant_id'):
            security_result.tenant_id = tenant.id
        
        result = await db.execute(
            select(Channel)
            .where(Channel.tenant_id == tenant.id)
            .where(Channel.type == channel_type)
            .where(Channel.active == True)
        )
        channel = result.scalar_one_or_none()
        
        # Cria canal se não existir (para compatibilidade)
        if not channel:
            channel = Channel(
                tenant_id=tenant.id,
                type=channel_type,
                active=True,
                config={}
            )
            db.add(channel)
            await db.flush()
        
    except Exception as e:
        logger.error(f"Erro ao buscar tenant/canal: {e}")
        await log_system_error(
            db=db,
            error_type="tenant_lookup",
            details={"tenant_slug": tenant_slug, "error": str(e)},
            tenant_id=tenant.id if 'tenant' in locals() else None,
            lead_id=lead.id if 'lead' in locals() else None,
        )
        return {
            "success": False,
            "error": "Erro interno ao buscar empresa",
            "reply": FALLBACK_RESPONSES["error"]
        }
    
    # ==========================================================================
    # 4. 🏢 EXTRAI CONTEXTO COMPLETO DA IA
    # ==========================================================================
    try:
        ai_context = extract_ai_context(tenant)
        settings = migrate_settings_if_needed(tenant.settings or {})
        
        logger.info(f"Contexto IA extraído: {ai_context['company_name']} - Nicho: {ai_context['niche_id']}")
        
    except Exception as e:
        logger.error(f"Erro ao extrair contexto IA: {e}")
        # Usa contexto mínimo
        ai_context = {
            "company_name": tenant.name,
            "niche_id": "services",
            "tone": "cordial",
            "ai_out_of_scope_message": "Desculpe, não posso ajudá-lo com isso.",
            "scope_description": "",
        }
        settings = {}
    
    # ==========================================================================
    # 5. BUSCA/CRIA LEAD
    # ==========================================================================
    try:
        lead, is_new = await get_or_create_lead(
            db=db, tenant=tenant, channel=channel, external_id=external_id,
            sender_name=sender_name, sender_phone=sender_phone,
            source=source, campaign=campaign,
        )
        
        await log_message_received(
            db=db, tenant_id=tenant.id, lead_id=lead.id,
            content_preview=content[:100], channel=channel_type,
        )
        
        logger.info(f"Lead {'criado' if is_new else 'encontrado'}: {lead.id} - Qualificação: {lead.qualification}")
        
    except Exception as e:
        logger.error(f"Erro ao buscar/criar lead: {e}")
        await log_system_error(
            db=db,
            error_type="lead_creation",
            details={"tenant_id": tenant.id, "error": str(e)}
        )
        return {
            "success": False,
            "error": "Erro ao processar seu cadastro",
            "reply": FALLBACK_RESPONSES["error"]
        }
    
    # ==========================================================================
    # 6. LGPD CHECK (após ter o lead)
    # ==========================================================================
    try:
        lgpd_request = detect_lgpd_request(content)
        
        if lgpd_request:
            logger.info(f"Solicitação LGPD detectada: {lgpd_request}")
            
            user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
            db.add(user_message)
            
            content_lower = content.lower().strip()
            
            if "confirmar exclusão" in content_lower or "confirmar exclusao" in content_lower:
                delete_result = await delete_lead_data(db, lead, hard_delete=False)
                lgpd_reply = (
                    "✅ Seus dados foram anonimizados com sucesso.\n\n"
                    "Seu histórico de conversas foi removido e seus dados pessoais foram excluídos.\n\n"
                    "Obrigado por utilizar nossos serviços."
                )
            elif "confirmar acesso" in content_lower:
                export = await export_lead_data(db, lead)
                lgpd_reply = (
                    f"📋 Seus dados foram exportados!\n\n"
                    f"*Dados Pessoais:*\n"
                    f"Nome: {export.personal_data.get('nome', 'N/A')}\n"
                    f"Telefone: {export.personal_data.get('telefone', 'N/A')}\n"
                    f"Email: {export.personal_data.get('email', 'N/A')}\n"
                    f"Cidade: {export.personal_data.get('cidade', 'N/A')}\n\n"
                    f"Total de mensagens: {len(export.messages)}\n\n"
                    f"Se precisar de mais detalhes, entre em contato conosco."
                )
            elif "confirmar exportação" in content_lower or "confirmar exportacao" in content_lower:
                export = await export_lead_data(db, lead)
                lgpd_reply = (
                    "📤 Exportação concluída!\n\n"
                    "Seus dados foram preparados. Em um sistema completo, "
                    "enviaríamos um arquivo JSON por email.\n\n"
                    f"Total de registros: {len(export.messages)} mensagens"
                )
            else:
                lgpd_reply = get_lgpd_response(
                    lgpd_request, 
                    tenant_name=ai_context["company_name"]
                )
            
            assistant_message = Message(
                lead_id=lead.id, role="assistant", content=lgpd_reply, tokens_used=0,
            )
            db.add(assistant_message)
            await db.commit()
            
            return {
                "success": True,
                "reply": lgpd_reply,
                "lead_id": lead.id,
                "is_new_lead": is_new,
                "lgpd_request": lgpd_request,
            }
    except Exception as e:
        logger.error(f"Erro no processamento LGPD: {e}")
        # Continua, não interrompe por erro LGPD
    
    # ==========================================================================
    # 7. VERIFICAÇÃO DE STATUS (lead já transferido)
    # ==========================================================================
    try:
        if lead.status == LeadStatus.HANDED_OFF.value:
            user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
            db.add(user_message)
            
            logger.info(f"Lead {lead.id} já foi transferido, apenas registrando mensagem")
            
            await db.commit()
            
            return {
                "success": True,
                "reply": None,
                "lead_id": lead.id,
                "is_new_lead": False,
                "qualification": lead.qualification,
                "status": "transferido",
                "message": "Lead já transferido para atendimento humano"
            }
    except Exception as e:
        logger.error(f"Erro verificando status do lead: {e}")
    
    # ==========================================================================
    # 8. AI GUARDS - BLOQUEIO CRÍTICO DE ESCOPO E LIMITES
    # ==========================================================================
    try:
        message_count = await count_lead_messages(db, lead.id)
        history = await get_conversation_history(db, lead.id)
        
        guards_result = await run_ai_guards_async(
            message=content,
            message_count=message_count,
            settings=settings,
            lead_qualification=lead.qualification or "frio",
            previous_messages=history[-10:] if history else [],  # Últimas 10 mensagens para contexto
        )
        
        logger.info(f"Resultado dos guards: {guards_result.get('reason', 'nenhum')}")
        
        # ======================================================================
        # 🚨 TRATAMENTO ROBUSTO DOS GUARDS - BLOQUEIO GARANTIDO
        # ======================================================================
        
        # Se os guards disserem que não pode responder, BLOQUEIA IMEDIATAMENTE
        if not guards_result.get("can_respond", True):
            guard_reason = guards_result.get("reason", "unknown")
            guard_response = guards_result.get("response")
            
            # Mensagem padrão baseada no motivo
            default_responses = {
                "out_of_scope": ai_context.get("ai_out_of_scope_message", FALLBACK_RESPONSES["out_of_scope"]),
                "price_block": (
                    "Para garantir informações corretas e atualizadas, quem confirma valores é sempre o especialista. "
                    "Me conta qual peça você está buscando e para qual data que eu já direciono certinho! 😊"
                ),
                "insistence_block": (
                    "Eu entendo sua dúvida! Só quem confirma valores é o especialista, "
                    "para evitar qualquer informação incorreta. "
                    "Me diga qual peça você quer e a data do evento que eu acelero para você 😉"
                ),
                "faq": guard_response or "Aqui está a informação que você precisa:",
                "out_of_hours": (
                    f"No momento estamos fora do horário de atendimento da {ai_context['company_name']}. "
                    "Nossa equipe retornará em breve. Deixe sua mensagem que responderemos assim que possível!"
                ),
                "message_limit": (
                    "Para garantir a melhor qualidade no atendimento, "
                    "vou conectar você diretamente com nosso especialista. "
                    "Em instantes ele entrará em contato!"
                ),
                "unknown": FALLBACK_RESPONSES["out_of_scope"],
            }
            
            final_response = guard_response or default_responses.get(guard_reason, default_responses["unknown"])
            
            # Se for fora do escopo, personaliza com o nome da empresa
            if guard_reason == "out_of_scope" and not guard_response:
                final_response = final_response.replace(
                    "[NEGÓCIO DO CLIENTE]", 
                    ai_context.get("scope_description", "nossos produtos e serviços")
                )
            
            # Registra a mensagem do usuário
            user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
            db.add(user_message)
            
            # Registra a resposta do guard
            assistant_message = Message(
                lead_id=lead.id, role="assistant", content=final_response, tokens_used=0
            )
            db.add(assistant_message)
            
            # Se for force_handoff, faz a transferência
            if guards_result.get("force_handoff"):
                logger.info(f"Forçando handoff para lead {lead.id} - Motivo: {guard_reason}")
                
                if not lead.summary:
                    lead.summary = await generate_lead_summary(
                        conversation=history,
                        extracted_data=lead.custom_data or {},
                        qualification={"qualification": lead.qualification},
                    )
                
                handoff_result = await execute_handoff(lead, tenant, guard_reason, db)
                
                # Adiciona mensagem de handoff
                handoff_message = Message(
                    lead_id=lead.id, role="assistant",
                    content=handoff_result["message_for_lead"], tokens_used=0,
                )
                db.add(handoff_message)
                
                await log_ai_action(
                    db=db, tenant_id=tenant.id, lead_id=lead.id,
                    action_type="handoff", details={"reason": guard_reason},
                )
                
                await db.commit()
                
                return {
                    "success": True,
                    "reply": final_response + "\n\n" + handoff_result["message_for_lead"],
                    "lead_id": lead.id,
                    "is_new_lead": is_new,
                    "qualification": lead.qualification,
                    "status": "transferido",
                    "handoff": {
                        "reason": guard_reason,
                        "manager_whatsapp": handoff_result["manager_whatsapp"],
                    },
                    "guard": guard_reason,
                }
            
            await db.commit()
            
            return {
                "success": True,
                "reply": final_response,
                "lead_id": lead.id,
                "is_new_lead": is_new,
                "qualification": lead.qualification,
                "guard": guard_reason,
            }
        
    except Exception as e:
        logger.error(f"Erro crítico nos AI Guards: {e}")
        await log_system_error(
            db=db,
            error_type="ai_guards",
            details={"lead_id": lead.id, "error": str(e)}
        )
        # Em caso de erro nos guards, bloqueia por segurança
        user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
        db.add(user_message)
        
        blocked_message = Message(
            lead_id=lead.id, role="assistant",
            content=FALLBACK_RESPONSES["security"], tokens_used=0,
        )
        db.add(blocked_message)
        await db.commit()
        
        return {
            "success": True,
            "reply": FALLBACK_RESPONSES["security"],
            "lead_id": lead.id,
            "is_new_lead": is_new,
            "security_blocked": True,
        }
    
    # ==========================================================================
    # 9. VERIFICA HANDOFF POR TRIGGERS CUSTOMIZADOS
    # ==========================================================================
    try:
        from src.infrastructure.services import check_handoff_triggers
        
        handoff_triggers = settings.get("handoff", {}).get("triggers", []) or settings.get("handoff_triggers", [])
        trigger_found, trigger_matched = check_handoff_triggers(
            message=content,
            custom_triggers=handoff_triggers,
        )
        
        if trigger_found:
            logger.info(f"Trigger de handoff detectado: {trigger_matched}")
            
            user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
            db.add(user_message)
            await db.flush()
            
            if not lead.summary:
                lead.summary = await generate_lead_summary(
                    conversation=history,
                    extracted_data=lead.custom_data or {},
                    qualification={"qualification": lead.qualification},
                )
            
            handoff_result = await execute_handoff(lead, tenant, "user_requested", db)
            
            assistant_message = Message(
                lead_id=lead.id, role="assistant",
                content=handoff_result["message_for_lead"], tokens_used=0,
            )
            db.add(assistant_message)
            
            await log_ai_action(
                db=db, tenant_id=tenant.id, lead_id=lead.id,
                action_type="handoff",
                details={"reason": "user_requested", "trigger": trigger_matched},
            )
            
            await db.commit()
            
            return {
                "success": True,
                "reply": handoff_result["message_for_lead"],
                "lead_id": lead.id,
                "is_new_lead": is_new,
                "qualification": lead.qualification,
                "status": "transferido",
                "handoff": {
                    "reason": "user_requested",
                    "manager_whatsapp": handoff_result["manager_whatsapp"],
                }
            }
    except Exception as e:
        logger.error(f"Erro verificando triggers de handoff: {e}")
        # Continua, não interrompe
    
    # ==========================================================================
    # 10. ATUALIZA STATUS PARA EM_ATENDIMENTO
    # ==========================================================================
    try:
        if lead.status == LeadStatus.NEW.value:
            old_status = lead.status
            lead.status = LeadStatus.IN_PROGRESS.value
            
            event = LeadEvent(
                lead_id=lead.id,
                event_type=EventType.STATUS_CHANGE.value,
                old_value=old_status,
                new_value=lead.status,
                description="Lead iniciou conversa"
            )
            db.add(event)
    except Exception as e:
        logger.error(f"Erro atualizando status do lead: {e}")
    
    # ==========================================================================
    # 11. SALVA MENSAGEM DO USUÁRIO
    # ==========================================================================
    try:
        user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
        db.add(user_message)
        await db.flush()
        
        await mark_lead_activity(db, lead)
        
    except Exception as e:
        logger.error(f"Erro salvando mensagem do usuário: {e}")
        return {
            "success": False,
            "error": "Erro ao processar sua mensagem",
            "reply": FALLBACK_RESPONSES["error"],
            "lead_id": lead.id,
        }
    
    # ==========================================================================
    # 12. DETECÇÃO DE SENTIMENTO E CONTEXTO
    # ==========================================================================
    sentiment = {"sentiment": "neutral", "confidence": 0.5}
    is_returning_lead = False
    hours_since_last = 0
    previous_summary = None
    
    try:
        sentiment = await detect_sentiment(content)
        logger.info(f"Sentimento detectado: {sentiment.get('sentiment')}")
        
        # Verifica se é lead retornando
        if not is_new:
            last_message_time = await get_last_message_time(db, lead.id)
            if last_message_time:
                from datetime import timezone
                now = datetime.now(timezone.utc)
                
                if last_message_time.tzinfo is None:
                    last_message_time = last_message_time.replace(tzinfo=timezone.utc)
                
                time_diff = now - last_message_time
                hours_since_last = time_diff.total_seconds() / 3600
                
                if hours_since_last > 6:
                    is_returning_lead = True
                    
                    if hours_since_last > 24 and len(history) >= 4:
                        previous_summary = await generate_conversation_summary(history)
                        if not lead.summary and previous_summary:
                            lead.summary = previous_summary
                            
    except Exception as e:
        logger.error(f"Erro na detecção de sentimento/contexto: {e}")
        # Continua com valores padrão
    
    # ==========================================================================
    # 13. MONTA CONTEXTO DO LEAD PARA PERSONALIZAÇÃO
    # ==========================================================================
    lead_context = None
    try:
        if lead.custom_data:
            lead_context = {
                "name": lead.name,
                "family_situation": lead.custom_data.get("family_situation"),
                "work_info": lead.custom_data.get("work_info"),
                "budget_range": lead.custom_data.get("budget_range"),
                "urgency_level": lead.custom_data.get("urgency_level"),
                "preferences": lead.custom_data.get("preferences"),
                "pain_points": lead.custom_data.get("pain_points"),
                "objections": lead.custom_data.get("objections"),
                "buying_signals": lead.custom_data.get("buying_signals"),
                "previous_experience": lead.custom_data.get("previous_experience"),
                "communication_style": lead.custom_data.get("communication_style"),
            }
            lead_context = {k: v for k, v in lead_context.items() if v is not None}
            if not lead_context:
                lead_context = None
                
    except Exception as e:
        logger.error(f"Erro montando contexto do lead: {e}")
        lead_context = None
    
    # ==========================================================================
    # 14. MONTA PROMPT DO SISTEMA COM IDENTIDADE EMPRESARIAL
    # ==========================================================================
    system_prompt = ""
    try:
        system_prompt = build_system_prompt(
            niche_id=ai_context["niche_id"],
            company_name=ai_context["company_name"],
            tone=ai_context["tone"],
            custom_questions=ai_context["custom_questions"],
            custom_rules=ai_context["custom_rules"],
            custom_prompt=ai_context["custom_prompt"],
            faq_items=ai_context["faq_items"],
            scope_description=ai_context["scope_description"],
            lead_context=lead_context,
            # 🏢 NOVOS PARÂMETROS - IDENTIDADE EMPRESARIAL!
            identity=ai_context["identity"],
            scope_config=ai_context["scope_config"],
        )
        
        logger.debug(f"Prompt do sistema montado ({len(system_prompt)} caracteres)")
        
    except Exception as e:
        logger.error(f"Erro crítico montando prompt: {e}")
        await log_system_error(
            db=db,
            error_type="prompt_build",
            details={"lead_id": lead.id, "error": str(e)}
        )
        # Cria prompt mínimo de emergência
        system_prompt = f"""
        Você é assistente da {ai_context['company_name']}.
        Responda apenas sobre {ai_context['scope_description'] or 'produtos e serviços da empresa'}.
        Se perguntarem sobre outros assuntos, diga: "{ai_context.get('ai_out_of_scope_message', 'Não posso ajudar com isso')}".
        Seja educado e profissional.
        """
    
    # ==========================================================================
    # 15. PREPARA MENSAGENS PARA A IA
    # ==========================================================================
    messages = []
    try:
        # Atualiza histórico (incluindo a mensagem atual)
        history = await get_conversation_history(db, lead.id)
        
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
        ]
        
        # Adiciona instruções de segurança reforçadas
        ai_scope = ai_context["ai_scope_description"]
        ai_fallback = ai_context["ai_out_of_scope_message"]
        
        if ai_scope:
            security_instructions = build_security_instructions(
                company_name=ai_context["company_name"],
                scope_description=ai_scope,
                out_of_scope_message=ai_fallback
            )
            messages[0]["content"] += f"\n\n{security_instructions}"
            
        # Adiciona contexto de FAQ se houver
        if guards_result.get("reason") == "faq" and guards_result.get("response"):
            messages.append({
                "role": "system",
                "content": f"INFORMAÇÃO DO FAQ (USE ESTA RESPOSTA): {guards_result['response']}"
            })
            
    except Exception as e:
        logger.error(f"Erro preparando mensagens para IA: {e}")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
    
    # ==========================================================================
    # 16. CHAMA IA COM CONTEXTO INTELIGENTE + ANTI-ALUCINAÇÃO
    # ==========================================================================
    ai_response = None
    final_response = ""
    was_blocked = False
    tokens_used = 0
    
    try:
        ai_response = await generate_context_aware_response(
            messages=messages,
            lead_data=lead_context or {},
            sentiment=sentiment,
            tone=ai_context["tone"],
            is_returning_lead=is_returning_lead,
            hours_since_last_message=hours_since_last,
            previous_summary=previous_summary or lead.summary,
        )
        
        # Valida resposta da IA (Anti-Alucinação FORTIFICADO)
        final_response, was_blocked = sanitize_response(
            ai_response["content"],
            ai_fallback,
            company_name=ai_context["company_name"],
            scope_description=ai_context["scope_description"]
        )
        
        tokens_used = ai_response.get("tokens_used", 0)
        
        # Log se bloqueou
        if was_blocked:
            logger.warning(f"⚠️ Resposta bloqueada por alucinação - Tenant: {tenant.slug}, Lead: {lead.id}")
            await log_ai_action(
                db=db,
                tenant_id=tenant.id,
                lead_id=lead.id,
                action_type="blocked_response",
                details={
                    "original_response": ai_response["content"][:200],
                    "reason": "hallucination_detected"
                },
            )
        
        logger.info(f"Resposta IA gerada ({len(final_response)} chars, {tokens_used} tokens)")
        
    except Exception as e:
        logger.error(f"Erro crítico chamando IA: {e}")
        await log_system_error(
            db=db,
            error_type="ai_call",
            details={"lead_id": lead.id, "error": str(e), "traceback": traceback.format_exc()}
        )
        
        # Resposta de fallback
        final_response = (
            f"Olá! Sou a assistente da {ai_context['company_name']} e posso te ajudar com {ai_context.get('scope_description', 'nossos produtos')}. "
            f"O que você gostaria de saber?"
        )
        was_blocked = False
        tokens_used = 0
    
    # ==========================================================================
    # 17. VERIFICA HANDOFF SUGERIDO PELA IA
    # ==========================================================================
    should_transfer_by_ai = False
    ai_handoff_reason = ""
    
    try:
        handoff_check = check_ai_handoff(content, final_response)
        should_transfer_by_ai = handoff_check["should_handoff"]
        ai_handoff_reason = handoff_check.get("reason", "")
        
        if should_transfer_by_ai:
            logger.info(f"IA sugeriu handoff: {ai_handoff_reason}")
    except Exception as e:
        logger.error(f"Erro verificando handoff da IA: {e}")
    
    # ==========================================================================
    # 18. SALVA RESPOSTA DA IA
    # ==========================================================================
    try:
        assistant_message = Message(
            lead_id=lead.id,
            role="assistant",
            content=final_response,
            tokens_used=tokens_used,
        )
        db.add(assistant_message)
        
        # Loga resposta da IA
        await log_ai_action(
            db=db,
            tenant_id=tenant.id,
            lead_id=lead.id,
            action_type="response",
            details={
                "tokens_used": tokens_used,
                "sentiment": sentiment.get("sentiment"),
                "is_returning": is_returning_lead,
                "was_blocked": was_blocked,
                "identity_loaded": bool(ai_context.get("identity")),
                "ai_suggested_handoff": should_transfer_by_ai,
            },
        )
        
    except Exception as e:
        logger.error(f"Erro salvando resposta da IA: {e}")
        # Continua mesmo com erro
    
    # ==========================================================================
    # 19. EXTRAI DADOS E QUALIFICA LEAD
    # ==========================================================================
    try:
        total_messages = await count_lead_messages(db, lead.id)
        
        if total_messages % 3 == 0 or total_messages >= 4:  # A cada 3 mensagens ou depois de 4
            await update_lead_data(db, lead, tenant, history + [
                {"role": "user", "content": content},
                {"role": "assistant", "content": final_response},
            ])
    except Exception as e:
        logger.error(f"Erro extraindo dados do lead: {e}")
        # Não interrompe o fluxo principal
    
    # ==========================================================================
    # 20. VERIFICA HANDOFF FINAL (LEAD QUENTE OU IA SUGERIU)
    # ==========================================================================
    try:
        should_transfer_final = (
            lead.qualification in ["quente", "hot"] or 
            should_transfer_by_ai
        )
        
        handoff_reason = "lead_hot" if lead.qualification in ["quente", "hot"] else "ai_suggested"
        
        if should_transfer_final:
            logger.info(f"Realizando handoff final - Razão: {handoff_reason}")
            
            if not lead.summary:
                lead.summary = await generate_lead_summary(
                    conversation=history + [
                        {"role": "user", "content": content},
                        {"role": "assistant", "content": final_response},
                    ],
                    extracted_data=lead.custom_data or {},
                    qualification={"qualification": lead.qualification},
                )
            
            handoff_result = await execute_handoff(lead, tenant, handoff_reason, db)
            
            transfer_message = Message(
                lead_id=lead.id,
                role="assistant",
                content=handoff_result["message_for_lead"],
                tokens_used=0,
            )
            db.add(transfer_message)
            
            await log_ai_action(
                db=db,
                tenant_id=tenant.id,
                lead_id=lead.id,
                action_type="handoff",
                details={
                    "reason": handoff_reason,
                    "qualification": lead.qualification,
                    "ai_suggestion": ai_handoff_reason if should_transfer_by_ai else None
                },
            )
            
            final_response_with_handoff = final_response + "\n\n" + handoff_result["message_for_lead"]
            
            await db.commit()
            
            # Calcula delay humanizado
            typing_delay = calculate_typing_delay(len(final_response_with_handoff))
            
            return {
                "success": True,
                "reply": final_response_with_handoff,
                "lead_id": lead.id,
                "is_new_lead": is_new,
                "qualification": lead.qualification,
                "status": "transferido",
                "handoff": {
                    "reason": handoff_reason,
                    "manager_whatsapp": handoff_result["manager_whatsapp"],
                },
                "typing_delay": typing_delay,
                "sentiment": sentiment.get("sentiment"),
                "was_blocked": was_blocked,
                "identity_loaded": bool(ai_context.get("identity")),
            }
    except Exception as e:
        logger.error(f"Erro no handoff final: {e}")
        # Continua sem handoff
    
    # ==========================================================================
    # 21. COMMIT FINAL E RETORNO
    # ==========================================================================
    try:
        await db.commit()
        
        # Calcula delay humanizado
        typing_delay = calculate_typing_delay(len(final_response))
        
        logger.info(f"✅ Mensagem processada com sucesso - Lead: {lead.id}, Qualificação: {lead.qualification}")
        
        return {
            "success": True,
            "reply": final_response,
            "lead_id": lead.id,
            "is_new_lead": is_new,
            "qualification": lead.qualification,
            "typing_delay": typing_delay,
            "sentiment": sentiment.get("sentiment"),
            "is_returning_lead": is_returning_lead,
            "was_blocked": was_blocked,
            "identity_loaded": bool(ai_context.get("identity")),
        }
        
    except Exception as e:
        logger.error(f"Erro no commit final: {e}")
        
        # Tenta rollback
        try:
            await db.rollback()
        except:
            pass
        
        return {
            "success": False,
            "error": "Erro interno ao processar sua mensagem",
            "reply": FALLBACK_RESPONSES["error"],
            "lead_id": lead.id,
        }


async def update_lead_data(
    db: AsyncSession,
    lead: Lead,
    tenant: Tenant,
    conversation: list[dict],
) -> None:
    """Extrai dados da conversa e atualiza o lead com tratamento de erro."""
    try:
        ai_context = extract_ai_context(tenant)
        niche_id = ai_context["niche_id"]
        niche_config = get_niche_config(niche_id)
        
        if not niche_config:
            logger.warning(f"Nicho não encontrado: {niche_id}")
            return
        
        extracted = await extract_lead_data(
            conversation=conversation,
            required_fields=niche_config.required_fields,
            optional_fields=niche_config.optional_fields,
        )
        
        # Atualiza dados básicos
        if extracted.get("name") and not lead.name:
            lead.name = extracted["name"]
        if extracted.get("phone") and not lead.phone:
            lead.phone = extracted["phone"]
        if extracted.get("email") and not lead.email:
            lead.email = extracted["email"]
        if extracted.get("city") and not lead.city:
            lead.city = extracted["city"]
        
        # Atualiza campos customizados
        custom_fields = {k: v for k, v in extracted.items() 
                         if k not in ["name", "phone", "email", "city"] and v is not None}
        if custom_fields:
            lead.custom_data = {**(lead.custom_data or {}), **custom_fields}
        
        # Qualificação
        qualification_result = await qualify_lead(
            conversation=conversation,
            extracted_data=extracted,
            qualification_rules=niche_config.qualification_rules,
        )
        
        new_qualification = qualification_result.get("qualification", "frio")
        old_qualification = lead.qualification
        
        if new_qualification != old_qualification:
            event = LeadEvent(
                lead_id=lead.id,
                event_type=EventType.QUALIFICATION_CHANGE.value,
                old_value=old_qualification,
                new_value=new_qualification,
                description=qualification_result.get("reason", ""),
            )
            db.add(event)
            lead.qualification = new_qualification
            
            # Notificação para lead quente
            if new_qualification in ["quente", "hot"] and old_qualification not in ["quente", "hot"]:
                notification = Notification(
                    tenant_id=tenant.id,
                    type="lead_quente",
                    title="🔥 Novo Lead Quente!",
                    message=f"{lead.name or 'Lead'} está muito interessado e pronto para comprar!",
                    reference_type="lead",
                    reference_id=lead.id,
                    read=False,
                )
                db.add(notification)
                logger.info(f"Lead {lead.id} atualizado para QUENTE")
        
        # Verifica se pode atualizar status
        required_collected = sum(1 for f in niche_config.required_fields 
                                if extracted.get(f) is not None)
        
        if new_qualification in ["quente", "hot"] or required_collected >= len(niche_config.required_fields) - 1:
            if lead.status == LeadStatus.IN_PROGRESS.value:
                lead.status = LeadStatus.QUALIFIED.value
                
                event = LeadEvent(
                    lead_id=lead.id,
                    event_type=EventType.STATUS_CHANGE.value,
                    old_value=LeadStatus.IN_PROGRESS.value,
                    new_value=LeadStatus.QUALIFIED.value,
                    description="Lead qualificado automaticamente",
                )
                db.add(event)
            
            # Gera summary se necessário
            if not lead.summary:
                summary = await generate_lead_summary(
                    conversation=conversation,
                    extracted_data=extracted,
                    qualification=qualification_result,
                )
                lead.summary = summary
                
    except Exception as e:
        logger.error(f"Erro atualizando dados do lead {lead.id}: {e}")
        # Não propaga o erro, apenas loga