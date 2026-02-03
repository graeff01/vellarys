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

from src.database import get_db_context
from src.infrastructure.services.morning_briefing_service import MorningBriefingService
from sqlalchemy import select
from src.models.tenant import Tenant

logger = logging.getLogger(__name__)


async def run_morning_briefing_job():
    """
    Executa o job de envio de Morning Briefing.

    Lógica:
    1. Verifica se é horário adequado (08:00 - 09:00)
    2. Itera por todos os tenants ativos
    3. Para cada tenant, envia o briefing para o gestor
    """

    # Timezone padrão (São Paulo)
    tz = pytz.timezone("America/Sao_Paulo")
    now = datetime.now(tz)
    current_hour = now.hour
    current_minute = now.minute

    # Verifica se está no horário correto (08:00 - 08:59)
    # Isso evita múltiplas execuções no mesmo dia
    if current_hour != 8:
        logger.info(f"⏰ Morning Briefing: Fora do horário (atual: {current_hour:02d}:{current_minute:02d}). Pulando execução.")
        return

    logger.info(f"📧 Iniciando envio de Morning Briefings ({now.strftime('%Y-%m-%d %H:%M:%S')})")

    try:
        async with get_db_context() as db:
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

            for tenant in tenants:
                try:
                    logger.info(f"📤 Enviando briefing para tenant: {tenant.name} (ID: {tenant.id})")

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
            logger.info(f"""
🎯 Morning Briefing Job Concluído:
   ✅ Enviados: {sent_count}
   ❌ Falharam: {failed_count}
   📊 Total: {len(tenants)} tenants
   ⏰ Horário: {now.strftime('%Y-%m-%d %H:%M:%S')}
            """)

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
