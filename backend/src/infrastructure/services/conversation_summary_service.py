"""
SERVIÇO DE RESUMO AUTOMÁTICO DE CONVERSAS
==========================================

Gera resumos inteligentes de conversas longas para:
1. Melhorar performance (menos tokens na IA)
2. Permitir histórico ilimitado
3. Manter contexto mesmo após muitas mensagens

Estratégia:
- A cada 50 mensagens, gera um resumo automático
- Usa GPT-4o-mini para resumir pontos-chave
- Armazena no campo conversation_summary
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Lead, Message
from src.infrastructure.llm import LLMFactory

logger = logging.getLogger(__name__)

# Threshold de mensagens para gerar resumo
SUMMARY_THRESHOLD = 50


async def should_generate_summary(
    db: AsyncSession,
    lead: Lead,
) -> bool:
    """
    Verifica se deve gerar um novo resumo automático.
    
    Critérios:
    - Lead tem >= 50 mensagens
    - Não tem conversation_summary OU
    - Conversation_summary foi gerado há mais de 50 mensagens
    """
    try:
        # Conta total de mensagens
        from sqlalchemy import func
        result = await db.execute(
            select(func.count(Message.id))
            .where(Message.lead_id == lead.id)
        )
        total_messages = result.scalar() or 0
        
        if total_messages < SUMMARY_THRESHOLD:
            return False
        
        # Se não tem resumo, gera
        if not lead.conversation_summary:
            return True
        
        # Se tem, verifica se passou muito tempo desde o último
        # (implementação simples: sempre que atingir múltiplos de 50)
        return total_messages % SUMMARY_THRESHOLD == 0
        
    except Exception as e:
        logger.error(f"Erro verificando necessidade de resumo: {e}")
        return False


async def generate_conversation_summary(
    db: AsyncSession,
    lead_id: int,
) -> Optional[str]:
    """
    Gera resumo automático da conversa usando IA.
    
    Returns:
        String com resumo ou None se falhar
    """
    try:
        # Busca TODAS as mensagens do lead
        result = await db.execute(
            select(Message)
            .where(Message.lead_id == lead_id)
            .order_by(Message.created_at.asc())
        )
        messages = result.scalars().all()
        
        if not messages:
            return None
        
        # Converte para formato de prompt
        conversation_text = ""
        for msg in messages:
            role = "Cliente" if msg.role == "user" else "IA"
            conversation_text += f"{role}: {msg.content}\n"
        
        # Limita tamanho (pega últimas 100 mensagens se for muito grande)
        if len(messages) > 100:
            messages_subset = messages[-100:]
            conversation_text = ""
            for msg in messages_subset:
                role = "Cliente" if msg.role == "user" else "IA"
                conversation_text += f"{role}: {msg.content}\n"
            
            conversation_text = f"[Conversa com {len(messages) - 100} mensagens anteriores omitidas]\n\n" + conversation_text
        
        # Prompt otimizado para resumo
        prompt = f"""Você é um assistente especializado em resumir conversas comerciais.

Analise a conversa abaixo e crie um RESUMO EXECUTIVO focado em:
1. **Interesse principal** do cliente (o que ele quer)
2. **Informações coletadas** (nome, orçamento, prazo, etc.)
3. **Dúvidas/Objeções** levantadas
4. **Próximos passos** ou pendências

CONVERSA:
{conversation_text}

IMPORTANTE:
- Seja CONCISO (máximo 200 palavras)
- Destaque informações ACIONÁVEIS
- Use bullets para clareza
- Não invente informações não mencionadas

RESUMO EXECUTIVO:"""

        provider = LLMFactory.get_provider()
        response = await provider.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # Mais factual
            max_tokens=400,
        )
        
        summary = response["content"].strip()
        
        logger.info(f"✅ Resumo gerado para lead {lead_id}: {len(summary)} chars")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Erro gerando resumo automático: {e}")
        return None


async def update_lead_summary(
    db: AsyncSession,
    lead: Lead,
) -> bool:
    """
    Atualiza o resumo automático do lead se necessário.
    
    Returns:
        True se atualizou, False caso contrário
    """
    try:
        # Verifica se deve gerar
        if not await should_generate_summary(db, lead):
            return False
        
        # Gera resumo
        summary = await generate_conversation_summary(db, lead.id)
        
        if not summary:
            return False
        
        # Atualiza no banco
        lead.conversation_summary = summary
        
        # Adiciona metadata de quando foi gerado
        if not lead.custom_data:
            lead.custom_data = {}
        
        lead.custom_data["summary_generated_at"] = datetime.now(timezone.utc).isoformat()
        lead.custom_data["summary_message_count"] = await get_message_count(db, lead.id)
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(lead, "custom_data")
        
        await db.commit()
        
        logger.info(f"✅ Resumo atualizado para lead {lead.id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro atualizando resumo do lead: {e}")
        await db.rollback()
        return False


async def get_message_count(db: AsyncSession, lead_id: int) -> int:
    """Conta total de mensagens do lead."""
    from sqlalchemy import func
    result = await db.execute(
        select(func.count(Message.id))
        .where(Message.lead_id == lead_id)
    )
    return result.scalar() or 0


async def get_effective_history(
    db: AsyncSession,
    lead: Lead,
    max_recent_messages: int = 30,
) -> List[Dict]:
    """
    Retorna histórico "efetivo" para a IA.
    
    Estratégia:
    - Se tem <50 mensagens: retorna todas
    - Se tem >=50: retorna resumo + últimas 30 mensagens
    
    Isso permite histórico ilimitado sem estourar contexto da IA.
    """
    try:
        # Conta mensagens
        total = await get_message_count(db, lead.id)
        
        # Se tem poucas mensagens, retorna normal
        if total < SUMMARY_THRESHOLD:
            result = await db.execute(
                select(Message)
                .where(Message.lead_id == lead.id)
                .order_by(Message.created_at.asc())
            )
            messages = result.scalars().all()
            return [{"role": msg.role, "content": msg.content} for msg in messages]
        
        # Se tem muitas, usa resumo + recentes
        history = []
        
        # 1. Adiciona resumo como contexto inicial
        if lead.conversation_summary:
            history.append({
                "role": "system",
                "content": f"📋 RESUMO DA CONVERSA ANTERIOR:\n{lead.conversation_summary}\n\n[Retomando conversa recente...]"
            })
        
        # 2. Adiciona últimas N mensagens
        result = await db.execute(
            select(Message)
            .where(Message.lead_id == lead.id)
            .order_by(Message.created_at.desc())
            .limit(max_recent_messages)
        )
        recent_messages = list(reversed(result.scalars().all()))
        
        for msg in recent_messages:
            history.append({"role": msg.role, "content": msg.content})
        
        logger.info(f"📚 Histórico efetivo: {len(history)} mensagens (resumo + {len(recent_messages)} recentes)")
        
        return history
        
    except Exception as e:
        logger.error(f"❌ Erro montando histórico efetivo: {e}")
        # Fallback: retorna últimas N mensagens
        result = await db.execute(
            select(Message)
            .where(Message.lead_id == lead.id)
            .order_by(Message.created_at.desc())
            .limit(max_recent_messages)
        )
        messages = list(reversed(result.scalars().all()))
        return [{"role": msg.role, "content": msg.content} for msg in messages]
