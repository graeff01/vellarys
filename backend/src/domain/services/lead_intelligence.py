"""
INTELIGÊNCIA DE LEADS
=====================
Orquestra qualificação, resumos e notificações inteligentes.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Lead, Message, Tenant
from src.domain.services.lead_qualifier import qualify_lead
from src.domain.services.summary_generator import generate_lead_summary
from src.domain.services.smart_notifications import (
    notify_hot_lead,
    notify_objection,
)

logger = logging.getLogger(__name__)


class LeadIntelligence:
    """
    Camada ORQUESTRADORA de inteligência de leads.

    Responsável por:
    - Decidir mudança de qualificação
    - Decidir geração de resumo
    - Decidir notificações

    ❌ NÃO FAZ commit
    ❌ NÃO decide fluxo da conversa
    """

    async def analyze_conversation(
        self,
        db: AsyncSession,
        lead: Lead,
        messages: List[Message],
        tenant: Tenant
    ) -> Dict[str, Any]:

        result = {
            "qualification_changed": False,
            "old_qualification": lead.qualification,
            "new_qualification": lead.qualification,
            "notifications_sent": [],
            "summary_updated": False,
        }

        try:
            # =====================================================
            # 1. QUALIFICAÇÃO (ANÁLISE)
            # =====================================================
            conversation_text = " ".join(
                m.content for m in messages if m.content
            )

            qualification_data = qualify_lead(
                lead=lead,
                messages=messages,
                conversation_text=conversation_text
            )

            old_qual = lead.qualification
            new_qual = qualification_data["qualification"]

            # Regras de estabilidade
            should_update_qualification = (
                old_qual != new_qual
                and qualification_data["confidence"] >= 0.6
            )

            if should_update_qualification:
                lead.qualification = new_qual
                lead.qualification_confidence = qualification_data["confidence"]
                lead.qualification_score = qualification_data["score"]
                lead.last_qualification_at = datetime.utcnow()

                result["qualification_changed"] = True
                result["new_qualification"] = new_qual

                logger.info(
                    f"Lead {lead.id} qualificação mudou: "
                    f"{old_qual} → {new_qual}"
                )

                # 🔥 Notificação de lead quente
                if new_qual == "hot" and old_qual != "hot":
                    await notify_hot_lead(
                        lead=lead,
                        qualification_data=qualification_data,
                        tenant=tenant,
                    )
                    result["notifications_sent"].append("hot_lead")

            # =====================================================
            # 2. RESUMO (EVENT-BASED)
            # =====================================================
            should_update_summary = (
                result["qualification_changed"]
                or not lead.summary
            )

            if should_update_summary:
                summary = generate_lead_summary(
                    lead=lead,
                    messages=messages,
                    qualification_data=qualification_data,
                )

                if summary != lead.summary:
                    lead.summary = summary
                    result["summary_updated"] = True
                    logger.info(f"Resumo atualizado para lead {lead.id}")

            # =====================================================
            # 3. OBJEÇÕES CRÍTICAS (ÚLTIMA MENSAGEM)
            # =====================================================
            last_user_messages = [
                m for m in messages if m.role == "user"
            ]

            if last_user_messages:
                last_message = last_user_messages[-1].content.lower()

                critical_objections = {
                    "muito caro": "Preço percebido como alto",
                    "tá caro": "Preço percebido como alto",
                    "acima do meu orçamento": "Fora da faixa de orçamento",
                    "não consigo pagar": "Restrição financeira",
                    "não gostei": "Desinteresse explícito",
                }

                for pattern, reason in critical_objections.items():
                    if pattern in last_message:
                        await notify_objection(
                            lead=lead,
                            objection=reason,
                            tenant=tenant,
                        )
                        result["notifications_sent"].append("objection")
                        break

        except Exception as e:
            logger.error(
                f"Erro na análise inteligente do lead {lead.id}",
                exc_info=True
            )

        return result


# Singleton
lead_intelligence = LeadIntelligence()


async def analyze_lead_conversation(
    db: AsyncSession,
    lead: Lead,
    messages: List[Message],
    tenant: Tenant
) -> Dict[str, Any]:
    return await lead_intelligence.analyze_conversation(
        db=db,
        lead=lead,
        messages=messages,
        tenant=tenant,
    )
