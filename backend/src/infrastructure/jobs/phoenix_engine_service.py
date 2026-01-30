"""
PHOENIX ENGINE - REATIVAÇÃO INTELIGENTE DE LEADS
================================================

Sistema avançado que monitora e reativa leads inativos (45+ dias)
usando IA para gerar mensagens personalizadas baseadas no histórico
do lead e no estoque atual de produtos/imóveis.

DIFERENÇAS DO FOLLOW-UP AUTOMÁTICO:
- Inatividade muito maior (45+ dias vs 24h)
- IA compara histórico do lead com estoque atual
- Análise de intenção de compra via IA
- Sistema de aprovação do gestor
- Upload em massa via CSV
- Comissão potencial estimada

CAMPOS DO LEAD UTILIZADOS:
- phoenix_status: Status no Phoenix (none, pending, reactivated, approved, rejected)
- phoenix_attempts: Número de tentativas de reativação
- last_phoenix_at: Data da última tentativa Phoenix
- phoenix_interest_score: Score de intenção de compra (0-100)
- phoenix_potential_commission: Comissão potencial estimada
- phoenix_ai_analysis: Análise completa da IA sobre o lead
- phoenix_original_seller_id: Vendedor original (para notificar após aprovação)

AUTOR: Vellarys AI
DATA: 2026-01-30
"""

import logging
import csv
import io
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database import async_session
from src.domain.entities import Lead, Message, Tenant, Seller, Product
from src.infrastructure.services.whatsapp_service import send_whatsapp_message
from src.infrastructure.services.openai_service import chat_completion

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURAÇÕES PADRÃO
# =============================================================================

DEFAULT_PHOENIX_CONFIG = {
    "enabled": False,
    "inactivity_days": 45,  # 45 dias sem interação
    "max_attempts": 2,  # Máximo de tentativas
    "interval_days": 15,  # Intervalo entre tentativas
    "require_manager_approval": True,  # Requer aprovação do gestor
    "min_interest_score_for_hot": 70,  # Score mínimo para marcar como "urgente"
    "respect_business_hours": True,
    "allowed_hours": {
        "start": "09:00",
        "end": "18:00",
    },
}


# =============================================================================
# SERVIÇO PRINCIPAL
# =============================================================================

class PhoenixEngineService:
    """
    Phoenix Engine - Sistema de Reativação Inteligente de Leads.

    Monitora leads inativos há 45+ dias e usa IA para gerar mensagens
    personalizadas baseadas no histórico do lead e no estoque atual.
    """

    def __init__(self):
        self.processed_count = 0
        self.sent_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.reactivated_count = 0

    # =========================================================================
    # MÉTODO PRINCIPAL - PROCESSA TODOS OS TENANTS
    # =========================================================================

    async def process_all_tenants(self):
        """
        Processa reativações Phoenix para todos os tenants ativos.

        CHAMADO PELO: Scheduler (diariamente)
        """
        print("=" * 60)
        print("🔥 PHOENIX ENGINE - INICIANDO BUSCA DE LEADS INATIVOS")
        print("=" * 60)

        self.processed_count = 0
        self.sent_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.reactivated_count = 0

        try:
            async with async_session() as session:
                # Busca todos os tenants ativos
                result = await session.execute(
                    select(Tenant).where(Tenant.active == True)
                )
                tenants = result.scalars().all()

                print(f"📊 Encontrados {len(tenants)} tenants ativos")

                for tenant in tenants:
                    await self._process_tenant(session, tenant)

                await session.commit()

        except Exception as e:
            print(f"❌ Erro crítico no Phoenix Engine: {e}")
            logger.error(f"❌ Erro crítico no Phoenix Engine: {e}", exc_info=True)

        # Log final
        print("=" * 60)
        print(f"🔥 PHOENIX ENGINE FINALIZADO")
        print(f"   Processados: {self.processed_count}")
        print(f"   Enviados: {self.sent_count}")
        print(f"   Reativados: {self.reactivated_count}")
        print(f"   Pulados: {self.skipped_count}")
        print(f"   Erros: {self.error_count}")
        print("=" * 60)

        return {
            "processed": self.processed_count,
            "sent": self.sent_count,
            "reactivated": self.reactivated_count,
            "skipped": self.skipped_count,
            "errors": self.error_count,
        }

    # =========================================================================
    # PROCESSA UM TENANT ESPECÍFICO
    # =========================================================================

    async def _process_tenant(self, session: AsyncSession, tenant: Tenant):
        """Processa reativações Phoenix de um tenant específico."""

        try:
            # Obtém configurações Phoenix do tenant
            config = self._get_phoenix_config(tenant)

            # Verifica se Phoenix está habilitado
            if not config.get("enabled", False):
                print(f"⏭️ Tenant {tenant.slug}: Phoenix Engine desabilitado")
                return

            print(f"🏢 Processando tenant: {tenant.name} ({tenant.slug})")

            # Verifica se está em horário permitido
            if not self._is_allowed_time(tenant, config):
                print(f"⏰ Tenant {tenant.slug}: Fora do horário permitido")
                return

            # Busca leads elegíveis para Phoenix
            leads = await self._get_inactive_leads(session, tenant, config)

            print(f"📋 Tenant {tenant.slug}: {len(leads)} leads inativos encontrados")

            for lead in leads:
                self.processed_count += 1
                await self._process_lead(session, tenant, lead, config)

        except Exception as e:
            print(f"❌ Erro ao processar tenant {tenant.slug}: {e}")
            logger.error(f"❌ Erro ao processar tenant {tenant.slug}: {e}", exc_info=True)
            self.error_count += 1

    # =========================================================================
    # BUSCA LEADS INATIVOS (45+ DIAS)
    # =========================================================================

    async def _get_inactive_leads(
        self,
        session: AsyncSession,
        tenant: Tenant,
        config: dict,
    ) -> List[Lead]:
        """
        Busca leads inativos há 45+ dias.

        CRITÉRIOS:
        1. Pertence ao tenant
        2. Tem telefone
        3. Última atividade há mais de X dias (padrão: 45)
        4. Status diferente de 'converted' (vendido)
        5. Não atingiu máximo de tentativas Phoenix
        6. Última tentativa Phoenix foi há mais de Y dias
        7. Phoenix status não é 'rejected' ou 'approved'
        """

        now = datetime.utcnow()
        inactivity_threshold = now - timedelta(days=config["inactivity_days"])
        interval_threshold = now - timedelta(days=config["interval_days"])

        # Query base
        query = (
            select(Lead)
            .options(
                selectinload(Lead.messages),
                selectinload(Lead.assigned_seller),
            )
            .where(
                and_(
                    # Pertence ao tenant
                    Lead.tenant_id == tenant.id,

                    # Tem telefone
                    Lead.phone.isnot(None),
                    Lead.phone != "",

                    # Última atividade há mais de X dias
                    or_(
                        Lead.last_activity_at.is_(None),
                        Lead.last_activity_at < inactivity_threshold,
                    ),

                    # Status diferente de 'converted' (vendido)
                    Lead.status != "converted",
                    Lead.status != "lost",

                    # Não atingiu máximo de tentativas
                    or_(
                        Lead.phoenix_attempts.is_(None),
                        Lead.phoenix_attempts < config["max_attempts"],
                    ),

                    # Última tentativa Phoenix foi há mais de Y dias
                    or_(
                        Lead.last_phoenix_at.is_(None),
                        Lead.last_phoenix_at < interval_threshold,
                    ),

                    # Phoenix status permite nova tentativa
                    or_(
                        Lead.phoenix_status.is_(None),
                        Lead.phoenix_status == "none",
                        Lead.phoenix_status == "pending",
                    ),

                    # Não está arquivado
                    Lead.archived_at.is_(None),
                )
            )
        )

        # Limita para não sobrecarregar
        query = query.limit(50)

        result = await session.execute(query)
        leads = result.scalars().all()

        return list(leads)

    # =========================================================================
    # PROCESSA UM LEAD
    # =========================================================================

    async def _process_lead(
        self,
        session: AsyncSession,
        tenant: Tenant,
        lead: Lead,
        config: dict,
    ):
        """Processa reativação Phoenix de um lead específico."""

        try:
            # Determina qual tentativa é essa
            attempt = (lead.phoenix_attempts or 0) + 1

            # Busca produtos/imóveis atuais do tenant
            products = await self._get_tenant_products(session, tenant)

            # Gera análise e mensagem com IA
            print(f"🤖 Phoenix analisando lead {lead.id} ({lead.name or 'Sem nome'})...")

            ai_result = await self._generate_phoenix_message(
                lead=lead,
                attempt=attempt,
                products=products,
                tenant=tenant,
            )

            if not ai_result or not ai_result.get("message"):
                print(f"⚠️ Lead {lead.id}: IA não gerou mensagem")
                self.skipped_count += 1
                return

            message = ai_result["message"]
            interest_score = ai_result.get("interest_score", 0)
            ai_analysis = ai_result.get("analysis", "")
            potential_commission = ai_result.get("potential_commission", 0.0)

            # Envia mensagem via WhatsApp
            print(f"📤 Enviando Phoenix #{attempt} para lead {lead.id} (Score: {interest_score}%)")

            result = await send_whatsapp_message(
                to=lead.phone,
                message=message,
            )

            if result.get("success"):
                # Salva mensagem no histórico
                msg = Message(
                    lead_id=lead.id,
                    role="assistant",
                    content=f"[PHOENIX #{attempt}] {message}",
                    tokens_used=0,
                )
                session.add(msg)

                # Atualiza lead com Phoenix data
                lead.phoenix_attempts = attempt
                lead.last_phoenix_at = datetime.utcnow()
                lead.phoenix_status = "pending"  # Aguardando resposta
                lead.phoenix_interest_score = interest_score
                lead.phoenix_ai_analysis = ai_analysis
                lead.phoenix_potential_commission = potential_commission

                # Salva vendedor original se houver
                if lead.assigned_seller_id and not lead.phoenix_original_seller_id:
                    lead.phoenix_original_seller_id = lead.assigned_seller_id

                self.sent_count += 1
                print(f"✅ Phoenix #{attempt} enviado para lead {lead.id}")

            else:
                error = result.get("error", "Erro desconhecido")
                print(f"❌ Falha ao enviar Phoenix para lead {lead.id}: {error}")
                self.error_count += 1

        except Exception as e:
            print(f"❌ Erro ao processar lead {lead.id}: {e}")
            logger.error(f"❌ Erro ao processar lead {lead.id}: {e}", exc_info=True)
            self.error_count += 1

    # =========================================================================
    # GERAÇÃO DE MENSAGEM COM IA
    # =========================================================================

    async def _generate_phoenix_message(
        self,
        lead: Lead,
        attempt: int,
        products: List[Product],
        tenant: Tenant,
    ) -> Optional[Dict[str, Any]]:
        """
        Gera mensagem de reativação ultra-personalizada usando GPT-4o.

        A IA analisa:
        1. Histórico de conversa do lead
        2. Interesse original do lead
        3. Estoque atual de produtos/imóveis
        4. Tempo de inatividade

        RETORNA:
        {
            "message": "Mensagem para enviar",
            "interest_score": 75,  # 0-100
            "analysis": "Análise completa da IA",
            "potential_commission": 5000.00
        }
        """

        try:
            # Extrai histórico de mensagens
            history_text = self._extract_conversation_history(lead)

            # Extrai interesse original
            original_interest = self._extract_lead_interest(lead)

            # Monta lista de produtos atuais
            products_text = self._format_products_for_ai(products)

            # Calcula dias de inatividade
            days_inactive = self._calculate_days_inactive(lead)

            prompt = f"""
Você é o Phoenix Engine da Vellarys, um sistema de reativação inteligente de leads.

# CONTEXTO DO LEAD:
Nome: {lead.name or 'Cliente'}
Telefone: {lead.phone}
Dias inativo: {days_inactive}
Tentativa Phoenix: #{attempt}
Interesse original: {original_interest}

# HISTÓRICO DA CONVERSA:
{history_text}

# ESTOQUE ATUAL ({len(products)} itens):
{products_text}

# SUA MISSÃO:
1. Analise o interesse original do lead
2. Compare com o estoque atual para encontrar matches perfeitos
3. Gere uma mensagem ultra-curta (máx 250 caracteres) e personalizada
4. Estime a intenção de compra (score 0-100)
5. Calcule comissão potencial estimada

# REGRAS DA MENSAGEM:
- Seja casual e amigável, não formal
- Mencione ESPECIFICAMENTE um produto/imóvel que combina com o interesse dele
- Use gatilhos mentais (escassez, novidade, oportunidade)
- Não use "Olá", prefira "Oi", "E aí", "Fala"
- Faça uma pergunta no final para engajar
- Se for tentativa 2, seja mais direto e urgente

# RESPONDA EM JSON:
{{
  "message": "Sua mensagem aqui",
  "interest_score": 75,
  "analysis": "Lead demonstrou interesse em apartamentos 2 quartos. Temos novo lançamento em Canoas que se encaixa perfeitamente.",
  "potential_commission": 5000.00,
  "matched_products": ["Apartamento 2Q Canoas", "Casa 3Q POA"]
}}
"""

            ai_response = await chat_completion(
                messages=[{"role": "system", "content": prompt}],
                temperature=0.7,
                max_tokens=500,
                response_format="json"
            )

            # Parse JSON response
            import json
            result = json.loads(ai_response["content"])

            return {
                "message": result.get("message", "").strip(),
                "interest_score": min(100, max(0, result.get("interest_score", 0))),
                "analysis": result.get("analysis", ""),
                "potential_commission": float(result.get("potential_commission", 0)),
            }

        except Exception as e:
            logger.error(f"⚠️ Falha ao gerar mensagem Phoenix com IA: {e}")
            return None

    # =========================================================================
    # ANÁLISE DE RESPOSTA (Detecta intenção de compra)
    # =========================================================================

    async def analyze_lead_response(
        self,
        lead: Lead,
        response_text: str,
    ) -> Dict[str, Any]:
        """
        Analisa a resposta do lead para detectar intenção de compra.

        Usado pelo webhook quando o lead responde a uma mensagem Phoenix.
        """

        try:
            prompt = f"""
Você é o Phoenix Engine analisando a resposta de um lead reativado.

# RESPOSTA DO LEAD:
"{response_text}"

# SUA MISSÃO:
Analise se o lead demonstra:
1. Intenção de compra (interessado, quer saber mais, quer visitar)
2. Apenas curiosidade (talvez, não sei, vou pensar)
3. Desinteresse (não quero, não tenho interesse)

# RESPONDA EM JSON:
{{
  "has_buying_intent": true,
  "intent_level": "high",  // "high", "medium", "low", "none"
  "confidence": 85,  // 0-100
  "sentiment": "positive",  // "positive", "neutral", "negative"
  "should_escalate": true,  // Se deve notificar o gestor imediatamente
  "reason": "Lead perguntou sobre valores e disponibilidade de visita"
}}
"""

            ai_response = await chat_completion(
                messages=[{"role": "system", "content": prompt}],
                temperature=0.3,
                max_tokens=200,
                response_format="json"
            )

            import json
            result = json.loads(ai_response["content"])

            return {
                "has_buying_intent": result.get("has_buying_intent", False),
                "intent_level": result.get("intent_level", "low"),
                "confidence": result.get("confidence", 0),
                "sentiment": result.get("sentiment", "neutral"),
                "should_escalate": result.get("should_escalate", False),
                "reason": result.get("reason", ""),
            }

        except Exception as e:
            logger.error(f"⚠️ Falha ao analisar resposta do lead: {e}")
            return {
                "has_buying_intent": False,
                "intent_level": "unknown",
                "confidence": 0,
                "sentiment": "neutral",
                "should_escalate": False,
                "reason": f"Erro na análise: {str(e)}",
            }

    # =========================================================================
    # UPLOAD DE CSV (Reativação em Massa)
    # =========================================================================

    async def process_csv_upload(
        self,
        csv_content: str,
        tenant_id: int,
    ) -> Dict[str, Any]:
        """
        Processa upload de CSV com lista de leads para reativar.

        CSV ESPERADO:
        phone,name,note
        5551999999999,João Silva,Lead interessado em 2Q
        5551988888888,Maria Santos,Queria casa em Canoas
        """

        try:
            async with async_session() as session:
                # Parse CSV
                csv_file = io.StringIO(csv_content)
                reader = csv.DictReader(csv_file)

                processed = 0
                added = 0
                errors = []

                for row in reader:
                    try:
                        phone = row.get("phone", "").strip()
                        name = row.get("name", "").strip()
                        note = row.get("note", "").strip()

                        if not phone:
                            continue

                        # Busca lead existente
                        result = await session.execute(
                            select(Lead).where(
                                and_(
                                    Lead.tenant_id == tenant_id,
                                    Lead.phone == phone,
                                )
                            )
                        )
                        lead = result.scalar_one_or_none()

                        if lead:
                            # Marca para Phoenix
                            lead.phoenix_status = "pending"
                            lead.phoenix_attempts = 0
                            lead.last_phoenix_at = None

                            if note:
                                # Adiciona nota ao custom_data
                                custom_data = lead.custom_data or {}
                                custom_data["phoenix_note"] = note
                                lead.custom_data = custom_data

                            added += 1

                        processed += 1

                    except Exception as e:
                        errors.append(f"Linha {processed + 1}: {str(e)}")

                await session.commit()

                return {
                    "success": True,
                    "processed": processed,
                    "added": added,
                    "errors": errors,
                }

        except Exception as e:
            logger.error(f"❌ Erro ao processar CSV: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # APROVAÇÃO DO GESTOR
    # =========================================================================

    async def approve_reactivation(
        self,
        lead_id: int,
        approved: bool,
        notify_seller: bool = True,
    ) -> Dict[str, Any]:
        """
        Gestor aprova ou rejeita a reativação de um lead.

        Se aprovado E notify_seller=True, notifica o vendedor original.
        """

        try:
            async with async_session() as session:
                # Busca lead
                result = await session.execute(
                    select(Lead)
                    .options(selectinload(Lead.assigned_seller))
                    .where(Lead.id == lead_id)
                )
                lead = result.scalar_one_or_none()

                if not lead:
                    return {"success": False, "error": "Lead não encontrado"}

                if approved:
                    lead.phoenix_status = "approved"
                    lead.status = "reactivated"  # Muda status principal

                    # Se deve notificar vendedor
                    if notify_seller and lead.phoenix_original_seller_id:
                        # TODO: Enviar notificação para o vendedor
                        pass

                    self.reactivated_count += 1

                else:
                    lead.phoenix_status = "rejected"

                await session.commit()

                return {
                    "success": True,
                    "status": "approved" if approved else "rejected",
                }

        except Exception as e:
            logger.error(f"❌ Erro ao aprovar reativação: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # DASHBOARD METRICS
    # =========================================================================

    async def get_dashboard_metrics(self, tenant_id: int) -> Dict[str, Any]:
        """
        Retorna métricas do Phoenix Engine para o dashboard.
        """

        try:
            async with async_session() as session:
                # Total de leads reativados
                result = await session.execute(
                    select(Lead).where(
                        and_(
                            Lead.tenant_id == tenant_id,
                            Lead.phoenix_status == "approved",
                        )
                    )
                )
                reactivated_leads = result.scalars().all()

                # Leads pendentes de aprovação
                result = await session.execute(
                    select(Lead).where(
                        and_(
                            Lead.tenant_id == tenant_id,
                            Lead.phoenix_status == "reactivated",
                        )
                    )
                )
                pending_leads = result.scalars().all()

                # Taxa de resposta
                result = await session.execute(
                    select(Lead).where(
                        and_(
                            Lead.tenant_id == tenant_id,
                            Lead.phoenix_attempts > 0,
                        )
                    )
                )
                contacted_leads = result.scalars().all()

                response_rate = 0
                if len(contacted_leads) > 0:
                    responded = sum(1 for l in contacted_leads if l.phoenix_status in ["reactivated", "approved"])
                    response_rate = (responded / len(contacted_leads)) * 100

                # Comissão potencial total
                total_commission = sum(
                    l.phoenix_potential_commission or 0
                    for l in reactivated_leads
                )

                return {
                    "total_reactivated": len(reactivated_leads),
                    "pending_approval": len(pending_leads),
                    "response_rate": round(response_rate, 1),
                    "total_potential_commission": round(total_commission, 2),
                    "contacted_count": len(contacted_leads),
                }

        except Exception as e:
            logger.error(f"❌ Erro ao buscar métricas: {e}")
            return {
                "total_reactivated": 0,
                "pending_approval": 0,
                "response_rate": 0,
                "total_potential_commission": 0,
                "contacted_count": 0,
            }

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_phoenix_config(self, tenant: Tenant) -> dict:
        """Obtém configurações Phoenix do tenant."""
        settings = tenant.settings or {}
        phoenix = settings.get("phoenix_engine", {})

        # Merge com defaults
        config = DEFAULT_PHOENIX_CONFIG.copy()
        config.update(phoenix)

        return config

    def _is_allowed_time(self, tenant: Tenant, config: dict) -> bool:
        """Verifica se está em horário permitido."""
        # Mesma lógica do follow_up_service.py
        settings = tenant.settings or {}

        if config.get("respect_business_hours", True):
            business_hours = settings.get("business_hours", {})

            if business_hours.get("enabled", False):
                return self._is_within_business_hours(business_hours)

        allowed_hours = config.get("allowed_hours", {})
        return self._is_within_allowed_hours(allowed_hours, settings)

    def _is_within_business_hours(self, business_hours: dict) -> bool:
        """Verifica horário comercial."""
        timezone_str = business_hours.get("timezone", "America/Sao_Paulo")

        try:
            tz = ZoneInfo(timezone_str)
        except Exception:
            tz = ZoneInfo("America/Sao_Paulo")

        now = datetime.now(tz)
        day_name = now.strftime("%A").lower()

        schedule = business_hours.get("schedule", {})
        day_config = schedule.get(day_name, {})

        if not day_config.get("enabled", False):
            return False

        try:
            open_time = datetime.strptime(day_config.get("open", "08:00"), "%H:%M").time()
            close_time = datetime.strptime(day_config.get("close", "18:00"), "%H:%M").time()
            current_time = now.time()

            return open_time <= current_time <= close_time

        except Exception:
            return True

    def _is_within_allowed_hours(self, allowed_hours: dict, settings: dict) -> bool:
        """Verifica horas permitidas."""
        business_hours = settings.get("business_hours", {})
        timezone_str = business_hours.get("timezone", "America/Sao_Paulo")

        try:
            tz = ZoneInfo(timezone_str)
        except Exception:
            tz = ZoneInfo("America/Sao_Paulo")

        now = datetime.now(tz)

        try:
            start_time = datetime.strptime(allowed_hours.get("start", "09:00"), "%H:%M").time()
            end_time = datetime.strptime(allowed_hours.get("end", "18:00"), "%H:%M").time()
            current_time = now.time()

            return start_time <= current_time <= end_time

        except Exception:
            return True

    async def _get_tenant_products(self, session: AsyncSession, tenant: Tenant) -> List[Product]:
        """Busca produtos/imóveis atuais do tenant."""
        try:
            result = await session.execute(
                select(Product)
                .where(Product.tenant_id == tenant.id)
                .limit(20)  # Limita para não sobrecarregar a IA
            )
            return list(result.scalars().all())
        except Exception:
            return []

    def _format_products_for_ai(self, products: List[Product]) -> str:
        """Formata produtos para a IA."""
        if not products:
            return "Nenhum produto no estoque atual."

        lines = []
        for i, p in enumerate(products[:10], 1):  # Max 10 produtos
            line = f"{i}. {p.name}"
            if p.price:
                line += f" - R$ {p.price:,.2f}"
            if p.description:
                line += f" ({p.description[:50]}...)" if len(p.description) > 50 else f" ({p.description})"
            lines.append(line)

        return "\n".join(lines)

    def _extract_conversation_history(self, lead: Lead) -> str:
        """Extrai histórico de conversa."""
        if not lead.messages:
            return "Sem histórico de conversa."

        recent = sorted(lead.messages, key=lambda m: m.created_at, reverse=True)[:8]
        lines = []
        for msg in reversed(recent):
            role = "Cliente" if msg.role == "user" else "IA"
            content = msg.content[:100]
            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def _extract_lead_interest(self, lead: Lead) -> str:
        """Extrai interesse original do lead."""
        custom_data = lead.custom_data or {}

        # Tenta várias chaves
        for key in ["interesse", "interest", "property_type", "servico", "produto"]:
            if custom_data.get(key):
                return custom_data[key]

        # Fallback: usa summary se houver
        if lead.summary:
            return lead.summary[:100]

        return "Interesse não especificado"

    def _calculate_days_inactive(self, lead: Lead) -> int:
        """Calcula dias de inatividade."""
        if not lead.last_activity_at:
            return 999  # Muito tempo

        delta = datetime.utcnow() - lead.last_activity_at
        return delta.days


# =============================================================================
# INSTÂNCIA GLOBAL
# =============================================================================

phoenix_engine_service = PhoenixEngineService()


# =============================================================================
# FUNÇÃO PARA O SCHEDULER
# =============================================================================

async def run_phoenix_engine_job():
    """Função para ser chamada pelo scheduler."""
    print("⏰ Scheduler chamou run_phoenix_engine_job()")
    print("=" * 60)

    result = await phoenix_engine_service.process_all_tenants()

    print("=" * 60)
    print("✅ PHOENIX ENGINE JOB FINALIZADO")
    print(f"   Reativados: {result.get('reactivated', 0)}")
    print("=" * 60)

    return result
