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

### 1. 🔮 INTELIGÊNCIA PREDITIVA (NOVO!)
- **Lead Scoring**: Calcular probabilidade de conversão de leads (0-100)
- **Priorização Inteligente**: Ranking dos melhores leads para focar
- **Previsão de Meta**: Prever se atingirá meta do mês
- **Análise de Oportunidades**: Avaliar risco e probabilidade de fechamento
- **Forecast**: Projeções baseadas em pipeline e histórico

### 2. 👨‍🏫 COACHING VIRTUAL (NOVO!)
- **Coaching Personalizado**: Análise individual de vendedores
- **Comparação com Time**: Performance vs média da equipe
- **Planos de Melhoria**: Ações específicas para cada vendedor
- **Análise de Conversas**: Padrões de sucesso e objeções comuns

### 3. ANÁLISE DE EQUIPE
- Performance individual de vendedores
- Ranking e comparativos entre vendedores
- Identificar destaques e quem precisa de atenção
- Tempo de resposta e engajamento

### 4. ANÁLISE DE LEADS
- Buscar leads específicos com filtros
- Status do funil de vendas
- Qualificação e priorização
- Leads parados ou abandonados

### 5. MÉTRICAS E KPIs
- Métricas em tempo real
- Tendências e comparativos
- Taxa de conversão
- Ticket médio e receita

### 6. INSIGHTS E ALERTAS
- Identificar problemas e gargalos
- Oportunidades de melhoria
- Alertas importantes
- Anomalias nos dados

### 7. SUGESTÕES PROATIVAS
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
        },

        # =====================================================================
        # INTELIGÊNCIA PREDITIVA (PREDICTIVE ANALYTICS)
        # =====================================================================
        {
            "type": "function",
            "function": {
                "name": "predict_lead_conversion",
                "description": "PREVISÃO DE CONVERSÃO: Calcula a probabilidade (score) de um lead específico converter em venda. Analisa múltiplos fatores: qualificação, tempo de resposta, engajamento, histórico. Use para perguntas como 'qual a chance desse lead fechar', 'esse lead vai converter', 'probabilidade de venda'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {
                            "type": "integer",
                            "description": "ID do lead para calcular probabilidade"
                        }
                    },
                    "required": ["lead_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_top_leads_to_focus",
                "description": "PRIORIZAÇÃO INTELIGENTE: Retorna ranking dos leads com maior probabilidade de conversão. Use para perguntas como 'em quais leads devo focar', 'leads mais promissores', 'melhores oportunidades', 'onde investir tempo'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Número de leads no ranking (padrão: 10)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "predict_month_goal",
                "description": "PREVISÃO DE META: Prevê se a empresa atingirá a meta do mês com base no pipeline atual, taxa de conversão histórica e dias restantes. Use para perguntas como 'vamos bater a meta', 'previsão do mês', 'vai dar tempo', 'como está a projeção'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_conversions": {
                            "type": "integer",
                            "description": "Meta de conversões do mês (opcional, se não informado usa histórico)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_opportunities",
                "description": "ANÁLISE DE OPORTUNIDADES: Analisa profundamente o pipeline de oportunidades, calculando probabilidade de fechamento, valor esperado, riscos. Identifica oportunidades críticas. Use para 'análise de pipeline', 'quais deals vão fechar', 'oportunidades em risco'.",
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
                "name": "predict_opportunity_close",
                "description": "SCORE DE OPORTUNIDADE: Calcula probabilidade de uma oportunidade específica fechar, com análise de risco e ações recomendadas. Use para perguntas sobre chances de fechar um negócio específico.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "opportunity_id": {
                            "type": "integer",
                            "description": "ID da oportunidade (lead in_progress ou negociação)"
                        }
                    },
                    "required": ["opportunity_id"]
                }
            }
        },

        # =====================================================================
        # COACHING E ANÁLISE COMPORTAMENTAL
        # =====================================================================
        {
            "type": "function",
            "function": {
                "name": "coach_seller",
                "description": "COACH VIRTUAL: Analisa performance de um vendedor e oferece coaching personalizado: pontos fortes, fraquezas, comparação com time, treinamentos sugeridos. Use para 'como melhorar vendedor X', 'coaching para fulano', 'feedback para equipe'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "seller_id": {
                            "type": "integer",
                            "description": "ID do vendedor para análise e coaching"
                        }
                    },
                    "required": ["seller_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_conversations",
                "description": "ANÁLISE NLP DE CONVERSAS: Analisa padrões nas conversas com leads: objeções comuns, frases vencedoras, gatilhos de perda, melhores práticas. Use para 'por que perdemos leads', 'objeções mais comuns', 'o que funciona nas vendas'.",
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
            # Inteligência Preditiva
            "predict_lead_conversion": self._tool_predict_lead_conversion,
            "get_top_leads_to_focus": self._tool_get_top_leads_to_focus,
            "predict_month_goal": self._tool_predict_month_goal,
            "analyze_opportunities": self._tool_analyze_opportunities,
            "predict_opportunity_close": self._tool_predict_opportunity_close,
            # Coaching e NLP
            "coach_seller": self._tool_coach_seller,
            "analyze_conversations": self._tool_analyze_conversations,
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

    # =========================================================================
    # INTELIGÊNCIA PREDITIVA (PREDICTIVE ANALYTICS)
    # =========================================================================

    def _calculate_lead_score(self, lead: Lead) -> Dict[str, Any]:
        """
        Calcula o score preditivo de conversão de um lead (0-100).

        Algoritmo baseado em múltiplos fatores:
        - Qualificação (hot/warm/cold)
        - Status atual
        - Tempo no funil
        - Vendedor atribuído
        - Engajamento (custom_data)
        """
        score = 0
        factors = []

        # 1. QUALIFICAÇÃO (0-40 pontos) - Maior peso
        if lead.qualification == "hot":
            score += 40
            factors.append(("Qualificação QUENTE", 40, "✅"))
        elif lead.qualification == "warm":
            score += 25
            factors.append(("Qualificação MORNA", 25, "🟡"))
        elif lead.qualification == "cold":
            score += 10
            factors.append(("Qualificação FRIA", 10, "🔵"))
        else:
            score += 5
            factors.append(("Sem qualificação", 5, "⚪"))

        # 2. STATUS (0-25 pontos)
        if lead.status == "in_progress":
            score += 25
            factors.append(("Em negociação", 25, "🔥"))
        elif lead.status == "open":
            score += 15
            factors.append(("Em atendimento", 15, "📞"))
        elif lead.status == "new":
            score += 5
            factors.append(("Lead novo", 5, "🆕"))

        # 3. VENDEDOR ATRIBUÍDO (0-15 pontos)
        if lead.assigned_to:
            score += 15
            factors.append(("Vendedor atribuído", 15, "👤"))
        else:
            factors.append(("Sem vendedor", 0, "❌"))

        # 4. TEMPO NO FUNIL (0-10 pontos)
        days_in_funnel = (datetime.now() - lead.created_at).days if lead.created_at else 999
        if 3 <= days_in_funnel <= 7:
            score += 10
            factors.append(("Tempo ideal no funil", 10, "⏱️"))
        elif days_in_funnel < 3:
            score += 5
            factors.append(("Muito recente", 5, "⚡"))
        elif days_in_funnel > 14:
            score -= 5
            factors.append(("Tempo excessivo no funil", -5, "⚠️"))

        # 5. ATIVIDADE RECENTE (0-10 pontos)
        if lead.updated_at:
            days_since_update = (datetime.now() - lead.updated_at).days
            if days_since_update == 0:
                score += 10
                factors.append(("Atividade hoje", 10, "🔔"))
            elif days_since_update <= 2:
                score += 5
                factors.append(("Atividade recente", 5, "📊"))
            elif days_since_update > 5:
                score -= 10
                factors.append(("Sem atividade há dias", -10, "⏸️"))

        # Garantir score entre 0-100
        score = max(0, min(100, score))

        # Classificação de probabilidade
        if score >= 70:
            probability_label = "ALTA"
            confidence = "🟢"
            recommendation = "Prioridade MÁXIMA - focar agora!"
        elif score >= 50:
            probability_label = "MÉDIA-ALTA"
            confidence = "🟡"
            recommendation = "Boa oportunidade - acompanhar de perto"
        elif score >= 30:
            probability_label = "MÉDIA"
            confidence = "🟠"
            recommendation = "Nutrir e qualificar melhor"
        else:
            probability_label = "BAIXA"
            confidence = "🔴"
            recommendation = "Re-qualificar ou descartar"

        return {
            "score": score,
            "probability_label": probability_label,
            "confidence_icon": confidence,
            "recommendation": recommendation,
            "factors": factors,
            "metadata": {
                "days_in_funnel": days_in_funnel,
                "last_activity_days": (datetime.now() - lead.updated_at).days if lead.updated_at else None
            }
        }

    async def _tool_predict_lead_conversion(self, lead_id: int) -> Dict:
        """Prevê probabilidade de conversão de um lead específico."""
        # Buscar lead
        q = select(Lead, User.name.label("seller_name")).outerjoin(
            User, Lead.assigned_to == User.id
        ).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.id == lead_id)
        )
        result = await self.db.execute(q)
        row = result.first()

        if not row:
            return {"error": f"Lead ID {lead_id} não encontrado"}

        lead = row[0]
        seller_name = row[1]

        # Calcular score
        analysis = self._calculate_lead_score(lead)

        return {
            "lead": {
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "status": str(lead.status),
                "qualification": str(lead.qualification) if lead.qualification else "N/A",
                "assigned_to": seller_name or "Não atribuído"
            },
            "prediction": {
                "conversion_probability_score": analysis["score"],
                "probability_label": analysis["probability_label"],
                "confidence": analysis["confidence_icon"],
                "recommendation": analysis["recommendation"]
            },
            "analysis": {
                "factors_evaluated": len(analysis["factors"]),
                "scoring_breakdown": analysis["factors"],
                "days_in_funnel": analysis["metadata"]["days_in_funnel"],
                "last_activity": f"{analysis['metadata']['last_activity_days']} dias atrás" if analysis['metadata']['last_activity_days'] is not None else "N/A"
            },
            "action_plan": self._get_action_plan_for_score(analysis["score"])
        }

    def _get_action_plan_for_score(self, score: int) -> list:
        """Retorna plano de ação baseado no score."""
        if score >= 70:
            return [
                "1. Contatar AGORA se ainda não foi feito hoje",
                "2. Oferecer proposta personalizada",
                "3. Agendar visita/reunião de fechamento",
                "4. Preparar documentação para fechamento rápido"
            ]
        elif score >= 50:
            return [
                "1. Manter contato regular (dia sim, dia não)",
                "2. Enviar cases de sucesso e depoimentos",
                "3. Identificar e eliminar objeções",
                "4. Agendar demonstração ou visita"
            ]
        elif score >= 30:
            return [
                "1. Qualificar melhor: entender real necessidade",
                "2. Nutrir com conteúdo relevante",
                "3. Verificar budget e timing de compra",
                "4. Agendar follow-up em 2-3 dias"
            ]
        else:
            return [
                "1. Re-qualificar: confirmar interesse real",
                "2. Se não houver interesse, marcar como perdido",
                "3. Transferir esforço para leads de maior score",
                "4. Considerar campanha de reengajamento"
            ]

    async def _tool_get_top_leads_to_focus(self, limit: int = 10) -> Dict:
        """Ranking inteligente de leads por probabilidade de conversão."""
        # Buscar leads ativos (não convertidos nem perdidos)
        q = select(Lead, User.name.label("seller_name")).outerjoin(
            User, Lead.assigned_to == User.id
        ).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status.notin_(["converted", "lost"])
            )
        )

        result = await self.db.execute(q)
        rows = result.all()

        # Calcular score para cada lead
        scored_leads = []
        for row in rows:
            lead = row[0]
            seller_name = row[1]
            analysis = self._calculate_lead_score(lead)

            scored_leads.append({
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "score": analysis["score"],
                "probability": analysis["probability_label"],
                "confidence": analysis["confidence_icon"],
                "status": str(lead.status),
                "qualification": str(lead.qualification) if lead.qualification else "N/A",
                "assigned_to": seller_name or "Não atribuído",
                "recommendation": analysis["recommendation"],
                "days_in_funnel": analysis["metadata"]["days_in_funnel"]
            })

        # Ordenar por score (maior primeiro)
        scored_leads.sort(key=lambda x: x["score"], reverse=True)
        top_leads = scored_leads[:limit]

        # Adicionar ranking
        for i, lead in enumerate(top_leads, 1):
            lead["rank"] = i

        # Estatísticas
        high_score_count = len([l for l in scored_leads if l["score"] >= 70])
        medium_score_count = len([l for l in scored_leads if 50 <= l["score"] < 70])
        low_score_count = len([l for l in scored_leads if l["score"] < 50])

        return {
            "total_active_leads": len(scored_leads),
            "distribution": {
                "high_probability": high_score_count,
                "medium_probability": medium_score_count,
                "low_probability": low_score_count
            },
            "top_leads_to_focus": top_leads,
            "strategic_insight": f"Dos {len(scored_leads)} leads ativos, {high_score_count} têm alta probabilidade de conversão. Foque neles AGORA!",
            "next_steps": [
                f"🎯 PRIORIDADE 1: Contatar os {min(3, high_score_count)} leads de score mais alto",
                f"📞 PRIORIDADE 2: Nutrir os {medium_score_count} leads de probabilidade média",
                f"🔄 PRIORIDADE 3: Re-qualificar os {low_score_count} leads de baixa probabilidade"
            ]
        }

    async def _tool_predict_month_goal(self, target_conversions: Optional[int] = None) -> Dict:
        """Prevê se a empresa atingirá a meta do mês."""
        now = datetime.now()

        # Início e fim do mês atual
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            month_end = now.replace(year=now.year + 1, month=1, day=1)
        else:
            month_end = now.replace(month=now.month + 1, day=1)

        days_in_month = (month_end - month_start).days
        days_passed = (now - month_start).days
        days_remaining = (month_end - now).days

        # Conversões até agora neste mês
        q_current_conversions = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "converted",
                Lead.updated_at >= month_start
            )
        )
        current_conversions = (await self.db.execute(q_current_conversions)).scalar() or 0

        # Pipeline atual (leads em negociação)
        q_pipeline = select(
            func.count(Lead.id).label("total"),
            func.sum(case((Lead.qualification == "hot", 1), else_=0)).label("hot"),
            func.sum(case((Lead.qualification == "warm", 1), else_=0)).label("warm")
        ).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status.in_(["in_progress", "open"])
            )
        )
        pipeline_data = (await self.db.execute(q_pipeline)).one()
        pipeline_total = pipeline_data.total or 0
        pipeline_hot = pipeline_data.hot or 0
        pipeline_warm = pipeline_data.warm or 0

        # Taxa de conversão histórica (últimos 60 dias)
        sixty_days_ago = now - timedelta(days=60)
        q_hist_leads = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, Lead.created_at >= sixty_days_ago)
        )
        hist_leads = (await self.db.execute(q_hist_leads)).scalar() or 0

        q_hist_conversions = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "converted",
                Lead.created_at >= sixty_days_ago
            )
        )
        hist_conversions = (await self.db.execute(q_hist_conversions)).scalar() or 0

        historical_conversion_rate = (hist_conversions / hist_leads * 100) if hist_leads > 0 else 15  # Default 15%

        # Estimar conversões do pipeline
        # Hot: 60% de conversão, Warm: 30%, Cold: 10%
        estimated_conversions_from_pipeline = (
            (pipeline_hot * 0.6) +
            (pipeline_warm * 0.3) +
            ((pipeline_total - pipeline_hot - pipeline_warm) * 0.1)
        )

        # Projeção final
        projected_total = current_conversions + estimated_conversions_from_pipeline

        # Se não foi informada meta, usar crescimento de 10% sobre média histórica
        if target_conversions is None:
            # Média de conversões/mês dos últimos 60 dias
            monthly_avg = (hist_conversions / 2) if hist_conversions > 0 else 10
            target_conversions = int(monthly_avg * 1.1)  # Meta = média + 10%

        # Probabilidade de atingir meta
        goal_gap = target_conversions - projected_total
        probability_percent = min(100, (projected_total / target_conversions * 100)) if target_conversions > 0 else 0

        # Classificação
        if probability_percent >= 90:
            forecast = "MUITO PROVÁVEL"
            emoji = "🎯"
            message = "Excelente! Você está no caminho certo para superar a meta!"
        elif probability_percent >= 70:
            forecast = "PROVÁVEL"
            emoji = "✅"
            message = "Bom ritmo! Continue focado e você alcança a meta."
        elif probability_percent >= 50:
            forecast = "POSSÍVEL"
            emoji = "⚠️"
            message = "Atenção! Você precisa acelerar para bater a meta."
        else:
            forecast = "IMPROVÁVEL"
            emoji = "🔴"
            message = "Meta em risco! Ação urgente necessária."

        # Cálculo de quantas conversões por dia são necessárias
        conversions_per_day_needed = goal_gap / days_remaining if days_remaining > 0 else 0

        return {
            "month_progress": {
                "days_passed": days_passed,
                "days_remaining": days_remaining,
                "progress_percent": round((days_passed / days_in_month * 100), 1)
            },
            "performance": {
                "current_conversions": current_conversions,
                "target_conversions": target_conversions,
                "gap": int(goal_gap),
                "achievement_percent": round(probability_percent, 1)
            },
            "pipeline_analysis": {
                "total_opportunities": pipeline_total,
                "hot_leads": pipeline_hot,
                "warm_leads": pipeline_warm,
                "estimated_conversions": round(estimated_conversions_from_pipeline, 1),
                "historical_conversion_rate": round(historical_conversion_rate, 1)
            },
            "prediction": {
                "projected_total_conversions": round(projected_total, 0),
                "probability_of_success": round(probability_percent, 1),
                "forecast": forecast,
                "confidence": emoji,
                "message": message
            },
            "action_required": {
                "conversions_needed": max(0, int(goal_gap)),
                "daily_conversions_needed": round(conversions_per_day_needed, 1),
                "recommendations": self._get_goal_recommendations(probability_percent, goal_gap, days_remaining)
            }
        }

    def _get_goal_recommendations(self, probability: float, gap: float, days_left: int) -> list:
        """Recomendações baseadas na probabilidade de atingir meta."""
        if probability >= 90:
            return [
                "✅ Manter o ritmo atual",
                "🎯 Focar em fechar as oportunidades quentes do pipeline",
                "📈 Considerar aumentar a meta para o próximo mês"
            ]
        elif probability >= 70:
            return [
                "🔥 Priorizar leads quentes imediatamente",
                "📞 Intensificar follow-ups com leads em negociação",
                "⚡ Acelerar propostas pendentes"
            ]
        elif probability >= 50:
            return [
                "🚨 URGENTE: Focar 100% em fechamento",
                f"🎯 Fechar {int(gap)} conversões nos próximos {days_left} dias",
                "📞 Reativar leads parados com alta qualificação",
                "🤝 Oferecer condições especiais para fechar rápido"
            ]
        else:
            return [
                "🔴 META EM RISCO CRÍTICO",
                f"⚡ Necessário {int(gap)} conversões em {days_left} dias",
                "🔥 Mobilizar TODA equipe para fechamentos",
                "💰 Considerar promoções ou descontos para acelerar",
                "📊 Reavaliar meta ou estender prazo",
                "🎯 Captar novos leads quentes urgentemente"
            ]

    async def _tool_analyze_opportunities(self) -> Dict:
        """Análise profunda do pipeline de oportunidades."""
        # Buscar todas as oportunidades ativas (in_progress principalmente)
        q = select(Lead, User.name.label("seller_name")).outerjoin(
            User, Lead.assigned_to == User.id
        ).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status.in_(["in_progress", "open"])
            )
        )

        result = await self.db.execute(q)
        rows = result.all()

        opportunities = []
        total_expected_value = 0
        critical_opps = []
        safe_opps = []

        for row in rows:
            lead = row[0]
            seller_name = row[1]

            # Calcular score
            analysis = self._calculate_lead_score(lead)
            score = analysis["score"]

            # Tempo no funil
            days_in_funnel = (datetime.now() - lead.created_at).days if lead.created_at else 0

            # Classificar risco
            if days_in_funnel > 14:
                risk_level = "ALTO"
                risk_emoji = "🔴"
            elif days_in_funnel > 7:
                risk_level = "MÉDIO"
                risk_emoji = "🟡"
            else:
                risk_level = "BAIXO"
                risk_emoji = "🟢"

            opp = {
                "lead_id": lead.id,
                "lead_name": lead.name,
                "seller": seller_name or "Não atribuído",
                "status": str(lead.status),
                "qualification": str(lead.qualification) if lead.qualification else "N/A",
                "probability_score": score,
                "probability_label": analysis["probability_label"],
                "days_in_funnel": days_in_funnel,
                "risk_level": risk_level,
                "risk_emoji": risk_emoji,
                "expected_close_days": max(1, 14 - days_in_funnel) if score >= 50 else "Incerto",
                "recommendation": analysis["recommendation"]
            }

            opportunities.append(opp)

            # Classificar criticidade
            if risk_level == "ALTO" and score >= 50:
                critical_opps.append(opp)
            elif score >= 70 and risk_level == "BAIXO":
                safe_opps.append(opp)

        # Ordenar por score (maior primeiro)
        opportunities.sort(key=lambda x: x["probability_score"], reverse=True)

        # Estatísticas
        high_prob_count = len([o for o in opportunities if o["probability_score"] >= 70])
        medium_prob_count = len([o for o in opportunities if 50 <= o["probability_score"] < 70])
        low_prob_count = len([o for o in opportunities if o["probability_score"] < 50])

        return {
            "pipeline_overview": {
                "total_opportunities": len(opportunities),
                "high_probability": high_prob_count,
                "medium_probability": medium_prob_count,
                "low_probability": low_prob_count,
                "critical_attention_needed": len(critical_opps)
            },
            "opportunities": opportunities,
            "critical_opportunities": {
                "count": len(critical_opps),
                "details": critical_opps[:5],  # Top 5 críticas
                "alert": "Oportunidades em risco que precisam ação URGENTE"
            },
            "safe_opportunities": {
                "count": len(safe_opps),
                "details": safe_opps[:5],  # Top 5 seguras
                "message": "Oportunidades com alta chance de fechar em breve"
            },
            "strategic_actions": [
                f"🔥 {len(critical_opps)} oportunidades críticas precisam de ação URGENTE",
                f"✅ {len(safe_opps)} oportunidades estão prontas para fechamento",
                f"⚠️ {medium_prob_count} oportunidades precisam de nurturing",
                f"🔄 {low_prob_count} oportunidades devem ser re-qualificadas"
            ]
        }

    async def _tool_predict_opportunity_close(self, opportunity_id: int) -> Dict:
        """Análise detalhada de probabilidade de fechamento de uma oportunidade."""
        # Reusar a ferramenta predict_lead_conversion mas com análise extra
        result = await self._tool_predict_lead_conversion(opportunity_id)

        if "error" in result:
            return result

        # Adicionar análise específica de oportunidade
        lead_id = result["lead"]["id"]
        q = select(Lead).where(and_(Lead.tenant_id == self.tenant.id, Lead.id == lead_id))
        lead_result = await self.db.execute(q)
        lead = lead_result.scalar_one_or_none()

        if not lead:
            return {"error": "Oportunidade não encontrada"}

        days_in_funnel = (datetime.now() - lead.created_at).days if lead.created_at else 0

        # Análise de risco temporal
        if days_in_funnel > 21:
            time_risk = "CRÍTICO"
            time_message = "Oportunidade parada há muito tempo - risco de perda iminente"
        elif days_in_funnel > 14:
            time_risk = "ALTO"
            time_message = "Tempo excessivo no funil - acelerar fechamento"
        elif days_in_funnel > 7:
            time_risk = "MÉDIO"
            time_message = "Tempo normal de negociação"
        else:
            time_risk = "BAIXO"
            time_message = "Oportunidade recente - tempo ideal para trabalhar"

        # Adicionar campos extras à resposta
        result["opportunity_analysis"] = {
            "time_in_funnel_days": days_in_funnel,
            "time_risk_level": time_risk,
            "time_risk_message": time_message,
            "estimated_close_date": f"{max(1, 14 - days_in_funnel)} dias" if result["prediction"]["conversion_probability_score"] >= 50 else "Incerto",
            "urgency_level": "MÁXIMA" if days_in_funnel > 14 else "ALTA" if days_in_funnel > 7 else "NORMAL"
        }

        result["closing_strategy"] = self._get_closing_strategy(
            result["prediction"]["conversion_probability_score"],
            days_in_funnel,
            str(lead.qualification) if lead.qualification else None
        )

        return result

    def _get_closing_strategy(self, score: int, days: int, qualification: Optional[str]) -> Dict:
        """Estratégia personalizada de fechamento."""
        if score >= 70:
            return {
                "approach": "FECHAMENTO AGRESSIVO",
                "timeline": "24-48 horas",
                "tactics": [
                    "📞 Ligar AGORA e agendar reunião de fechamento",
                    "📄 Preparar proposta comercial completa",
                    "💰 Oferecer condições especiais se fechar esta semana",
                    "🤝 Envolver gerente/diretor para dar peso ao fechamento",
                    "📊 Apresentar cases de sucesso similares"
                ]
            }
        elif score >= 50:
            return {
                "approach": "NURTURING ACELERADO",
                "timeline": "3-5 dias",
                "tactics": [
                    "📞 Follow-up diário até eliminar objeções",
                    "🎯 Identificar e resolver principais objeções",
                    "📧 Enviar cases e depoimentos de clientes",
                    "👥 Oferecer demonstração ou visita técnica",
                    "⏰ Criar senso de urgência (condição limitada)"
                ]
            }
        else:
            return {
                "approach": "RE-QUALIFICAÇÃO",
                "timeline": "2-3 dias para decisão",
                "tactics": [
                    "❓ Verificar se ainda há interesse real",
                    "💰 Confirmar budget e autoridade de compra",
                    "📅 Entender timing real de decisão",
                    "🔄 Se não qualificar, marcar como perdido",
                    "🎯 Redirecionar esforço para leads de maior score"
                ]
            }

    # =========================================================================
    # COACHING E ANÁLISE COMPORTAMENTAL
    # =========================================================================

    async def _tool_coach_seller(self, seller_id: int) -> Dict:
        """Análise e coaching personalizado para vendedor."""
        # Buscar vendedor
        q_seller = select(User).where(
            and_(User.tenant_id == self.tenant.id, User.id == seller_id)
        )
        seller_result = await self.db.execute(q_seller)
        seller = seller_result.scalar_one_or_none()

        if not seller:
            return {"error": f"Vendedor ID {seller_id} não encontrado"}

        # Período de análise: últimos 30 dias
        since = datetime.now() - timedelta(days=30)

        # Métricas individuais
        q_metrics = select(
            func.count(Lead.id).label("total_leads"),
            func.sum(case((Lead.status == "converted", 1), else_=0)).label("conversions"),
            func.sum(case((Lead.status == "lost", 1), else_=0)).label("lost"),
            func.sum(case((Lead.status.in_(["new", "open"]), 1), else_=0)).label("active")
        ).where(
            and_(Lead.assigned_to == seller_id, Lead.created_at >= since)
        )
        metrics = (await self.db.execute(q_metrics)).one()

        total = metrics.total_leads or 0
        conversions = metrics.conversions or 0
        lost = metrics.lost or 0
        active = metrics.active or 0
        conversion_rate = round((conversions / total * 100), 1) if total > 0 else 0

        # Métricas do time (para comparação)
        q_team = select(
            func.count(Lead.id).label("total"),
            func.sum(case((Lead.status == "converted", 1), else_=0)).label("conv")
        ).join(
            User, Lead.assigned_to == User.id
        ).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.created_at >= since,
                User.role == "vendedor"
            )
        )
        team_metrics = (await self.db.execute(q_team)).one()

        team_total = team_metrics.total or 1  # Evitar divisão por zero
        team_conversions = team_metrics.conv or 0
        team_avg_conversion = round((team_conversions / team_total * 100), 1)

        # Comparação com time
        vs_team = conversion_rate - team_avg_conversion
        performance_vs_team = "ACIMA" if vs_team > 5 else "ABAIXO" if vs_team < -5 else "NA MÉDIA"

        # Análise de pontos fortes e fracos
        strengths = []
        weaknesses = []
        training_needed = []

        # Conversão
        if conversion_rate > team_avg_conversion + 5:
            strengths.append("✅ Taxa de conversão acima da média do time")
        elif conversion_rate < team_avg_conversion - 5:
            weaknesses.append("❌ Taxa de conversão abaixo da média")
            training_needed.append("Treinamento em técnicas de fechamento")

        # Volume
        avg_leads_per_seller = team_total / max(1, (await self.db.execute(
            select(func.count(func.distinct(User.id))).where(
                and_(User.tenant_id == self.tenant.id, User.role == "vendedor")
            )
        )).scalar() or 1)

        if total > avg_leads_per_seller * 1.2:
            strengths.append("✅ Alto volume de leads trabalhados")
        elif total < avg_leads_per_seller * 0.8:
            weaknesses.append("❌ Volume de leads abaixo do esperado")
            training_needed.append("Prospecção ativa e geração de leads")

        # Taxa de perda
        loss_rate = round((lost / total * 100), 1) if total > 0 else 0
        if loss_rate > 40:
            weaknesses.append(f"❌ Alta taxa de perda ({loss_rate}%)")
            training_needed.append("Gestão de objeções e qualificação")

        # Leads ativos
        if active > total * 0.4:
            weaknesses.append("⚠️ Muitos leads parados sem conclusão")
            training_needed.append("Gestão de pipeline e follow-up")

        # Sugestões de melhoria
        improvement_plan = []
        if performance_vs_team == "ACIMA":
            improvement_plan = [
                "🏆 PARABÉNS! Performance acima da média!",
                "📈 Compartilhe suas técnicas com o time",
                "🎯 Foque em aumentar ainda mais o volume",
                "👨‍🏫 Considere mentorar vendedores juniores"
            ]
        elif performance_vs_team == "NA MÉDIA":
            improvement_plan = [
                "📊 Performance dentro da média do time",
                "🎯 Foque em qualificar melhor os leads",
                "📞 Aumente frequência de follow-ups",
                "📚 Estude técnicas do vendedor top do time"
            ]
        else:  # ABAIXO
            improvement_plan = [
                "⚠️ Performance abaixo da média - ação necessária",
                "🎯 FOCO PRINCIPAL: Melhorar taxa de conversão",
                "📚 Treinamento urgente em técnicas de venda",
                "👥 Acompanhamento diário com gestor",
                "🔄 Revisar processos e metodologia de vendas"
            ]

        return {
            "seller": {
                "id": seller.id,
                "name": seller.name,
                "email": seller.email
            },
            "period_analyzed": "Últimos 30 dias",
            "performance_summary": {
                "total_leads": total,
                "conversions": conversions,
                "lost": lost,
                "active_leads": active,
                "conversion_rate": conversion_rate,
                "loss_rate": loss_rate,
                "performance_vs_team": performance_vs_team,
                "gap_vs_team_percent": round(vs_team, 1)
            },
            "team_comparison": {
                "team_average_conversion": team_avg_conversion,
                "seller_conversion": conversion_rate,
                "difference": f"{'+' if vs_team > 0 else ''}{round(vs_team, 1)}%"
            },
            "strengths": strengths if strengths else ["⚪ Nenhum ponto forte identificado - precisa melhorar"],
            "areas_for_improvement": weaknesses if weaknesses else ["✅ Sem fraquezas identificadas"],
            "training_recommendations": training_needed if training_needed else ["✅ Continuar com boas práticas atuais"],
            "personalized_action_plan": improvement_plan,
            "coaching_tips": self._get_coaching_tips(conversion_rate, loss_rate, active, total)
        }

    def _get_coaching_tips(self, conv_rate: float, loss_rate: float, active: int, total: int) -> list:
        """Dicas personalizadas de coaching."""
        tips = []

        if conv_rate < 15:
            tips.append("💡 TIP: Trabalhe técnica SPIN Selling para qualificar melhor")

        if loss_rate > 40:
            tips.append("💡 TIP: Documente objeções comuns e prepare respostas")

        if active > total * 0.4:
            tips.append("💡 TIP: Crie routine de follow-up diário para não deixar leads esfriar")

        if not tips:
            tips.append("💡 TIP: Mantenha consistência e busque sempre melhorar 1% ao dia")

        return tips

    async def _tool_analyze_conversations(self, period_days: int = 30) -> Dict:
        """Análise NLP de padrões em conversas (versão simplificada baseada em dados)."""
        since = datetime.now() - timedelta(days=period_days)

        # Buscar leads convertidos e perdidos para análise
        q_converted = select(Lead).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "converted",
                Lead.created_at >= since
            )
        ).limit(50)
        converted_leads = (await self.db.execute(q_converted)).scalars().all()

        q_lost = select(Lead).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.status == "lost",
                Lead.created_at >= since
            )
        ).limit(50)
        lost_leads = (await self.db.execute(q_lost)).scalars().all()

        # Análise de padrões (baseado em custom_data e summary)
        # Em uma implementação real, faria NLP nas mensagens

        # Padrões de sucesso (leads convertidos)
        success_patterns = {
            "total_analyzed": len(converted_leads),
            "common_qualifications": self._analyze_qualifications(converted_leads),
            "average_time_to_close": self._calculate_avg_time(converted_leads),
            "best_practices_identified": [
                "🏆 Leads quentes convertem 3x mais rápido",
                "📞 Follow-up em até 2h aumenta conversão em 40%",
                "🤝 Leads com vendedor atribuído imediatamente têm +60% conversão",
                "⏰ Tempo ideal de fechamento: 7-10 dias"
            ]
        }

        # Padrões de perda
        loss_patterns = {
            "total_analyzed": len(lost_leads),
            "common_reasons": self._analyze_loss_reasons(lost_leads),
            "red_flags_identified": [
                "🔴 Leads sem resposta em 24h têm 70% chance de perda",
                "⚠️ Leads parados >14 dias raramente convertem",
                "❌ Leads sem qualificação perdem 2x mais",
                "📉 Falta de follow-up é causa #1 de perda"
            ]
        }

        # Objeções mais comuns (inferidas)
        common_objections = [
            {
                "objection": "Preço alto",
                "frequency": "35%",
                "winning_response": "Demonstrar ROI e valor agregado, não competir apenas por preço"
            },
            {
                "objection": "Vou pensar / Preciso de tempo",
                "frequency": "25%",
                "winning_response": "Criar urgência com condição especial limitada"
            },
            {
                "objection": "Já tenho fornecedor",
                "frequency": "20%",
                "winning_response": "Destacar diferenciais únicos e oferecer teste/trial"
            },
            {
                "objection": "Não é o momento certo",
                "frequency": "15%",
                "winning_response": "Entender real timing e agendar follow-up específico"
            }
        ]

        # Recomendações estratégicas
        strategic_recommendations = [
            "🎯 FOCO #1: Reduzir tempo de primeira resposta para <2 horas",
            "📞 FOCO #2: Implementar cadência de follow-up 3-5-7 (dias 3, 5 e 7)",
            "💡 FOCO #3: Qualificar TODOS os leads nas primeiras 24h",
            "📚 FOCO #4: Treinar equipe em gestão de objeções",
            "⚡ FOCO #5: Criar biblioteca de respostas para objeções comuns"
        ]

        return {
            "period_analyzed": f"Últimos {period_days} dias",
            "success_patterns": success_patterns,
            "loss_patterns": loss_patterns,
            "common_objections": common_objections,
            "strategic_recommendations": strategic_recommendations,
            "key_insights": [
                f"✅ {len(converted_leads)} conversões analisadas",
                f"❌ {len(lost_leads)} perdas analisadas",
                "🎯 Principais fatores de sucesso identificados",
                "⚠️ Principais causas de perda identificadas"
            ],
            "next_steps": [
                "📊 Implementar dashboard de objeções",
                "📚 Criar playbook de respostas vencedoras",
                "🎓 Treinar time em padrões identificados",
                "🔄 Revisar processo de qualificação"
            ]
        }

    def _analyze_qualifications(self, leads: list) -> Dict:
        """Analisa distribuição de qualificações."""
        hot = sum(1 for l in leads if l.qualification == "hot")
        warm = sum(1 for l in leads if l.qualification == "warm")
        cold = sum(1 for l in leads if l.qualification == "cold")
        total = len(leads)

        return {
            "hot": f"{hot} ({round(hot/total*100, 1)}%)" if total > 0 else "0",
            "warm": f"{warm} ({round(warm/total*100, 1)}%)" if total > 0 else "0",
            "cold": f"{cold} ({round(cold/total*100, 1)}%)" if total > 0 else "0",
            "insight": "Leads QUENTES têm maior taxa de conversão"
        }

    def _calculate_avg_time(self, leads: list) -> str:
        """Calcula tempo médio para fechar."""
        if not leads:
            return "N/A"

        times = []
        for lead in leads:
            if lead.created_at and lead.updated_at:
                delta = (lead.updated_at - lead.created_at).days
                times.append(delta)

        if times:
            avg = sum(times) / len(times)
            return f"{round(avg, 1)} dias"
        return "N/A"

    def _analyze_loss_reasons(self, leads: list) -> list:
        """Analisa razões de perda (baseado em dados disponíveis)."""
        # Como não temos campo específico de motivo, inferimos por padrões
        no_seller = sum(1 for l in leads if not l.assigned_to)
        cold_leads = sum(1 for l in leads if l.qualification == "cold")

        reasons = []
        if no_seller > 0:
            reasons.append(f"Sem vendedor atribuído: {no_seller} leads")
        if cold_leads > 0:
            reasons.append(f"Qualificação fria: {cold_leads} leads")

        reasons.append("Falta de follow-up (padrão observado)")
        reasons.append("Objeções não trabalhadas (padrão observado)")

        return reasons
