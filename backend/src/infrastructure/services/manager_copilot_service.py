import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.llm.factory import LLMFactory
from src.config import get_settings
from src.domain.entities import Lead, User, Tenant, LeadStatus
from src.infrastructure.services.openai_service import chat_completion

logger = logging.getLogger(__name__)
settings = get_settings()

class ManagerCopilotService:
    """
    Serviço de Inteligência Artificial para Gestores (Jarvis).
    Permite consultas em linguagem natural sobre o negócio.
    """

    SYSTEM_PROMPT = """
    Você é o 'Jarvis', o assistente executivo de inteligência da Vellarys.
    Seu objetivo é ajudar o Gestor Imobiliário a tomar decisões baseadas em dados.
    
    Você tem acesso a ferramentas para consultar dados reais da empresa.
    SEMPRE que o usuário perguntar sobre números, leads, vendedores ou desempenho, USE AS FERRAMENTAS.
    Não invente números. Se a ferramenta retornar dados, analise-os e responda de forma executiva e estratégica.
    
    Estilo de Resposta:
    - Profissional, direto e perspicaz.
    - Use formatação Markdown (negrito, listas) para facilitar leitura.
    - Dê insights, não apenas números. Ex: "A conversão caiu 10%, sugiro focar em..."
    - Se a pergunta for sobre configurações, explique como configurar ou verifique as settings se disponíveis.
    """

    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "get_key_metrics",
                "description": "Retorna métricas chave do negócio: total de leads, novos hoje, vendas no mês, taxa de resposta.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_leads",
                "description": "Busca leads com filtros específicos. Útil para perguntas como 'leads do setor X' ou 'interessados em aluguel'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["new", "open", "in_progress", "converted", "lost"], "description": "Status do lead"},
                        "qualification": {"type": "string", "enum": ["hot", "warm", "cold"], "description": "Qualificação (quente/morno/frio)"},
                        "city": {"type": "string", "description": "Cidade do lead"},
                        "limit": {"type": "integer", "description": "Número máximo de resultados (padrão 5)"}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_seller_ranking",
                "description": "Retorna ranking de vendedores por leads atendidos ou conversões.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period_days": {"type": "integer", "description": "Período em dias (padrão 30)"}
                    },
                    "required": []
                }
            }
        }
    ]

    def __init__(self, db: AsyncSession, tenant: Tenant, user: User):
        self.db = db
        self.tenant = tenant
        self.user = user

    async def process_query(self, query: str, conversation_history: List[Dict] = None) -> str:
        """Processa a pergunta do gestor e retorna a resposta da IA."""
        
        if not conversation_history:
            conversation_history = []
            
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            *conversation_history,
            {"role": "user", "content": query}
        ]

        # 1. Primeira chamada ao LLM para decidir ferramentas
        response = await chat_completion(
            messages=messages,
            tools=self.TOOLS,
            tool_choice="auto",
            temperature=0.3 # Baixa temperatura para precisão no uso de ferramentas
        )

        tool_calls = response.get("tool_calls")

        # 2. Se a IA decidiu usar ferramentas, executamos
        if tool_calls:
            # Adiciona a resposta da IA (com a intenção de chamada) ao histórico
            messages.append(response)

            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])
                
                logger.info(f"Jarvis executando ferramenta: {function_name} com args: {function_args}")
                
                tool_result = await self._execute_tool(function_name, function_args)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": function_name,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

            # 3. Segunda chamada ao LLM para interpretar os resultados e formular a resposta final
            final_response = await chat_completion(
                messages=messages,
                temperature=0.7 # Temperatura mais alta para criatividade na análise
            )
            return final_response["content"]
        
        else:
            # Se não usou ferramentas, retorna a resposta direta (papo furado ou conhecimento geral)
            return response["content"]

    async def _execute_tool(self, name: str, args: dict) -> Any:
        """Dispatcher de ferramentas."""
        if name == "get_key_metrics":
            return await self._tool_get_key_metrics()
        elif name == "search_leads":
            return await self._tool_search_leads(**args)
        elif name == "get_seller_ranking":
            return await self._tool_get_seller_ranking(**args)
        else:
            return {"error": "Ferramenta desconhecida"}

    # =========================================================================
    # IMPLEMENTAÇÃO DAS FERRAMENTAS
    # =========================================================================

    async def _tool_get_key_metrics(self):
        """Calcula métricas básicas."""
        # Total Leads
        q_total = select(func.count(Lead.id)).where(Lead.tenant_id == self.tenant.id)
        total = (await self.db.execute(q_total)).scalar() or 0
        
        # Leads Hoje
        today = datetime.now().date()
        q_today = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= today)
        )
        new_today = (await self.db.execute(q_today)).scalar() or 0
        
        # Leads por Status
        q_status = select(Lead.status, func.count(Lead.id)).where(
            Lead.tenant_id == self.tenant.id
        ).group_by(Lead.status)
        status_rows = (await self.db.execute(q_status)).all()
        status_dist = {r[0]: r[1] for r in status_rows}

        return {
            "total_leads": total,
            "leads_today": new_today,
            "status_distribution": status_dist,
            "analysis_context": "Estes são os dados em tempo real do CRM."
        }

    async def _tool_search_leads(self, status: str = None, qualification: str = None, city: str = None, limit: int = 5):
        """Busca leads com filtros."""
        query = select(Lead).where(Lead.tenant_id == self.tenant.id)
        
        if status:
            query = query.where(Lead.status == status)
        if qualification:
            query = query.where(Lead.qualification == qualification)
        if city:
            # Case insensitive search
            query = query.where(Lead.city.ilike(f"%{city}%"))
            
        query = query.order_by(desc(Lead.created_at)).limit(limit)
        
        result = await self.db.execute(query)
        leads = result.scalars().all()
        
        return [
            {
                "id": l.id,
                "name": l.name,
                "city": l.city,
                "status": l.status,
                "qualification": l.qualification,
                "summary": l.summary,
                "created_at": l.created_at.strftime("%Y-%m-%d")
            }
            for l in leads
        ]

    async def _tool_get_seller_ranking(self, period_days: int = 30):
        """Ranking de vendedores."""
        # Simples contagem de leads atribuídos nos últimos X dias
        since = datetime.now() - timedelta(days=period_days)
        
        q = select(User.name, func.count(Lead.id).label("leads_count"))\
            .join(Lead, Lead.assigned_to == User.id)\
            .where(and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= since))\
            .group_by(User.name)\
            .order_by(desc("leads_count"))
            
        rows = (await self.db.execute(q)).all()
        
        return [
            {"seller": r[0], "leads_assigned": r[1]}
            for r in rows
        ]
