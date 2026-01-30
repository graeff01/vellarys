import logging
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.domain.entities import Lead, Message
from src.infrastructure.services.openai_service import chat_completion

logger = logging.getLogger(__name__)

class SalesAdvisorService:
    """
    Serviço especializado em dar dicas táticas para o vendedor (Intelligence Injection).
    Foca no 'agora': o que falar, o que evitar, qual o próximo passo.
    """

    SYSTEM_PROMPT = """
    Você é um Coach de Vendas Sênior da Vellarys (Real Estate).
    Sua missão: Analisar a conversa e dar UMA dica tática e direta para o corretor fechar o negócio.
    
    Analise a conversa e extraia:
    1. O principal interesse/dor do cliente (ex: "Segurança", "Investimento", "Espaço").
    2. O sentimento atual (Positivo/Neutro/Negativo).
    3. Uma "Dica de Ouro" (Actionable Advice).
    
    Regras:
    - Seja curto e direto (estilo tweet).
    - Se o cliente falou de "segurança", mande focar em "guarita blindada".
    - Se o cliente reclamou de preço, mande focar em "financiamento" ou "valorização".
    
    Saída JSON:
    {
        "sentiment": "positive|neutral|negative",
        "key_topic": "string (ex: Segurança)",
        "tip": "string (Dica curta e matadora)",
        "action": "string (Ação sugerida, ex: Enviar vídeo do playground)"
    }
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_insight(self, lead_id: int) -> Dict:
        """Gera um insight tático para um lead específico."""
        
        # 1. Buscar Lead e Mensagens
        lead = await self.db.get(Lead, lead_id)
        if not lead:
            return {"error": "Lead not found"}

        result = await self.db.execute(
            select(Message)
            .where(Message.lead_id == lead_id)
            .order_by(Message.created_at.desc())
            .limit(10) # Analisa as últimas 10 mensagens
        )
        messages = result.scalars().all()
        
        # Se não tem mensagens, retorna insight genérico baseado nos dados do lead
        if not messages:
            return self._generate_cold_start_insight(lead)

        # 2. Preparar contexto para o LLM
        conversation_text = ""
        for msg in reversed(messages): # Ordem cronológica
            sender = "Cliente" if msg.role == "user" else "Vendedor"
            conversation_text += f"{sender}: {msg.content}\n"

        # 3. Chamar LLM
        try:
            prompt = f"""
            Dados do Lead:
            Nome: {lead.name}
            Interesse: {lead.interest}
            Qualificação: {lead.qualification}
            
            Conversa Recente:
            {conversation_text}
            """
            
            response = await chat_completion(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3, # Baixa temperatura para ser consistente
                response_format={"type": "json_object"}
            )
            
            import json
            content = response.get("content", "{}")
            insight_data = json.loads(content)
            
            return insight_data

        except Exception as e:
            logger.error(f"Erro ao gerar insight de vendas: {e}")
            return {
                "sentiment": "neutral",
                "key_topic": "Geral",
                "tip": "Tente engajar o cliente com perguntas abertas.",
                "action": "Ligar para entender necessidades"
            }

    def _generate_cold_start_insight(self, lead: Lead) -> Dict:
        """Gera insight para leads sem mensagens."""
        if lead.qualification == 'hot':
            return {
                "sentiment": "positive",
                "key_topic": "Alta Intenção",
                "tip": "Este lead é quente! Não deixe esfriar.",
                "action": "Ligue agora (Lead tem alta prioridade)"
            }
        else:
            return {
                "sentiment": "neutral",
                "key_topic": "Prospecção",
                "tip": "Inicie a conversa focando em entender a dor dele.",
                "action": "Enviar mensagem de quebra-gelo"
            }
