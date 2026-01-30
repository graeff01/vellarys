import logging
from fastapi import HTTPException
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from src.domain.entities import Tenant, User, Lead, LeadEvent, Opportunity
from src.infrastructure.services.email_service import send_welcome_email 
import resend
import json
from src.infrastructure.llm import LLMFactory
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class MorningBriefingService:
    """
    Serviço responsável por gerar e enviar o Morning Briefing (08:00).
    Foca em: Metas, Alertas de Leads Negligenciados e Ações Táticas.
    """

    def __init__(self, db: AsyncSession, tenant: Tenant):
        self.db = db
        self.tenant = tenant

    async def generate_and_send(self, target_email: str = None):
        """Gera os dados e envia o email."""
        
        # Se não informou email, tenta descobrir automaticamente
        if not target_email:
            # 1. Tenta settings do tenant
            target_email = self.tenant.settings.get('morning_briefing_recipient')
            
            # 2. Se não tem, busca o primeiro gestor ou admin
            if not target_email:
                q_user = select(User).where(
                    and_(User.tenant_id == self.tenant.id, User.role.in_(['gestor', 'admin']))
                ).limit(1)
                user_res = await self.db.execute(q_user)
                manager = user_res.scalar_one_or_none()
                if manager:
                    target_email = manager.email
                else:
                    target_email = "douglas@velocebm.com" # Último Fallback

        logger.info(f"Gerando Morning Briefing para {self.tenant.name} -> Destinatário: {target_email}")

        # 1. Coletar Dados Ricos
        stats = await self._get_daily_stats()
        alerts = await self._get_neglected_leads()
        
        # 2. Gerar Análise Estratégica via IA
        ai_analysis = await self._get_ai_analysis(stats, alerts)
        
        # 3. Gerar HTML "Edificado"
        html_content = self._build_email_html(stats, alerts, ai_analysis)

        # 4. Enviar
        if not settings.resend_api_key:
            logger.warning("Resend API Key não configurada.")
            return

        try:
           # Busca remitente personalizado ou usa padrão
           sender_email = self.tenant.settings.get('ai_sender_email', settings.email_from)
           
           params = {
                "from": f"Vellarys Intelligence <{sender_email}>",
                "to": [target_email],
                "subject": f"Briefing Matinal - {self.tenant.name}",
                "html": html_content,
            }
           resend.Emails.send(params)
           logger.info(f"Morning Briefing enviado para {target_email}")
           return {"success": True}
        except Exception as e:
            error_msg = str(e)
            if "domain is not verified" in error_msg:
                logger.error(f"Erro de domínio não verificado no Resend: {error_msg}")
                raise HTTPException(
                    status_code=400, 
                    detail="Domínio não verificado no Resend. Você precisa verificar seu domínio em resend.com/domains ou usar o remetente padrão 'onboarding@resend.dev' para testes."
                )
            
            logger.error(f"Erro ao enviar Morning Briefing: {e}")
            raise

    async def _get_daily_stats(self):
        """Calcula estatísticas de ontem e acumulado do mês com comparativos."""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)
        month_start = today.replace(day=1)

        # Leads Ontem
        q_leads_yest = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, func.date(Lead.created_at) == yesterday)
        )
        leads_yesterday = (await self.db.execute(q_leads_yest)).scalar() or 0

        # Leads Anteontem (para variação)
        q_leads_before = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, func.date(Lead.created_at) == day_before)
        )
        leads_day_before = (await self.db.execute(q_leads_before)).scalar() or 0
        
        variation = 0
        if leads_day_before > 0:
            variation = int(((leads_yesterday - leads_day_before) / leads_day_before) * 100)

        # Leads Qualificados Ontem (Warm/Hot)
        q_qual = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id, 
                func.date(Lead.created_at) == yesterday,
                Lead.qualification.in_(['warm', 'hot'])
            )
        )
        qualified_yesterday = (await self.db.execute(q_qual)).scalar() or 0

        # Novas Oportunidades criadas ontem
        q_opp = select(func.count(Opportunity.id)).where(
            and_(Opportunity.tenant_id == self.tenant.id, func.date(Opportunity.created_at) == yesterday)
        )
        new_opportunities = (await self.db.execute(q_opp)).scalar() or 0

        # Vendas Mês (Status 'converted')
        q_sales = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id, 
                Lead.status == 'converted',
                Lead.updated_at >= month_start
            )
        )
        sales_month = (await self.db.execute(q_sales)).scalar() or 0
        
        # Receita e Meta
        revenue_month = sales_month * 500000 # Mock ticket médio
        revenue_goal = 2000000 # Meta 2M
        
        return {
            "leads_yesterday": leads_yesterday,
            "leads_day_before": leads_day_before,
            "leads_variation_percent": variation,
            "qualified_yesterday": qualified_yesterday,
            "new_opportunities": new_opportunities,
            "sales_month_count": sales_month,
            "revenue_month": revenue_month,
            "revenue_goal": revenue_goal,
            "revenue_missing": max(0, revenue_goal - revenue_month),
            "progress_percent": min(100, int((revenue_month / revenue_goal) * 100))
        }

    async def _get_neglected_leads(self):
        """Busca leads QUENTES sem interação há mais de 24h."""
        limit_date = datetime.now() - timedelta(hours=24)
        
        q = select(Lead).where(
            and_(
                Lead.tenant_id == self.tenant.id,
                Lead.qualification == 'hot',
                Lead.status.in_(['new', 'open', 'in_progress']),
                Lead.updated_at < limit_date
            )
        ).limit(5)
        
        result = await self.db.execute(q)
        leads = result.scalars().all()
        
        return [
            {"name": l.name, "seller": l.assigned_seller_id or "Sem dono", "days": (datetime.now() - l.updated_at).days}
            for l in leads
        ]

    async def _get_ai_analysis(self, stats: dict, alerts: list):
        """Usa IA para gerar uma análise estratégica baseada nos dados."""
        
        # Prepara o contexto para a IA
        context = f"""
        EMPRESA: {self.tenant.name}
        NICHO: {self.tenant.settings.get('niche', 'Geral')}
        
        PERFORMANCE:
        - Leads ontem: {stats['leads_yesterday']} (Variação: {stats['leads_variation_percent']}% vs dia anterior)
        - Leads qualificados (Warm/Hot) ontem: {stats['qualified_yesterday']}
        - Novas Oportunidades: {stats['new_opportunities']}
        - Vendas mês: {stats['sales_month_count']}
        - Receita Atual: R$ {stats['revenue_month']:,.2f}
        - Meta Mensal: R$ {stats['revenue_goal']:,.2f}
        - Progresso da Meta: {stats['progress_percent']}%
        
        LEADS NEGLIGENCIADOS (SITUAÇÃO CRÍTICA):
        {json.dumps(alerts, ensure_ascii=False)}
        """
        
        prompt = f"""
        Você é um Diretor de Estratégia Comercial (Senior Business Consultant).
        Seu objetivo é analisar os dados do dia anterior e gerar um briefing executivo de alto impacto para o Gestor.
        
        REGRAS:
        - Tom: Corporativo, executivo, assertivo, extremamente direto.
        - Idioma: Português do Brasil.
        - FOCO EM OURO: Identifique o que os números dizem além da superfície.
        - Identifique GARGALOS e OPORTUNIDADES imediatas.

        CONTEÚDO:
        1. RESUMO EXECUTIVO: Analise a saúde do dia e o progresso estratégico.
        2. AÇÕES TÁTICAS PARA HOJE: 3 pontos concretos para a reunião matinal.

        DADOS:
        {context}
        """

        try:
            provider = LLMFactory.get_provider()
            response = await provider.chat_completion(
                messages=[{"role": "system", "content": prompt}],
                temperature=0.3,
                max_tokens=600
            )
            return response["content"].strip()
        except Exception as e:
            logger.error(f"Erro ao gerar análise de IA: {e}")
            return "Análise estratégica indisponível. Foco total em metas e recuperação de leads quentes."

    def _build_email_html(self, stats, alerts, ai_analysis):
        """Constrói o HTML Premium do Email."""
        
        # Formata a análise da IA (Markdown simples para HTML)
        ai_html = ai_analysis.replace('\n', '<br>')
        
        # Lista de Alertas HTML
        alerts_html = ""
        if alerts:
            for alert in alerts:
                # Tenta buscar nome do vendedor
                seller_info = alert['seller']
                alerts_html += f"""
                <div style="background: #fff5f5; border-left: 4px solid #ef4444; padding: 12px; margin-bottom: 10px; border-radius: 6px;">
                    <div style="font-weight: 700; color: #991b1b; display: flex; justify-content: space-between;">
                        <span>🚨 {alert['name']}</span>
                        <span style="font-size: 11px; background: #fee2e2; padding: 2px 6px; border-radius: 10px;">-{alert['days']} Dias</span>
                    </div>
                    <div style="font-size: 12px; color: #b91c1c; margin-top: 4px;">
                        Responsável: Vendedor {seller_info}
                    </div>
                </div>
                """
        else:
            alerts_html = """
            <div style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 15px; border-radius: 6px; color: #166534; font-size: 14px;">
                ✅ <strong>Operação Limpa:</strong> Nenhum lead quente negligenciado encontrado.
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }}
                .header {{ background: #1e293b; padding: 40px 30px; color: white; border-bottom: 4px solid #4f46e5; }}
                .title {{ font-size: 20px; font-weight: 800; margin: 0; text-transform: uppercase; letter-spacing: 1px; }}
                .subtitle {{ opacity: 0.7; margin-top: 5px; font-size: 12px; font-weight: 500; text-transform: uppercase; }}
                .content {{ padding: 30px; }}
                .section-title {{ font-size: 12px; font-weight: 800; color: #64748b; margin: 30px 0 15px 0; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }}
                .metric-grid {{ display: flex; gap: 15px; margin-bottom: 20px; }}
                .metric-card {{ background: #f1f5f9; border-radius: 12px; padding: 15px; flex: 1; text-align: left; }}
                .metric-value {{ font-size: 24px; font-weight: 800; color: #0f172a; margin: 5px 0; }}
                .metric-label {{ font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; }}
                .variation {{ font-size: 10px; font-weight: 700; }}
                .variation.up {{ color: #10b981; }}
                .variation.down {{ color: #ef4444; }}
                .ai-box {{ background: #fdfefe; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; font-size: 14px; line-height: 1.6; color: #334155; border-left: 5px solid #4f46e5; }}
                .footer {{ background: #f8fafc; padding: 25px; text-align: center; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
                .btn {{ display: block; background: #4f46e5; color: white !important; text-decoration: none; padding: 14px; border-radius: 8px; font-weight: 700; margin-top: 30px; text-align: center; font-size: 14px; box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2); }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="subtitle">{datetime.now().strftime('%d de %B, %Y')}</div>
                    <h1 class="title">Briefing Matinal - {self.tenant.name}</h1>
                </div>
                
                <div class="content">
                    <!-- INDICADORES CHAVE -->
                    <div class="section-title">📊 KPIs DO DIA ANTERIOR</div>
                    <div class="metric-grid">
                        <div class="metric-card">
                            <div class="metric-label">Novos Leads</div>
                            <div class="metric-value">{stats['leads_yesterday']}</div>
                            <div class="variation {'up' if stats['leads_variation_percent'] >= 0 else 'down'}">
                                {('+' if stats['leads_variation_percent'] >= 0 else '')}{stats['leads_variation_percent']}% vs anteontem
                            </div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Qualificados</div>
                            <div class="metric-value">{stats['qualified_yesterday']}</div>
                            <div style="font-size: 10px; color: #64748b;">Warm & Hot</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Oportunidades</div>
                            <div class="metric-value">{stats['new_opportunities']}</div>
                            <div style="font-size: 10px; color: #64748b;">Funil de Vendas</div>
                        </div>
                    </div>

                    <!-- BARRA DE PROGRESSO DA META -->
                    <div style="margin-top: 10px; margin-bottom: 30px;">
                        <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748b; font-weight: 700; margin-bottom: 5px; text-transform: uppercase;">
                            <span>Meta do Mês (Progresso: {stats['progress_percent']}%)</span>
                            <span>R$ {stats['revenue_goal']/1000000:.1f}M</span>
                        </div>
                        <div style="height: 10px; background: #e2e8f0; border-radius: 5px; overflow: hidden;">
                            <div style="width: {stats['progress_percent']}%; height: 100%; background: #4f46e5;"></div>
                        </div>
                        <div style="text-align: right; font-size: 10px; color: #94a3b8; margin-top: 5px;">
                            Atual: R$ {stats['revenue_month']/1000:.0f}k | Falta: R$ {stats['revenue_missing']/1000:.0f}k
                        </div>
                    </div>

                    <!-- ANALISE EXECUTIVA IA -->
                    <div class="section-title">🧠 ANÁLISE ESTRATÉGICA (Vellarys AI)</div>
                    <div class="ai-box">
                        {ai_html}
                    </div>

                    <!-- LEADS NEGLIGENCIADOS -->
                    <div class="section-title" style="color: #ef4444;">⚠️ LEADS EM RISCO (NEED ATTENTION)</div>
                    {alerts_html}
                    
                    <a href="{settings.frontend_url}/dashboard" class="btn">ABRIR DASHBOARD EXECUTIVO</a>
                </div>

                <div class="footer">
                    Este é um relatório gerado pela inteligência distribuída Vellarys.<br>
                    © {datetime.now().year} Vellarys Intelligence. Todos os direitos reservados.
                </div>
            </div>
        </body>
        </html>
        """
