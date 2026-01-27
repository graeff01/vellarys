import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func, desc, and_, or_, case, cast, Float, extract
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.llm.factory import LLMFactory
from src.config import get_settings
from src.domain.entities import Lead, User, Tenant, LeadStatus
from src.infrastructure.services.openai_service import chat_completion

logger = logging.getLogger(__name__)
settings = get_settings()


class ManagerCopilotService:
    """
    Vellarys Copilot - Assistente Executivo de Inteligência para Gestores.

    Um assistente AI poderoso que ajuda gestores a:
    - Analisar performance da equipe e vendedores
    - Obter insights sobre leads e conversões
    - Tomar decisões baseadas em dados
    - Identificar oportunidades e problemas
    - Receber sugestões proativas de ações

    LIMITAÇÃO: Apenas dados da empresa do gestor logado.
    """

    SYSTEM_PROMPT = """
Você é o **Vellarys Copilot**, o assistente executivo de inteligência da plataforma Vellarys.
Você é o braço direito do gestor, um aliado estratégico que ajuda a tomar decisões inteligentes.

## SUA IDENTIDADE
- Nome: Vellarys Copilot
- Função: Assistente Executivo de Inteligência
- Especialidade: Análise de dados comerciais, performance de equipe, gestão de leads e vendas
- Personalidade: Profissional, perspicaz, direto e sempre útil

## SEU OBJETIVO
Ajudar o gestor a ter total controle e visibilidade sobre sua operação comercial.
Você deve ser proativo, oferecer insights valiosos e ajudar na tomada de decisões.

## CAPACIDADES
Você pode ajudar o gestor com:

### 1. ANÁLISE DE EQUIPE
- Performance individual de vendedores
- Ranking e comparativos entre vendedores
- Identificar destaques e quem precisa de atenção
- Tempo de resposta e engajamento

### 2. ANÁLISE DE LEADS
- Buscar leads específicos com filtros
- Status do funil de vendas
- Qualificação e priorização
- Leads parados ou abandonados

### 3. MÉTRICAS E KPIs
- Métricas em tempo real
- Tendências e comparativos
- Taxa de conversão
- Ticket médio e receita

### 4. INSIGHTS E ALERTAS
- Identificar problemas e gargalos
- Oportunidades de melhoria
- Alertas importantes
- Anomalias nos dados

### 5. SUGESTÕES PROATIVAS
- Ações recomendadas
- Prioridades do dia
- Estratégias de melhoria

## REGRAS ABSOLUTAS (NUNCA QUEBRE ESTAS REGRAS)

1. **ESCOPO LIMITADO**: Você APENAS responde sobre dados da empresa do gestor logado.
   - NUNCA responda sobre outras empresas
   - NUNCA faça pesquisas externas ou na internet
   - NUNCA invente dados ou estatísticas
   - Se perguntarem algo fora do escopo, responda educadamente:
     "Desculpe, como seu assistente da Vellarys, só posso ajudar com dados da sua empresa."

2. **USE AS FERRAMENTAS**: SEMPRE use as ferramentas disponíveis quando o gestor perguntar sobre:
   - Números, métricas ou estatísticas
   - Vendedores ou equipe
   - Leads específicos ou filtros
   - Comparativos ou rankings
   - Performance ou tendências

3. **HONESTIDADE**: Se não houver dados, diga claramente. Nunca invente.

4. **INSIGHTS, NÃO SÓ DADOS**: Não seja um robô que só repete números.
   - Interprete os dados
   - Ofereça contexto e insights
   - Sugira ações quando apropriado
   - Compare com períodos anteriores quando relevante

## FORMATO DE RESPOSTA
- Use Markdown para formatação clara
- Use **negrito** para destacar pontos importantes
- Use listas para múltiplos itens
- Use emojis com moderação para indicadores visuais (📈 📉 ⚠️ ✅ 🔥)
- Seja conciso mas completo

## CONTEXTO DA EMPRESA
Empresa: {tenant_name}
Gestor: {user_name}
Data atual: {current_date}

Lembre-se: Você é um aliado estratégico do gestor. Ajude-o a tomar as melhores decisões!
"""

    TOOLS = [
        # =====================================================================
        # MÉTRICAS E DASHBOARD
        # =====================================================================
        {
            "type": "function",
            "function": {
                "name": "get_dashboard_metrics",
                "description": "Retorna métricas completas do dashboard: total de leads, leads hoje/semana/mês, conversões, taxa de conversão, ticket médio, receita total. Use sempre que o gestor perguntar sobre números gerais, métricas ou 'como está a empresa'.",
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
                "name": "get_pipeline_analysis",
                "description": "Analisa o funil de vendas: leads em cada etapa (novo, em atendimento, em negociação, convertido, perdido), gargalos, velocidade do funil.",
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
                "name": "compare_periods",
                "description": "Compara métricas entre dois períodos. Útil para perguntas como 'como foi essa semana vs semana passada' ou 'comparar este mês com o anterior'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period_type": {
                            "type": "string",
                            "enum": ["day", "week", "month"],
                            "description": "Tipo de período para comparar"
                        }
                    },
                    "required": ["period_type"]
                }
            }
        },

        # =====================================================================
        # EQUIPE E VENDEDORES
        # =====================================================================
        {
            "type": "function",
            "function": {
                "name": "get_team_overview",
                "description": "Visão geral completa da equipe: todos os vendedores ativos, leads atribuídos a cada um, conversões, taxa de conversão individual. Use para perguntas sobre a equipe em geral.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period_days": {
                            "type": "integer",
                            "description": "Período de análise em dias (padrão: 30)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_seller_ranking",
                "description": "Ranking detalhado de vendedores por diferentes critérios: conversões, leads atendidos, taxa de conversão, receita gerada. Use para perguntas sobre 'quem é o melhor vendedor', 'ranking', 'destaque'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric": {
                            "type": "string",
                            "enum": ["conversions", "leads", "conversion_rate", "revenue"],
                            "description": "Métrica para ordenar o ranking (padrão: conversions)"
                        },
                        "period_days": {
                            "type": "integer",
                            "description": "Período em dias (padrão: 30)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Número de vendedores no ranking (padrão: 10)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_seller_details",
                "description": "Detalhes completos de um vendedor específico: performance, leads, conversões, taxa, tempo médio de resposta, leads ativos. Use quando perguntarem sobre um vendedor específico pelo nome.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "seller_name": {
                            "type": "string",
                            "description": "Nome ou parte do nome do vendedor"
                        },
                        "period_days": {
                            "type": "integer",
                            "description": "Período de análise em dias (padrão: 30)"
                        }
                    },
                    "required": ["seller_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_sellers_needing_attention",
                "description": "Identifica vendedores que precisam de atenção: baixa conversão, muitos leads parados, sem atividade recente. Use para perguntas como 'quem precisa de ajuda', 'problemas na equipe'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period_days": {
                            "type": "integer",
                            "description": "Período de análise em dias (padrão: 7)"
                        }
                    },
                    "required": []
                }
            }
        },

        # =====================================================================
        # LEADS
        # =====================================================================
        {
            "type": "function",
            "function": {
                "name": "search_leads",
                "description": "Busca leads com múltiplos filtros: status, qualificação, cidade, vendedor atribuído, período. Use para qualquer busca específica de leads.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["new", "open", "in_progress", "converted", "lost"],
                            "description": "Status do lead"
                        },
                        "qualification": {
                            "type": "string",
                            "enum": ["hot", "warm", "cold"],
                            "description": "Qualificação (quente/morno/frio)"
                        },
                        "city": {
                            "type": "string",
                            "description": "Cidade do lead"
                        },
                        "seller_name": {
                            "type": "string",
                            "description": "Nome do vendedor atribuído"
                        },
                        "days_ago": {
                            "type": "integer",
                            "description": "Leads criados nos últimos X dias"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Número máximo de resultados (padrão: 10)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_lead_details",
                "description": "Detalhes completos de um lead específico pelo nome ou ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_identifier": {
                            "type": "string",
                            "description": "Nome ou ID do lead"
                        }
                    },
                    "required": ["lead_identifier"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_stale_leads",
                "description": "Identifica leads parados/abandonados: sem interação há X dias, leads quentes esfriando, oportunidades perdidas. Use para perguntas sobre 'leads parados', 'abandonados', 'esquecidos'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "inactive_days": {
                            "type": "integer",
                            "description": "Dias sem atividade para considerar parado (padrão: 3)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Número máximo de leads (padrão: 20)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_hot_leads",
                "description": "Lista leads quentes (hot) que precisam de atenção imediata. Use para perguntas sobre 'leads quentes', 'prioridades', 'oportunidades'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Número máximo de leads (padrão: 15)"
                        }
                    },
                    "required": []
                }
            }
        },

        # =====================================================================
        # ANÁLISES E INSIGHTS
        # =====================================================================
        {
            "type": "function",
            "function": {
                "name": "get_conversion_analysis",
                "description": "Análise detalhada de conversões: taxa geral, por vendedor, por origem, por período, motivos de perda. Use para perguntas sobre 'conversão', 'por que perdemos leads', 'taxa de fechamento'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period_days": {
                            "type": "integer",
                            "description": "Período de análise em dias (padrão: 30)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_performance_trends",
                "description": "Tendências de performance ao longo do tempo: evolução de leads, conversões, receita. Identifica se está melhorando ou piorando.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric": {
                            "type": "string",
                            "enum": ["leads", "conversions", "revenue"],
                            "description": "Métrica para analisar tendência"
                        },
                        "period_days": {
                            "type": "integer",
                            "description": "Período de análise em dias (padrão: 30)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_daily_summary",
                "description": "Resumo do dia: leads novos, conversões, destaques, alertas. Use para perguntas como 'como foi hoje', 'resumo do dia', 'o que aconteceu hoje'.",
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
                "name": "get_weekly_summary",
                "description": "Resumo da semana: performance geral, comparativo com semana anterior, destaques, pontos de atenção.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },

        # =====================================================================
        # ALERTAS E SUGESTÕES
        # =====================================================================
        {
            "type": "function",
            "function": {
                "name": "get_alerts_and_issues",
                "description": "Identifica problemas e alertas: leads sem resposta, vendedores inativos, queda de performance, gargalos. Use para perguntas sobre 'problemas', 'alertas', 'o que precisa de atenção'.",
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
                "name": "get_suggested_actions",
                "description": "Sugere ações prioritárias baseadas nos dados: o que fazer agora, próximos passos, melhorias. Use para perguntas como 'o que devo fazer', 'sugestões', 'prioridades', 'próximos passos'.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },

        # =====================================================================
        # RECEITA E VENDAS
        # =====================================================================
        {
            "type": "function",
            "function": {
                "name": "get_revenue_analysis",
                "description": "Análise de receita e vendas: total vendido, ticket médio, por vendedor, por período. Use para perguntas sobre 'receita', 'faturamento', 'vendas', 'dinheiro'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period_days": {
                            "type": "integer",
                            "description": "Período de análise em dias (padrão: 30)"
                        }
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

    def _get_system_prompt(self) -> str:
        """Gera o system prompt com contexto dinâmico."""
        return self.SYSTEM_PROMPT.format(
            tenant_name=self.tenant.name if self.tenant else "Empresa",
            user_name=self.user.name if self.user else "Gestor",
            current_date=datetime.now().strftime("%d/%m/%Y %H:%M")
        )

    async def process_query(self, query: str, conversation_history: List[Dict] = None) -> str:
        """Processa a pergunta do gestor e retorna a resposta da IA."""

        if not conversation_history:
            conversation_history = []

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            *conversation_history,
            {"role": "user", "content": query}
        ]

        # 1. Primeira chamada ao LLM para decidir ferramentas
        response = await chat_completion(
            messages=messages,
            tools=self.TOOLS,
            tool_choice="auto",
            temperature=0.2,  # Baixa temperatura para precisão no uso de ferramentas
            max_tokens=1000   # Mais tokens para respostas completas
        )

        tool_calls = response.get("tool_calls")

        # 2. Se a IA decidiu usar ferramentas, executamos
        if tool_calls:
            assistant_message = {
                "role": "assistant",
                "content": response.get("content") or "",
                "tool_calls": tool_calls
            }
            messages.append(assistant_message)

            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])

                logger.info(f"Vellarys Copilot executando: {function_name} com args: {function_args}")

                try:
                    tool_result = await self._execute_tool(function_name, function_args)
                except Exception as e:
                    logger.error(f"Erro ao executar ferramenta {function_name}: {e}")
                    tool_result = {"error": str(e)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": function_name,
                    "content": json.dumps(tool_result, ensure_ascii=False, default=str)
                })

            # 3. Segunda chamada ao LLM para interpretar os resultados
            final_response = await chat_completion(
                messages=messages,
                temperature=0.6,  # Temperatura moderada para análise criativa
                max_tokens=1500   # Mais tokens para análises detalhadas
            )
            return final_response["content"]

        else:
            return response["content"]

    async def _execute_tool(self, name: str, args: dict) -> Any:
        """Dispatcher de ferramentas."""
        tool_map = {
            # Métricas
            "get_dashboard_metrics": self._tool_get_dashboard_metrics,
            "get_pipeline_analysis": self._tool_get_pipeline_analysis,
            "compare_periods": self._tool_compare_periods,
            # Equipe
            "get_team_overview": self._tool_get_team_overview,
            "get_seller_ranking": self._tool_get_seller_ranking,
            "get_seller_details": self._tool_get_seller_details,
            "get_sellers_needing_attention": self._tool_get_sellers_needing_attention,
            # Leads
            "search_leads": self._tool_search_leads,
            "get_lead_details": self._tool_get_lead_details,
            "get_stale_leads": self._tool_get_stale_leads,
            "get_hot_leads": self._tool_get_hot_leads,
            # Análises
            "get_conversion_analysis": self._tool_get_conversion_analysis,
            "get_performance_trends": self._tool_get_performance_trends,
            "get_daily_summary": self._tool_get_daily_summary,
            "get_weekly_summary": self._tool_get_weekly_summary,
            # Alertas e Sugestões
            "get_alerts_and_issues": self._tool_get_alerts_and_issues,
            "get_suggested_actions": self._tool_get_suggested_actions,
            # Receita
            "get_revenue_analysis": self._tool_get_revenue_analysis,
        }

        handler = tool_map.get(name)
        if handler:
            return await handler(**args)
        return {"error": f"Ferramenta '{name}' não encontrada"}

    # =========================================================================
    # MÉTRICAS E DASHBOARD
    # =========================================================================

    async def _tool_get_dashboard_metrics(self) -> Dict:
        """Métricas completas do dashboard."""
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Total Leads
        q_total = select(func.count(Lead.id)).where(Lead.tenant_id == self.tenant.id)
        total_leads = (await self.db.execute(q_total)).scalar() or 0

        # Leads Hoje
        q_today = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= today)
        )
        leads_today = (await self.db.execute(q_today)).scalar() or 0

        # Leads esta semana
        q_week = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= week_ago)
        )
        leads_week = (await self.db.execute(q_week)).scalar() or 0

        # Leads este mês
        q_month = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= month_ago)
        )
        leads_month = (await self.db.execute(q_month)).scalar() or 0

        # Conversões (leads com status converted)
        q_converted = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.status == "converted")
        )
        total_converted = (await self.db.execute(q_converted)).scalar() or 0

        # Conversões este mês
        q_converted_month = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "converted",
                Lead.updated_at >= month_ago
            )
        )
        conversions_month = (await self.db.execute(q_converted_month)).scalar() or 0

        # Taxa de conversão
        conversion_rate = (total_converted / total_leads * 100) if total_leads > 0 else 0

        # Distribuição por status
        q_status = select(Lead.status, func.count(Lead.id)).where(
            Lead.tenant_id == self.tenant.id
        ).group_by(Lead.status)
        status_rows = (await self.db.execute(q_status)).all()
        status_distribution = {str(r[0]): r[1] for r in status_rows}

        # Distribuição por qualificação
        q_qual = select(Lead.qualification, func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.qualification.isnot(None))
        ).group_by(Lead.qualification)
        qual_rows = (await self.db.execute(q_qual)).all()
        qualification_distribution = {str(r[0]): r[1] for r in qual_rows}

        # Receita total (baseado em conversões - Deal não implementado)
        total_revenue = 0  # TODO: Implementar quando Deal estiver disponível

        return {
            "total_leads": total_leads,
            "leads_today": leads_today,
            "leads_this_week": leads_week,
            "leads_this_month": leads_month,
            "total_conversions": total_converted,
            "conversions_this_month": conversions_month,
            "conversion_rate_percent": round(conversion_rate, 2),
            "status_distribution": status_distribution,
            "qualification_distribution": qualification_distribution,
            "total_revenue": total_revenue,
            "analysis_timestamp": datetime.now().isoformat()
        }

    async def _tool_get_pipeline_analysis(self) -> Dict:
        """Análise detalhada do funil de vendas."""
        # Status count
        q_status = select(Lead.status, func.count(Lead.id)).where(
            Lead.tenant_id == self.tenant.id
        ).group_by(Lead.status)
        status_rows = (await self.db.execute(q_status)).all()

        pipeline = {}
        total = 0
        for status, count in status_rows:
            pipeline[str(status)] = count
            total += count

        # Calcular percentuais
        pipeline_percentages = {}
        for status, count in pipeline.items():
            pipeline_percentages[status] = round(count / total * 100, 1) if total > 0 else 0

        # Identificar gargalos (etapas com muitos leads parados)
        bottlenecks = []
        if pipeline.get("new", 0) > 20:
            bottlenecks.append(f"Muitos leads novos sem atendimento ({pipeline.get('new', 0)} leads)")
        if pipeline.get("open", 0) > 30:
            bottlenecks.append(f"Muitos leads em aberto ({pipeline.get('open', 0)} leads)")
        if pipeline.get("in_progress", 0) > 50:
            bottlenecks.append(f"Leads acumulando em negociação ({pipeline.get('in_progress', 0)} leads)")

        # Taxa de perda
        lost = pipeline.get("lost", 0)
        loss_rate = round(lost / total * 100, 1) if total > 0 else 0

        return {
            "pipeline_stages": pipeline,
            "pipeline_percentages": pipeline_percentages,
            "total_leads": total,
            "bottlenecks_identified": bottlenecks,
            "loss_rate_percent": loss_rate,
            "healthy_pipeline": len(bottlenecks) == 0
        }

    async def _tool_compare_periods(self, period_type: str = "week") -> Dict:
        """Compara métricas entre períodos."""
        today = datetime.now().date()

        if period_type == "day":
            current_start = today
            previous_start = today - timedelta(days=1)
            previous_end = today
            period_label = "hoje vs ontem"
        elif period_type == "week":
            current_start = today - timedelta(days=7)
            previous_start = today - timedelta(days=14)
            previous_end = today - timedelta(days=7)
            period_label = "esta semana vs semana passada"
        else:  # month
            current_start = today - timedelta(days=30)
            previous_start = today - timedelta(days=60)
            previous_end = today - timedelta(days=30)
            period_label = "este mês vs mês passado"

        # Leads período atual
        q_current = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= current_start)
        )
        current_leads = (await self.db.execute(q_current)).scalar() or 0

        # Leads período anterior
        q_previous = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.created_at >= previous_start,
                Lead.created_at < previous_end
            )
        )
        previous_leads = (await self.db.execute(q_previous)).scalar() or 0

        # Conversões período atual
        q_conv_current = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "converted",
                Lead.updated_at >= current_start
            )
        )
        current_conversions = (await self.db.execute(q_conv_current)).scalar() or 0

        # Conversões período anterior
        q_conv_previous = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "converted",
                Lead.updated_at >= previous_start,
                Lead.updated_at < previous_end
            )
        )
        previous_conversions = (await self.db.execute(q_conv_previous)).scalar() or 0

        # Calcular variações
        leads_variation = ((current_leads - previous_leads) / previous_leads * 100) if previous_leads > 0 else 0
        conv_variation = ((current_conversions - previous_conversions) / previous_conversions * 100) if previous_conversions > 0 else 0

        return {
            "comparison": period_label,
            "current_period": {
                "leads": current_leads,
                "conversions": current_conversions
            },
            "previous_period": {
                "leads": previous_leads,
                "conversions": previous_conversions
            },
            "variations": {
                "leads_percent": round(leads_variation, 1),
                "conversions_percent": round(conv_variation, 1)
            },
            "trending_up": leads_variation > 0 and conv_variation > 0
        }

    # =========================================================================
    # EQUIPE E VENDEDORES
    # =========================================================================

    async def _tool_get_team_overview(self, period_days: int = 30) -> Dict:
        """Visão geral completa da equipe."""
        since = datetime.now() - timedelta(days=period_days)

        # Buscar vendedores com leads
        q = select(
            User.id,
            User.name,
            User.email,
            func.count(Lead.id).label("total_leads"),
            func.sum(case((Lead.status == "converted", 1), else_=0)).label("conversions")
        ).outerjoin(
            Lead, and_(Lead.assigned_to == User.id, Lead.created_at >= since)
        ).where(
            and_(User.tenant_id == self.tenant.id, User.role == "vendedor")
        ).group_by(User.id, User.name, User.email)

        rows = (await self.db.execute(q)).all()

        team = []
        for row in rows:
            total = row.total_leads or 0
            conversions = row.conversions or 0
            rate = round(conversions / total * 100, 1) if total > 0 else 0
            team.append({
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "leads_assigned": total,
                "conversions": conversions,
                "conversion_rate_percent": rate
            })

        # Ordenar por conversões
        team.sort(key=lambda x: x["conversions"], reverse=True)

        # Estatísticas gerais
        total_sellers = len(team)
        total_leads = sum(s["leads_assigned"] for s in team)
        total_conversions = sum(s["conversions"] for s in team)
        avg_conversion = round(total_conversions / total_leads * 100, 1) if total_leads > 0 else 0

        return {
            "period_days": period_days,
            "total_sellers": total_sellers,
            "total_leads_assigned": total_leads,
            "total_conversions": total_conversions,
            "average_conversion_rate": avg_conversion,
            "team_members": team,
            "top_performer": team[0]["name"] if team else None
        }

    async def _tool_get_seller_ranking(self, metric: str = "conversions", period_days: int = 30, limit: int = 10) -> Dict:
        """Ranking detalhado de vendedores."""
        since = datetime.now() - timedelta(days=period_days)

        q = select(
            User.name,
            func.count(Lead.id).label("total_leads"),
            func.sum(case((Lead.status == "converted", 1), else_=0)).label("conversions")
        ).join(
            Lead, Lead.assigned_to == User.id
        ).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.created_at >= since,
                User.role == "vendedor"
            )
        ).group_by(User.name)

        rows = (await self.db.execute(q)).all()

        ranking = []
        for row in rows:
            total = row.total_leads or 0
            conversions = row.conversions or 0
            rate = round(conversions / total * 100, 1) if total > 0 else 0
            ranking.append({
                "name": row.name,
                "leads": total,
                "conversions": conversions,
                "conversion_rate": rate
            })

        # Ordenar pelo critério escolhido
        sort_key = {
            "conversions": lambda x: x["conversions"],
            "leads": lambda x: x["leads"],
            "conversion_rate": lambda x: x["conversion_rate"],
            "revenue": lambda x: x["conversions"]  # Simplificado
        }.get(metric, lambda x: x["conversions"])

        ranking.sort(key=sort_key, reverse=True)
        ranking = ranking[:limit]

        # Adicionar posição
        for i, seller in enumerate(ranking, 1):
            seller["position"] = i

        return {
            "metric_used": metric,
            "period_days": period_days,
            "ranking": ranking,
            "total_sellers_ranked": len(ranking)
        }

    async def _tool_get_seller_details(self, seller_name: str, period_days: int = 30) -> Dict:
        """Detalhes completos de um vendedor."""
        since = datetime.now() - timedelta(days=period_days)

        # Buscar vendedor
        q_seller = select(User).where(
            and_(
                User.tenant_id == self.tenant.id,
                User.name.ilike(f"%{seller_name}%")
            )
        )
        result = await self.db.execute(q_seller)
        seller = result.scalar_one_or_none()

        if not seller:
            return {"error": f"Vendedor '{seller_name}' não encontrado"}

        # Métricas do vendedor
        q_leads = select(
            func.count(Lead.id).label("total"),
            func.sum(case((Lead.status == "converted", 1), else_=0)).label("conversions"),
            func.sum(case((Lead.status == "lost", 1), else_=0)).label("lost"),
            func.sum(case((Lead.status == "new", 1), else_=0)).label("new"),
            func.sum(case((Lead.status == "in_progress", 1), else_=0)).label("in_progress"),
            func.sum(case((Lead.qualification == "hot", 1), else_=0)).label("hot_leads")
        ).where(
            and_(Lead.assigned_to == seller.id, Lead.created_at >= since)
        )

        metrics = (await self.db.execute(q_leads)).one()

        total = metrics.total or 0
        conversions = metrics.conversions or 0
        rate = round(conversions / total * 100, 1) if total > 0 else 0

        # Leads ativos (não convertidos nem perdidos)
        active_leads = (metrics.new or 0) + (metrics.in_progress or 0)

        return {
            "seller": {
                "id": seller.id,
                "name": seller.name,
                "email": seller.email,
                "role": seller.role
            },
            "period_days": period_days,
            "performance": {
                "total_leads": total,
                "conversions": conversions,
                "lost": metrics.lost or 0,
                "conversion_rate_percent": rate,
                "active_leads": active_leads,
                "hot_leads": metrics.hot_leads or 0
            },
            "status_breakdown": {
                "new": metrics.new or 0,
                "in_progress": metrics.in_progress or 0,
                "converted": conversions,
                "lost": metrics.lost or 0
            }
        }

    async def _tool_get_sellers_needing_attention(self, period_days: int = 7) -> Dict:
        """Identifica vendedores que precisam de atenção."""
        since = datetime.now() - timedelta(days=period_days)

        q = select(
            User.name,
            func.count(Lead.id).label("total_leads"),
            func.sum(case((Lead.status == "converted", 1), else_=0)).label("conversions"),
            func.sum(case((Lead.status == "new", 1), else_=0)).label("new_leads")
        ).outerjoin(
            Lead, and_(Lead.assigned_to == User.id, Lead.created_at >= since)
        ).where(
            and_(User.tenant_id == self.tenant.id, User.role == "vendedor")
        ).group_by(User.name)

        rows = (await self.db.execute(q)).all()

        attention_needed = []
        for row in rows:
            total = row.total_leads or 0
            conversions = row.conversions or 0
            new_leads = row.new_leads or 0
            rate = round(conversions / total * 100, 1) if total > 0 else 0

            issues = []

            # Sem conversões
            if total > 5 and conversions == 0:
                issues.append("Nenhuma conversão no período")

            # Taxa de conversão muito baixa
            if total > 10 and rate < 5:
                issues.append(f"Taxa de conversão muito baixa ({rate}%)")

            # Muitos leads novos parados
            if new_leads > 10:
                issues.append(f"Muitos leads novos sem atendimento ({new_leads})")

            # Sem atividade
            if total == 0:
                issues.append("Sem leads atribuídos no período")

            if issues:
                attention_needed.append({
                    "seller_name": row.name,
                    "total_leads": total,
                    "conversions": conversions,
                    "conversion_rate": rate,
                    "issues": issues
                })

        return {
            "period_days": period_days,
            "sellers_needing_attention": len(attention_needed),
            "details": attention_needed
        }

    # =========================================================================
    # LEADS
    # =========================================================================

    async def _tool_search_leads(
        self,
        status: str = None,
        qualification: str = None,
        city: str = None,
        seller_name: str = None,
        days_ago: int = None,
        limit: int = 10
    ) -> Dict:
        """Busca leads com múltiplos filtros."""
        query = select(Lead, User.name.label("seller_name")).outerjoin(
            User, Lead.assigned_to == User.id
        ).where(Lead.tenant_id == self.tenant.id)

        filters_applied = []

        if status:
            query = query.where(Lead.status == status)
            filters_applied.append(f"status={status}")
        if qualification:
            query = query.where(Lead.qualification == qualification)
            filters_applied.append(f"qualificação={qualification}")
        if city:
            query = query.where(Lead.city.ilike(f"%{city}%"))
            filters_applied.append(f"cidade contém '{city}'")
        if seller_name:
            query = query.where(User.name.ilike(f"%{seller_name}%"))
            filters_applied.append(f"vendedor contém '{seller_name}'")
        if days_ago:
            since = datetime.now() - timedelta(days=days_ago)
            query = query.where(Lead.created_at >= since)
            filters_applied.append(f"últimos {days_ago} dias")

        query = query.order_by(desc(Lead.created_at)).limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        leads = []
        for row in rows:
            lead = row[0]
            seller = row[1]
            leads.append({
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "city": lead.city,
                "status": str(lead.status),
                "qualification": str(lead.qualification) if lead.qualification else None,
                "assigned_to": seller,
                "summary": lead.summary[:100] if lead.summary else None,
                "created_at": lead.created_at.strftime("%d/%m/%Y")
            })

        return {
            "filters_applied": filters_applied,
            "total_found": len(leads),
            "limit": limit,
            "leads": leads
        }

    async def _tool_get_lead_details(self, lead_identifier: str) -> Dict:
        """Detalhes completos de um lead."""
        # Tentar buscar por ID ou nome
        try:
            lead_id = int(lead_identifier)
            q = select(Lead, User.name.label("seller_name")).outerjoin(
                User, Lead.assigned_to == User.id
            ).where(
                and_(Lead.tenant_id == self.tenant.id, Lead.id == lead_id)
            )
        except ValueError:
            q = select(Lead, User.name.label("seller_name")).outerjoin(
                User, Lead.assigned_to == User.id
            ).where(
                and_(Lead.tenant_id == self.tenant.id, Lead.name.ilike(f"%{lead_identifier}%"))
            )

        result = await self.db.execute(q)
        row = result.first()

        if not row:
            return {"error": f"Lead '{lead_identifier}' não encontrado"}

        lead = row[0]
        seller = row[1]

        return {
            "lead": {
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "email": lead.email,
                "city": lead.city,
                "status": str(lead.status),
                "qualification": str(lead.qualification) if lead.qualification else None,
                "assigned_to": seller,
                "summary": lead.summary,
                "custom_data": lead.custom_data,
                "created_at": lead.created_at.strftime("%d/%m/%Y %H:%M"),
                "updated_at": lead.updated_at.strftime("%d/%m/%Y %H:%M") if lead.updated_at else None
            }
        }

    async def _tool_get_stale_leads(self, inactive_days: int = 3, limit: int = 20) -> Dict:
        """Identifica leads parados/abandonados."""
        stale_date = datetime.now() - timedelta(days=inactive_days)

        q = select(Lead, User.name.label("seller_name")).outerjoin(
            User, Lead.assigned_to == User.id
        ).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status.notin_(["converted", "lost"]),
                Lead.updated_at < stale_date
            )
        ).order_by(Lead.updated_at).limit(limit)

        result = await self.db.execute(q)
        rows = result.all()

        stale_leads = []
        for row in rows:
            lead = row[0]
            seller = row[1]
            days_inactive = (datetime.now() - lead.updated_at).days if lead.updated_at else inactive_days
            stale_leads.append({
                "id": lead.id,
                "name": lead.name,
                "status": str(lead.status),
                "qualification": str(lead.qualification) if lead.qualification else None,
                "assigned_to": seller,
                "days_inactive": days_inactive,
                "last_activity": lead.updated_at.strftime("%d/%m/%Y") if lead.updated_at else "N/A"
            })

        # Alertas por qualificação
        hot_stale = [l for l in stale_leads if l["qualification"] == "hot"]
        warm_stale = [l for l in stale_leads if l["qualification"] == "warm"]

        return {
            "inactive_days_threshold": inactive_days,
            "total_stale_leads": len(stale_leads),
            "hot_leads_stale": len(hot_stale),
            "warm_leads_stale": len(warm_stale),
            "critical_alert": len(hot_stale) > 0,
            "leads": stale_leads
        }

    async def _tool_get_hot_leads(self, limit: int = 15) -> Dict:
        """Lista leads quentes que precisam de atenção."""
        q = select(Lead, User.name.label("seller_name")).outerjoin(
            User, Lead.assigned_to == User.id
        ).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.qualification == "hot",
                Lead.status.notin_(["converted", "lost"])
            )
        ).order_by(desc(Lead.created_at)).limit(limit)

        result = await self.db.execute(q)
        rows = result.all()

        hot_leads = []
        for row in rows:
            lead = row[0]
            seller = row[1]
            hot_leads.append({
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "status": str(lead.status),
                "assigned_to": seller or "Não atribuído",
                "created_at": lead.created_at.strftime("%d/%m/%Y"),
                "summary": lead.summary[:80] if lead.summary else None
            })

        unassigned = [l for l in hot_leads if l["assigned_to"] == "Não atribuído"]

        return {
            "total_hot_leads": len(hot_leads),
            "unassigned_hot_leads": len(unassigned),
            "urgent_action_needed": len(unassigned) > 0,
            "leads": hot_leads
        }

    # =========================================================================
    # ANÁLISES E INSIGHTS
    # =========================================================================

    async def _tool_get_conversion_analysis(self, period_days: int = 30) -> Dict:
        """Análise detalhada de conversões."""
        since = datetime.now() - timedelta(days=period_days)

        # Totais
        q_total = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= since)
        )
        total = (await self.db.execute(q_total)).scalar() or 0

        q_converted = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "converted",
                Lead.created_at >= since
            )
        )
        converted = (await self.db.execute(q_converted)).scalar() or 0

        q_lost = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "lost",
                Lead.created_at >= since
            )
        )
        lost = (await self.db.execute(q_lost)).scalar() or 0

        conversion_rate = round(converted / total * 100, 1) if total > 0 else 0
        loss_rate = round(lost / total * 100, 1) if total > 0 else 0

        # Conversão por vendedor
        q_by_seller = select(
            User.name,
            func.count(Lead.id).label("total"),
            func.sum(case((Lead.status == "converted", 1), else_=0)).label("converted")
        ).join(
            Lead, Lead.assigned_to == User.id
        ).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= since)
        ).group_by(User.name)

        seller_rows = (await self.db.execute(q_by_seller)).all()
        by_seller = []
        for row in seller_rows:
            seller_total = row.total or 0
            seller_converted = row.converted or 0
            rate = round(seller_converted / seller_total * 100, 1) if seller_total > 0 else 0
            by_seller.append({
                "seller": row.name,
                "total": seller_total,
                "converted": seller_converted,
                "rate": rate
            })
        by_seller.sort(key=lambda x: x["rate"], reverse=True)

        # Conversão por qualificação
        q_by_qual = select(
            Lead.qualification,
            func.count(Lead.id).label("total"),
            func.sum(case((Lead.status == "converted", 1), else_=0)).label("converted")
        ).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= since)
        ).group_by(Lead.qualification)

        qual_rows = (await self.db.execute(q_by_qual)).all()
        by_qualification = {}
        for row in qual_rows:
            qual_total = row.total or 0
            qual_converted = row.converted or 0
            rate = round(qual_converted / qual_total * 100, 1) if qual_total > 0 else 0
            by_qualification[str(row.qualification) if row.qualification else "undefined"] = {
                "total": qual_total,
                "converted": qual_converted,
                "rate": rate
            }

        return {
            "period_days": period_days,
            "overview": {
                "total_leads": total,
                "converted": converted,
                "lost": lost,
                "conversion_rate_percent": conversion_rate,
                "loss_rate_percent": loss_rate
            },
            "by_seller": by_seller,
            "by_qualification": by_qualification,
            "insights": [
                f"Taxa de conversão geral: {conversion_rate}%",
                f"Taxa de perda: {loss_rate}%",
                f"Melhor vendedor: {by_seller[0]['seller']} ({by_seller[0]['rate']}%)" if by_seller else "N/A"
            ]
        }

    async def _tool_get_performance_trends(self, metric: str = "leads", period_days: int = 30) -> Dict:
        """Tendências de performance ao longo do tempo."""
        # Dividir o período em semanas
        weeks = []
        for i in range(4):
            week_end = datetime.now() - timedelta(days=i*7)
            week_start = week_end - timedelta(days=7)

            if metric == "leads":
                q = select(func.count(Lead.id)).where(
                    and_(
                        Lead.tenant_id == self.tenant.id,
                        Lead.created_at >= week_start,
                        Lead.created_at < week_end
                    )
                )
            else:  # conversions
                q = select(func.count(Lead.id)).where(
                    and_(
                        Lead.tenant_id == self.tenant.id,
                        Lead.status == "converted",
                        Lead.updated_at >= week_start,
                        Lead.updated_at < week_end
                    )
                )

            count = (await self.db.execute(q)).scalar() or 0
            weeks.append({
                "week": f"Semana {4-i}",
                "start": week_start.strftime("%d/%m"),
                "end": week_end.strftime("%d/%m"),
                "value": count
            })

        weeks.reverse()

        # Calcular tendência
        if len(weeks) >= 2:
            first_half = sum(w["value"] for w in weeks[:2])
            second_half = sum(w["value"] for w in weeks[2:])
            if first_half > 0:
                trend_percent = round((second_half - first_half) / first_half * 100, 1)
            else:
                trend_percent = 100 if second_half > 0 else 0
            trending = "up" if trend_percent > 0 else "down" if trend_percent < 0 else "stable"
        else:
            trend_percent = 0
            trending = "stable"

        return {
            "metric": metric,
            "period_days": period_days,
            "weekly_data": weeks,
            "trend": {
                "direction": trending,
                "change_percent": trend_percent
            },
            "summary": f"{'📈 Crescendo' if trending == 'up' else '📉 Caindo' if trending == 'down' else '➡️ Estável'} {abs(trend_percent)}% nas últimas semanas"
        }

    async def _tool_get_daily_summary(self) -> Dict:
        """Resumo do dia."""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # Leads hoje
        q_today = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= today)
        )
        leads_today = (await self.db.execute(q_today)).scalar() or 0

        # Leads ontem (para comparar)
        q_yesterday = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.created_at >= yesterday,
                Lead.created_at < today
            )
        )
        leads_yesterday = (await self.db.execute(q_yesterday)).scalar() or 0

        # Conversões hoje
        q_conv = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "converted",
                Lead.updated_at >= today
            )
        )
        conversions_today = (await self.db.execute(q_conv)).scalar() or 0

        # Leads quentes não atendidos
        q_hot = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.qualification == "hot",
                Lead.status == "new"
            )
        )
        hot_unattended = (await self.db.execute(q_hot)).scalar() or 0

        # Variação
        variation = leads_today - leads_yesterday
        variation_text = f"+{variation}" if variation > 0 else str(variation)

        return {
            "date": today.strftime("%d/%m/%Y"),
            "metrics": {
                "new_leads": leads_today,
                "vs_yesterday": variation_text,
                "conversions": conversions_today,
                "hot_unattended": hot_unattended
            },
            "highlights": [],
            "alerts": [
                f"⚠️ {hot_unattended} leads quentes aguardando atendimento" if hot_unattended > 0 else None
            ],
            "summary": f"Hoje: {leads_today} novos leads ({variation_text} vs ontem), {conversions_today} conversões"
        }

    async def _tool_get_weekly_summary(self) -> Dict:
        """Resumo da semana."""
        today = datetime.now().date()
        week_start = today - timedelta(days=7)
        prev_week_start = today - timedelta(days=14)

        # Esta semana
        q_this_week = select(
            func.count(Lead.id).label("total"),
            func.sum(case((Lead.status == "converted", 1), else_=0)).label("conversions")
        ).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= week_start)
        )
        this_week = (await self.db.execute(q_this_week)).one()

        # Semana passada
        q_last_week = select(
            func.count(Lead.id).label("total"),
            func.sum(case((Lead.status == "converted", 1), else_=0)).label("conversions")
        ).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.created_at >= prev_week_start,
                Lead.created_at < week_start
            )
        )
        last_week = (await self.db.execute(q_last_week)).one()

        # Calcular variações
        leads_var = ((this_week.total or 0) - (last_week.total or 0))
        conv_var = ((this_week.conversions or 0) - (last_week.conversions or 0))

        # Top performer da semana
        q_top = select(
            User.name,
            func.sum(case((Lead.status == "converted", 1), else_=0)).label("conversions")
        ).join(
            Lead, Lead.assigned_to == User.id
        ).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= week_start)
        ).group_by(User.name).order_by(desc("conversions")).limit(1)

        top_result = (await self.db.execute(q_top)).first()
        top_performer = top_result[0] if top_result else None

        return {
            "period": f"{week_start.strftime('%d/%m')} - {today.strftime('%d/%m')}",
            "this_week": {
                "leads": this_week.total or 0,
                "conversions": this_week.conversions or 0
            },
            "last_week": {
                "leads": last_week.total or 0,
                "conversions": last_week.conversions or 0
            },
            "variations": {
                "leads": f"+{leads_var}" if leads_var > 0 else str(leads_var),
                "conversions": f"+{conv_var}" if conv_var > 0 else str(conv_var)
            },
            "top_performer": top_performer,
            "summary": f"Semana: {this_week.total or 0} leads, {this_week.conversions or 0} conversões. Destaque: {top_performer or 'N/A'}"
        }

    # =========================================================================
    # ALERTAS E SUGESTÕES
    # =========================================================================

    async def _tool_get_alerts_and_issues(self) -> Dict:
        """Identifica problemas e alertas."""
        alerts = []

        # 1. Leads quentes sem atendimento
        q_hot_new = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.qualification == "hot",
                Lead.status == "new"
            )
        )
        hot_new = (await self.db.execute(q_hot_new)).scalar() or 0
        if hot_new > 0:
            alerts.append({
                "severity": "critical",
                "type": "leads_hot_unattended",
                "message": f"{hot_new} leads QUENTES aguardando primeiro contato",
                "action": "Atribuir e contatar imediatamente"
            })

        # 2. Leads parados há mais de 3 dias
        stale_date = datetime.now() - timedelta(days=3)
        q_stale = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status.notin_(["converted", "lost"]),
                Lead.updated_at < stale_date
            )
        )
        stale_count = (await self.db.execute(q_stale)).scalar() or 0
        if stale_count > 10:
            alerts.append({
                "severity": "high",
                "type": "leads_stale",
                "message": f"{stale_count} leads sem movimentação há mais de 3 dias",
                "action": "Revisar e reativar ou encerrar"
            })

        # 3. Leads não atribuídos
        q_unassigned = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.assigned_to.is_(None),
                Lead.status.notin_(["converted", "lost"])
            )
        )
        unassigned = (await self.db.execute(q_unassigned)).scalar() or 0
        if unassigned > 5:
            alerts.append({
                "severity": "medium",
                "type": "leads_unassigned",
                "message": f"{unassigned} leads sem vendedor atribuído",
                "action": "Distribuir entre a equipe"
            })

        # 4. Taxa de conversão baixa
        q_total = select(func.count(Lead.id)).where(Lead.tenant_id == self.tenant.id)
        total = (await self.db.execute(q_total)).scalar() or 0
        q_converted = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.status == "converted")
        )
        converted = (await self.db.execute(q_converted)).scalar() or 0
        conversion_rate = (converted / total * 100) if total > 0 else 0

        if conversion_rate < 10 and total > 50:
            alerts.append({
                "severity": "high",
                "type": "low_conversion",
                "message": f"Taxa de conversão baixa: {round(conversion_rate, 1)}%",
                "action": "Analisar funil e capacitar equipe"
            })

        return {
            "total_alerts": len(alerts),
            "critical_alerts": len([a for a in alerts if a["severity"] == "critical"]),
            "alerts": alerts,
            "status": "needs_attention" if alerts else "all_clear"
        }

    async def _tool_get_suggested_actions(self) -> Dict:
        """Sugere ações prioritárias baseadas nos dados."""
        suggestions = []

        # Analisar dados para gerar sugestões

        # 1. Leads quentes sem atendimento
        q_hot_new = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.qualification == "hot",
                Lead.status == "new"
            )
        )
        hot_new = (await self.db.execute(q_hot_new)).scalar() or 0
        if hot_new > 0:
            suggestions.append({
                "priority": 1,
                "action": f"🔥 URGENTE: Contatar {hot_new} leads quentes aguardando",
                "reason": "Leads quentes têm maior probabilidade de conversão",
                "impact": "alto"
            })

        # 2. Leads não atribuídos
        q_unassigned = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.assigned_to.is_(None),
                Lead.status == "new"
            )
        )
        unassigned = (await self.db.execute(q_unassigned)).scalar() or 0
        if unassigned > 0:
            suggestions.append({
                "priority": 2,
                "action": f"📋 Distribuir {unassigned} leads novos para a equipe",
                "reason": "Leads sem dono tendem a ser esquecidos",
                "impact": "alto"
            })

        # 3. Leads parados
        stale_date = datetime.now() - timedelta(days=5)
        q_stale = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status.notin_(["converted", "lost"]),
                Lead.updated_at < stale_date
            )
        )
        stale_count = (await self.db.execute(q_stale)).scalar() or 0
        if stale_count > 10:
            suggestions.append({
                "priority": 3,
                "action": f"🔄 Revisar {stale_count} leads parados há mais de 5 dias",
                "reason": "Reativar ou encerrar para limpar o funil",
                "impact": "médio"
            })

        # 4. Análise de performance
        suggestions.append({
            "priority": 4,
            "action": "📊 Revisar ranking de vendedores e dar feedback",
            "reason": "Reconhecer top performers e apoiar quem precisa",
            "impact": "médio"
        })

        # 5. Sugestão de meta
        q_month = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "converted",
                Lead.updated_at >= datetime.now() - timedelta(days=30)
            )
        )
        month_conversions = (await self.db.execute(q_month)).scalar() or 0
        suggestions.append({
            "priority": 5,
            "action": f"🎯 Meta sugerida: {int(month_conversions * 1.1)} conversões no próximo mês (+10%)",
            "reason": "Crescimento sustentável baseado no histórico",
            "impact": "estratégico"
        })

        return {
            "total_suggestions": len(suggestions),
            "suggestions": sorted(suggestions, key=lambda x: x["priority"]),
            "focus_message": "Foque primeiro nas ações de alta prioridade (🔥)"
        }

    async def _tool_get_revenue_analysis(self, period_days: int = 30) -> Dict:
        """Análise de receita e vendas (baseado em conversões)."""
        since = datetime.now() - timedelta(days=period_days)

        # Usar conversões como proxy para vendas (Deal não implementado ainda)
        q_conversions = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "converted",
                Lead.updated_at >= since
            )
        )
        deal_count = (await self.db.execute(q_conversions)).scalar() or 0

        # Conversões por vendedor
        q_by_seller = select(
            User.name,
            func.count(Lead.id).label("conversions")
        ).join(
            Lead, Lead.assigned_to == User.id
        ).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "converted",
                Lead.updated_at >= since
            )
        ).group_by(User.name).order_by(desc("conversions"))

        seller_rows = (await self.db.execute(q_by_seller)).all()
        by_seller = [
            {"seller": r.name, "conversions": r.conversions or 0}
            for r in seller_rows
        ]

        return {
            "period_days": period_days,
            "sales": {
                "total_conversions": deal_count,
                "note": "Valores de receita não disponíveis - mostrando conversões"
            },
            "by_seller": by_seller,
            "tip": "Para análise de receita detalhada, configure os valores nos negócios fechados"
        }
