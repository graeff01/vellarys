"""
CASO DE USO: PROCESSAR MENSAGEM (VERSÃO INTELIGENTE COM ANTI-ALUCINAÇÃO)
==========================================================================

Fluxo principal quando um lead envia uma mensagem.
Inclui:
- Memória de contexto (retomar conversa)
- Detecção de sentimento
- Respostas personalizadas
- Segurança completa
- 🔒 PROTEÇÃO ANTI-ALUCINAÇÃO (NOVO!)
"""

import logging  # ⭐ ADICIONE ESTA LINHA
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

# Novas funções inteligentes
from src.infrastructure.services.openai_service import (
    detect_sentiment,
    generate_context_aware_response,
    generate_conversation_summary,
    calculate_typing_delay,
)

# ⭐ ADICIONE ESTE IMPORT (ANTI-ALUCINAÇÃO)
from src.infrastructure.services.ai_security import (
    build_security_instructions,
    sanitize_response,
    should_handoff as check_ai_handoff,
)

# Serviços de segurança
from src.infrastructure.services.security_service import (
    run_security_check,
    get_safe_response_for_threat,
    ThreatLevel,
)
from src.infrastructure.services.message_rate_limiter import (
    check_message_rate_limit,
    get_rate_limit_response,
)
from src.infrastructure.services.audit_service import (
    log_message_received,
    log_security_threat,
    log_ai_action,
    AuditAction,
    AuditSeverity,
)
from src.infrastructure.services.lgpd_service import (
    detect_lgpd_request,
    get_lgpd_response,
    export_lead_data,
    delete_lead_data,
)

logger = logging.getLogger(__name__)  # ⭐ ADICIONE ESTA LINHA


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
    """Busca lead existente ou cria um novo."""
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


async def get_conversation_history(
    db: AsyncSession,
    lead_id: int,
    limit: int = 20,
) -> list[dict]:
    """Busca histórico de mensagens do lead."""
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


async def get_last_message_time(db: AsyncSession, lead_id: int) -> Optional[datetime]:
    """Retorna o timestamp da última mensagem do lead."""
    result = await db.execute(
        select(Message.created_at)
        .where(Message.lead_id == lead_id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    last_time = result.scalar_one_or_none()
    return last_time


async def count_lead_messages(db: AsyncSession, lead_id: int) -> int:
    """Conta total de mensagens do lead."""
    result = await db.execute(
        select(func.count(Message.id))
        .where(Message.lead_id == lead_id)
    )
    return result.scalar() or 0


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
    
    FLUXO INTELIGENTE:
    1. Rate Limiting - Proteção contra flooding
    2. Security Check - Detecta ameaças
    3. LGPD Check - Detecta solicitações de dados
    4. Detecção de Sentimento - Ajusta tom
    5. Memória de Contexto - Verifica se lead está retornando
    6. AI Guards - Horário, escopo, FAQ, limite
    7. 🔒 Processamento com IA + Anti-Alucinação
    8. Audit Log - Registra tudo
    """
    
    # ==========================================================================
    # 0. BUSCA TENANT
    # ==========================================================================
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug).where(Tenant.active == True)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        return {"success": False, "error": "Tenant não encontrado ou inativo"}
    
    settings = tenant.settings or {}
    
    # ==========================================================================
    # 1. RATE LIMITING
    # ==========================================================================
    rate_limit_result = await check_message_rate_limit(
        phone=sender_phone or external_id,
        tenant_id=tenant.id,
    )
    
    if not rate_limit_result.allowed:
        return {
            "success": True,
            "reply": get_rate_limit_response(),
            "lead_id": None,
            "is_new_lead": False,
            "blocked_reason": "rate_limit",
            "retry_after": rate_limit_result.retry_after_seconds,
        }
    
    # ==========================================================================
    # 2. SECURITY CHECK
    # ==========================================================================
    security_result = run_security_check(
        content=content,
        sender_id=sender_phone or external_id,
        tenant_id=tenant.id,
    )
    
    if not security_result.is_safe and security_result.should_block:
        result_channel = await db.execute(
            select(Channel)
            .where(Channel.tenant_id == tenant.id)
            .where(Channel.type == channel_type)
            .where(Channel.active == True)
        )
        channel = result_channel.scalar_one_or_none()
        
        lead, is_new = await get_or_create_lead(
            db=db, tenant=tenant, channel=channel, external_id=external_id,
            sender_name=sender_name, sender_phone=sender_phone,
            source=source, campaign=campaign,
        )
        
        await log_security_threat(
            db=db, tenant_id=tenant.id, lead_id=lead.id,
            threat_type=security_result.threat_type,
            threat_level=security_result.threat_level,
            content_preview=content[:200],
            matched_pattern=security_result.matched_pattern,
            blocked=True,
        )
        
        user_message = Message(
            lead_id=lead.id, role="user",
            content=security_result.sanitized_content, tokens_used=0,
        )
        db.add(user_message)
        
        safe_response = get_safe_response_for_threat(security_result.threat_type)
        
        assistant_message = Message(
            lead_id=lead.id, role="assistant",
            content=safe_response, tokens_used=0,
        )
        db.add(assistant_message)
        
        await db.commit()
        
        return {
            "success": True,
            "reply": safe_response,
            "lead_id": lead.id,
            "is_new_lead": is_new,
            "security_blocked": True,
            "threat_level": security_result.threat_level,
        }
    
    content = security_result.sanitized_content
    
    # ==========================================================================
    # 3. BUSCA/CRIA LEAD E CANAL
    # ==========================================================================
    result = await db.execute(
        select(Channel)
        .where(Channel.tenant_id == tenant.id)
        .where(Channel.type == channel_type)
        .where(Channel.active == True)
    )
    channel = result.scalar_one_or_none()
    
    lead, is_new = await get_or_create_lead(
        db=db, tenant=tenant, channel=channel, external_id=external_id,
        sender_name=sender_name, sender_phone=sender_phone,
        source=source, campaign=campaign,
    )
    
    await log_message_received(
        db=db, tenant_id=tenant.id, lead_id=lead.id,
        content_preview=content, channel=channel_type,
    )
    
    # ==========================================================================
    # 4. LGPD CHECK
    # ==========================================================================
    lgpd_request = detect_lgpd_request(content)
    
    if lgpd_request:
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
                tenant_name=settings.get("company_name", tenant.name)
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
    
    # ==========================================================================
    # 5. VERIFICAÇÃO DE STATUS (lead já transferido)
    # ==========================================================================
    if lead.status == LeadStatus.HANDED_OFF.value:
        user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
        db.add(user_message)
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
    
    # ==========================================================================
    # 6. DETECÇÃO DE SENTIMENTO (NOVO!)
    # ==========================================================================
    sentiment = await detect_sentiment(content)
    
    # ==========================================================================
    # 7. VERIFICA SE LEAD ESTÁ RETORNANDO (MEMÓRIA!)
    # ==========================================================================
    is_returning_lead = False
    hours_since_last = 0
    previous_summary = None
    
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
                
                if hours_since_last > 24:
                    history = await get_conversation_history(db, lead.id)
                    if len(history) >= 4:
                        previous_summary = await generate_conversation_summary(history)
                        if not lead.summary and previous_summary:
                            lead.summary = previous_summary
    
    # ==========================================================================
    # 8. AI GUARDS (horário, escopo, FAQ, limite)
    # ==========================================================================
    message_count = await count_lead_messages(db, lead.id)
    
    guards_result = await run_ai_guards_async(
        message=content,
        message_count=message_count,
        settings=settings,
        lead_qualification=lead.qualification or "frio",
    )
    
    if guards_result.get("force_handoff"):
        user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
        db.add(user_message)
        await db.flush()
        
        history = await get_conversation_history(db, lead.id)
        if not lead.summary:
            lead.summary = await generate_lead_summary(
                conversation=history,
                extracted_data=lead.custom_data or {},
                qualification={"qualification": lead.qualification},
            )
        
        handoff_result = await execute_handoff(lead, tenant, "message_limit", db)
        
        assistant_message = Message(
            lead_id=lead.id, role="assistant",
            content=handoff_result["message_for_lead"], tokens_used=0,
        )
        db.add(assistant_message)
        
        await log_ai_action(
            db=db, tenant_id=tenant.id, lead_id=lead.id,
            action_type="handoff", details={"reason": "message_limit"},
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
                "reason": "message_limit",
                "manager_whatsapp": handoff_result["manager_whatsapp"],
            }
        }
    
    if not guards_result.get("can_respond") and guards_result.get("reason") == "out_of_hours":
        user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
        db.add(user_message)
        
        assistant_message = Message(
            lead_id=lead.id, role="assistant",
            content=guards_result["response"], tokens_used=0,
        )
        db.add(assistant_message)
        await db.commit()
        
        return {
            "success": True,
            "reply": guards_result["response"],
            "lead_id": lead.id,
            "is_new_lead": is_new,
            "qualification": lead.qualification,
            "reason": "out_of_hours",
        }
    
    # ==========================================================================
    # 9. VERIFICA HANDOFF POR TRIGGER
    # ==========================================================================
    from src.infrastructure.services import check_handoff_triggers
    trigger_found, trigger_matched = check_handoff_triggers(
        message=content,
        custom_triggers=settings.get("handoff_triggers", []),
    )
    
    if trigger_found:
        user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
        db.add(user_message)
        await db.flush()
        
        history = await get_conversation_history(db, lead.id)
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
    
    # ==========================================================================
    # 10. ATUALIZA STATUS PARA EM_ATENDIMENTO
    # ==========================================================================
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
    
    # ==========================================================================
    # 11. SALVA MENSAGEM DO USUÁRIO
    # ==========================================================================
    user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
    db.add(user_message)
    await db.flush()
    
    await mark_lead_activity(db, lead)
    
    # ==========================================================================
    # 12. BUSCA HISTÓRICO
    # ==========================================================================
    history = await get_conversation_history(db, lead.id)
    
    # ==========================================================================
    # 13. VERIFICA FAQ E ESCOPO
    # ==========================================================================
    faq_response = guards_result.get("response") if guards_result.get("reason") == "faq" else None
    
    if guards_result.get("reason") == "out_of_scope":
        assistant_message = Message(
            lead_id=lead.id, role="assistant",
            content=guards_result["response"], tokens_used=0,
        )
        db.add(assistant_message)
        await db.commit()
        
        return {
            "success": True,
            "reply": guards_result["response"],
            "lead_id": lead.id,
            "is_new_lead": is_new,
            "qualification": lead.qualification,
            "reason": "out_of_scope",
        }
    
    # ==========================================================================
    # 14. MONTA CONTEXTO DO LEAD PARA PERSONALIZAÇÃO
    # ==========================================================================
    lead_context = None
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
    
    # ==========================================================================
    # 15. MONTA PROMPT DO SISTEMA
    # ==========================================================================
    system_prompt = build_system_prompt(
        niche_id=settings.get("niche", "services"),
        company_name=settings.get("company_name", tenant.name),
        tone=settings.get("tone", "cordial"),
        custom_questions=settings.get("custom_questions", []),
        custom_rules=settings.get("custom_rules", []),
        custom_prompt=settings.get("custom_prompt"),
        faq_items=settings.get("faq_items", []),
        scope_description=settings.get("scope_description", ""),
        lead_context=lead_context,
    )
    
    # ==========================================================================
    # 16. CHAMA IA COM CONTEXTO INTELIGENTE + 🔒 ANTI-ALUCINAÇÃO
    # ==========================================================================
    messages = [
        {"role": "system", "content": system_prompt},
        *history,
    ]
    
    # ⭐ ADICIONA INSTRUÇÕES DE SEGURANÇA
    ai_scope = settings.get("ai_scope_description", "")
    ai_fallback = settings.get("ai_out_of_scope_message", 
        "Desculpe, não tenho essa informação. Posso conectar você com nossa equipe?")
    
    if ai_scope:
        security_instructions = build_security_instructions(
            company_name=settings.get("company_name", tenant.name),
            scope_description=ai_scope,
            out_of_scope_message=ai_fallback
        )
        messages[0]["content"] += security_instructions
    
    if faq_response:
        messages.append({
            "role": "system",
            "content": f"INFORMAÇÃO DO FAQ: {faq_response}. Use essa informação para responder o cliente de forma natural."
        })
    
    # Usa resposta com contexto inteligente
    ai_response = await generate_context_aware_response(
        messages=messages,
        lead_data=lead_context or {},
        sentiment=sentiment,
        tone=settings.get("tone", "cordial"),
        is_returning_lead=is_returning_lead,
        hours_since_last_message=hours_since_last,
        previous_summary=previous_summary or lead.summary,
    )
    
    # ⭐ VALIDA RESPOSTA DA IA (ANTI-ALUCINAÇÃO)
    final_response, was_blocked = sanitize_response(
        ai_response["content"],
        ai_fallback
    )
    
    # ⭐ LOG SE BLOQUEOU
    if was_blocked:
        logger.warning(f"⚠️ Resposta bloqueada - Tenant: {tenant.slug}, Lead: {lead.id}")
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
    
    # ⭐ VERIFICA HANDOFF SUGERIDO PELA IA
    handoff_check = check_ai_handoff(content, final_response)
    should_transfer_by_ai = handoff_check["should_handoff"]
    
    # Atualiza resposta para usar a versão validada
    ai_response["content"] = final_response
    
    # Calcula delay humanizado
    typing_delay = calculate_typing_delay(len(final_response))
    
    # Loga resposta da IA com contexto usado
    await log_ai_action(
        db=db,
        tenant_id=tenant.id,
        lead_id=lead.id,
        action_type="response",
        details={
            "tokens_used": ai_response["tokens_used"],
            "context_used": ai_response.get("context_used"),
            "sentiment": sentiment.get("sentiment"),
            "is_returning": is_returning_lead,
            "was_blocked": was_blocked,
        },
    )
    
    # ==========================================================================
    # 17. SALVA RESPOSTA DA IA
    # ==========================================================================
    assistant_message = Message(
        lead_id=lead.id,
        role="assistant",
        content=final_response,  # ⭐ USA A RESPOSTA VALIDADA
        tokens_used=ai_response["tokens_used"],
    )
    db.add(assistant_message)
    
    # ==========================================================================
    # 18. EXTRAI DADOS E QUALIFICA
    # ==========================================================================
    total_messages = len(history) + 2
    
    if total_messages % 2 == 0 or total_messages >= 4:
        await update_lead_data(db, lead, tenant, history + [
            {"role": "user", "content": content},
            {"role": "assistant", "content": final_response},  # ⭐ USA A RESPOSTA VALIDADA
        ])
    
    # ==========================================================================
    # 19. VERIFICA HANDOFF (LEAD HOT OU ⭐ IA SUGERIU)
    # ==========================================================================
    should_transfer_after = (
        lead.qualification in ["quente", "hot"] or 
        should_transfer_by_ai  # ⭐ NOVO: IA pode sugerir handoff
    )
    
    # Define motivo do handoff
    handoff_reason = "lead_hot" if lead.qualification in ["quente", "hot"] else "ai_suggested"
    
    if should_transfer_after:
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
                "reason": handoff_reason,  # ⭐ USA VARIÁVEL
                "qualification": lead.qualification,
                "ai_suggestion": handoff_check.get("reason") if should_transfer_by_ai else None  # ⭐ NOVO
            },
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
                "reason": handoff_reason,
                "manager_whatsapp": handoff_result["manager_whatsapp"],
            },
            "typing_delay": typing_delay,
            "sentiment": sentiment.get("sentiment"),
        }
    
    await db.commit()
    
    return {
        "success": True,
        "reply": final_response,  # ⭐ USA A RESPOSTA VALIDADA
        "lead_id": lead.id,
        "is_new_lead": is_new,
        "qualification": lead.qualification,
        "typing_delay": typing_delay,
        "sentiment": sentiment.get("sentiment"),
        "is_returning_lead": is_returning_lead,
        "was_blocked": was_blocked,  # ⭐ NOVO: indica se resposta foi bloqueada
    }


async def update_lead_data(
    db: AsyncSession,
    lead: Lead,
    tenant: Tenant,
    conversation: list[dict],
) -> None:
    """Extrai dados da conversa e atualiza o lead."""
    settings = tenant.settings or {}
    niche_id = settings.get("niche", "services")
    niche_config = get_niche_config(niche_id)
    
    if not niche_config:
        return
    
    extracted = await extract_lead_data(
        conversation=conversation,
        required_fields=niche_config.required_fields,
        optional_fields=niche_config.optional_fields,
    )
    
    if extracted.get("name") and not lead.name:
        lead.name = extracted["name"]
    if extracted.get("phone") and not lead.phone:
        lead.phone = extracted["phone"]
    if extracted.get("email") and not lead.email:
        lead.email = extracted["email"]
    if extracted.get("city") and not lead.city:
        lead.city = extracted["city"]
    
    custom_fields = {k: v for k, v in extracted.items() 
                     if k not in ["name", "phone", "email", "city"] and v is not None}
    if custom_fields:
        lead.custom_data = {**(lead.custom_data or {}), **custom_fields}
    
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
        
        if new_qualification == "quente" and old_qualification != "quente":
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
    
    required_collected = sum(1 for f in niche_config.required_fields 
                            if extracted.get(f) is not None)
    
    if new_qualification == "quente" or required_collected >= len(niche_config.required_fields) - 1:
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
        
        summary = await generate_lead_summary(
            conversation=conversation,
            extracted_data=extracted,
            qualification=qualification_result,
        )
        lead.summary = summary