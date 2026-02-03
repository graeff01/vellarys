"""
MORNING BRIEFING JOB
====================

Job agendado para enviar briefings matinais para gestores de cada tenant.
Executa diariamente às 08:00 (horário de São Paulo).
"""

import asyncio
import logging
from datetime import datetime
import pytz

from src.infrastructure.database import async_session
from src.infrastructure.services.morning_briefing_service import MorningBriefingService
from sqlalchemy import select
from src.domain.entities import Tenant

logger = logging.getLogger(__name__)


async def run_morning_briefing_job():
    """
    Executa o job de envio de Morning Briefing.

    Lógica:
    1. Itera por todos os tenants ativos
    2. Para cada tenant, verifica se chegou o horário configurado
    3. Envia o briefing para o gestor no horário específico do tenant
    """

    # Timezone padrão (São Paulo)
    tz = pytz.timezone("America/Sao_Paulo")
    now = datetime.now(tz)
    current_hour = now.hour
    current_minute = now.minute
    current_time_str = f"{current_hour:02d}:{current_minute:02d}"

    logger.info(f"⏰ Morning Briefing Job: Verificando horários (atual: {current_time_str})")

    try:
        async with async_session() as db:
            # Busca todos os tenants ativos
            result = await db.execute(
                select(Tenant).where(
                    Tenant.active == True
                )
            )
            tenants = result.scalars().all()

            if not tenants:
                logger.warning("⚠️ Nenhum tenant ativo encontrado")
                return

            logger.info(f"📊 Encontrados {len(tenants)} tenants ativos")

            # Envia briefing para cada tenant
            sent_count = 0
            failed_count = 0
            skipped_count = 0

            for tenant in tenants:
                try:
                    # Verifica horário configurado do tenant (default: 08:00)
                    tenant_settings = tenant.settings or {}
                    configured_time = tenant_settings.get('morning_briefing_time', '08:00')

                    # Extrai hora e minuto configurados
                    try:
                        configured_hour, configured_minute = map(int, configured_time.split(':'))
                    except (ValueError, AttributeError):
                        configured_hour, configured_minute = 8, 0  # Fallback para 08:00

                    # Verifica se é o horário correto para este tenant (±5 minutos de tolerância)
                    time_diff_minutes = abs((current_hour * 60 + current_minute) - (configured_hour * 60 + configured_minute))

                    if time_diff_minutes > 5:
                        # Não é o horário deste tenant, pula
                        logger.debug(f"⏭️  Tenant {tenant.name}: Horário configurado {configured_time}, atual {current_time_str} - pulando")
                        skipped_count += 1
                        continue

                    logger.info(f"📤 Enviando briefing para tenant: {tenant.name} (ID: {tenant.id}) - Horário: {configured_time}")

                    # Cria instância do serviço
                    service = MorningBriefingService(db)

                    # Gera e envia o briefing
                    result = await service.generate_and_send(tenant_id=tenant.id)

                    if result.get("success"):
                        sent_count += 1
                        recipient = result.get("recipient", "N/A")
                        logger.info(f"✅ Briefing enviado com sucesso para {recipient} (Tenant: {tenant.name})")
                    else:
                        failed_count += 1
                        error = result.get("error", "Erro desconhecido")
                        logger.warning(f"⚠️ Falha ao enviar briefing para tenant {tenant.name}: {error}")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Erro ao processar tenant {tenant.name} (ID: {tenant.id}): {str(e)}", exc_info=True)
                    continue

                # Pequeno delay entre envios para não sobrecarregar o servidor de email
                await asyncio.sleep(2)

            # Log final
            if sent_count > 0 or failed_count > 0:
                logger.info(f"""
🎯 Morning Briefing Job Concluído:
   ✅ Enviados: {sent_count}
   ❌ Falharam: {failed_count}
   ⏭️  Pulados: {skipped_count} (horário diferente)
   📊 Total: {len(tenants)} tenants
   ⏰ Horário: {now.strftime('%Y-%m-%d %H:%M:%S')}
                """)
            else:
                logger.debug(f"⏰ Nenhum tenant com horário configurado para {current_time_str}")

    except Exception as e:
        logger.error(f"❌ Erro crítico no Morning Briefing Job: {str(e)}", exc_info=True)
        raise


def should_run_now() -> bool:
    """
    Verifica se o job deve ser executado agora.
    Retorna True apenas se for entre 08:00 e 08:59 no timezone de São Paulo.
    """
    tz = pytz.timezone("America/Sao_Paulo")
    now = datetime.now(tz)
    return now.hour == 8
