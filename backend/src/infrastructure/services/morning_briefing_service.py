import logging
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from src.domain.entities import Tenant, User, Lead, LeadEvent
from src.infrastructure.services.email_service import send_welcome_email 
import resend
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

        # 1. Coletar Dados
        stats = await self._get_daily_stats()
        alerts = await self._get_neglected_leads()
        
        # 2. Gerar HTML "Edificado"
        html_content = self._build_email_html(stats, alerts)

        # 3. Enviar
        if not settings.resend_api_key:
            logger.warning("Resend API Key não configurada.")
            return

        try:
           # Busca remitente personalizado ou usa padrão
           sender_email = self.tenant.settings.get('ai_sender_email', settings.email_from)
           
           params = {
                "from": f"Vellarys Intelligence <{sender_email}>",
                "to": [target_email],
                "subject": f"🎯 Briefing Matinal: Sua Estratégia para Hoje ({datetime.now().strftime('%d/%m')})",
                "html": html_content,
            }
           resend.Emails.send(params)
           logger.info(f"Morning Briefing enviado para {target_email}")
           return {"success": True}
        except Exception as e:
            logger.error(f"Erro ao enviar Morning Briefing: {e}")
            raise

    async def _get_daily_stats(self):
        """Calcula estatísticas de ontem e acumulado do mês."""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        month_start = today.replace(day=1)

        # Leads Ontem
        q_leads_yest = select(func.count(Lead.id)).where(
            and_(Lead.tenant_id == self.tenant.id, func.date(Lead.created_at) == yesterday)
        )
        leads_yesterday = (await self.db.execute(q_leads_yest)).scalar() or 0

        # Vendas Mês (Simulado com Status 'converted')
        q_sales = select(func.count(Lead.id)).where(
            and_(
                Lead.tenant_id == self.tenant.id, 
                Lead.status == 'converted',
                Lead.updated_at >= month_start
            )
        )
        sales_month = (await self.db.execute(q_sales)).scalar() or 0
        
        # Receita Estimada (Exemplo: Ticket Médio R$ 500k)
        revenue_month = sales_month * 500000 
        revenue_goal = 2000000 # Mock Meta 2M
        
        return {
            "leads_yesterday": leads_yesterday,
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

    def _build_email_html(self, stats, alerts):
        """Constrói o HTML Premium do Email."""
        
        # Lista de Alertas HTML
        alerts_html = ""
        if alerts:
            for alert in alerts:
                alerts_html += f"""
                <div style="background: #fff5f5; border-left: 4px solid #ef4444; padding: 10px; margin-bottom: 8px; border-radius: 4px;">
                    <strong>🚨 {alert['name']}</strong> (Esfriando há {alert['days']} dias)<br>
                    <span style="font-size: 12px; color: #666;">Responsável: Vendedor {alert['seller']}</span>
                </div>
                """
        else:
            alerts_html = """
            <div style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 10px; border-radius: 4px;">
                ✅ Nenhum lead quente negligenciado! O time está afiado.
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Helvetica', 'Arial', sans-serif; background-color: #f4f4f5; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
                .header {{ background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%); padding: 40px 30px; text-align: center; color: white; }}
                .title {{ font-size: 24px; font-weight: 800; margin: 0; letter-spacing: -0.5px; }}
                .subtitle {{ opacity: 0.9; margin-top: 5px; font-size: 14px; font-weight: 400; }}
                .content {{ padding: 30px; }}
                .metric-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; text-align: center; margin-bottom: 20px; }}
                .metric-value {{ font-size: 32px; font-weight: 800; color: #1e293b; margin: 5px 0; }}
                .metric-label {{ font-size: 12px; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: 1px; }}
                .section-title {{ font-size: 16px; font-weight: 700; color: #1e293b; margin: 25px 0 15px 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 5px; }}
                .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
                .btn {{ display: inline-block; background: #4f46e5; color: white; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 600; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 class="title">📈 Estratégia do Dia</h1>
                    <p class="subtitle">Seu resumo executivo de inteligência comercial</p>
                </div>
                
                <div class="content">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <p style="font-size: 14px; color: #64748b;">Bom dia! Aqui está o panorama para você dominar o mercado hoje.</p>
                    </div>

                    <!-- METAS -->
                    <div class="section-title">📊 PERFORMANCE DO MÊS</div>
                    <div style="display: flex; gap: 15px;">
                        <div class="metric-card" style="flex: 1;">
                            <div class="metric-label">VENDAS</div>
                            <div class="metric-value">{stats['sales_month_count']}</div>
                        </div>
                        <div class="metric-card" style="flex: 1;">
                            <div class="metric-label">META ({stats['progress_percent']}%)</div>
                            <div class="metric-value" style="color: #4f46e5;">R$ {stats['revenue_month']/1000:.0f}k</div>
                        </div>
                    </div>
                    <p style="font-size: 13px; color: #64748b; text-align: center; margin-top: -10px;">
                        Faltam <strong>R$ {stats['revenue_missing']/1000:.0f}k</strong> para bater a meta mensal.
                    </p>

                    <!-- ALERTA DE LEADS -->
                    <div class="section-title">🚨 ATENÇÃO IMEDIATA (DEAL RESCUE)</div>
                    {alerts_html}
                    
                    <!-- AÇÃO SUGERIDA -->
                    <div class="section-title">💡 AÇÃO TÁTICA SUGERIDA</div>
                    <div style="background: #fffbeb; border: 1px solid #fcd34d; padding: 15px; border-radius: 6px;">
                        <p style="margin: 0; color: #92400e; font-style: italic;">
                            "Reuna a equipe por 15min e foque 100% em recuperar esses {len(alerts) if alerts else 0} leads parados. Se convertermos 1 deles hoje, avançamos 5% na meta."
                        </p>
                    </div>

                    <div style="text-align: center;">
                        <a href="{settings.frontend_url}/dashboard" class="btn">Acessar CRM Agora</a>
                    </div>
                </div>

                <div class="footer">
                    Vellarys AI Engine • Active Intelligence System<br>
                    Enviado automaticamente às 06:00
                </div>
            </div>
        </body>
        </html>
        """
