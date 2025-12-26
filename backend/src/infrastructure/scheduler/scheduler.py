"""
SCHEDULER DE JOBS PERIÓDICOS
=============================

Gerencia a execução de tarefas agendadas.

JOBS CONFIGURADOS:
- Follow-up automático: A cada hora

TECNOLOGIA: APScheduler (AsyncIOScheduler)

ÚLTIMA ATUALIZAÇÃO: 2024-12-26
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Instância global do scheduler
scheduler: AsyncIOScheduler = None


def create_scheduler() -> AsyncIOScheduler:
    """
    Cria e configura o scheduler.
    
    CHAMADO POR: main.py no startup
    """
    global scheduler
    
    if scheduler is not None:
        logger.warning("⚠️ Scheduler já existe, retornando instância existente")
        return scheduler
    
    logger.info("🔧 Criando scheduler...")
    
    scheduler = AsyncIOScheduler(
        timezone="America/Sao_Paulo",
        job_defaults={
            "coalesce": True,  # Agrupa execuções perdidas
            "max_instances": 1,  # Só uma instância por vez
            "misfire_grace_time": 60 * 5,  # 5 minutos de tolerância
        }
    )
    
    # =========================================================================
    # REGISTRA OS JOBS
    # =========================================================================
    
    _register_follow_up_job(scheduler)
    
    logger.info("✅ Scheduler criado com sucesso")
    
    return scheduler


def _register_follow_up_job(sched: AsyncIOScheduler):
    """
    Registra o job de follow-up automático.
    
    EXECUTA: A cada hora, no minuto 30
    EXEMPLO: 08:30, 09:30, 10:30, ...
    """
    from src.infrastructure.jobs.follow_up_service import run_follow_up_job
    
    sched.add_job(
        run_follow_up_job,
        trigger=CronTrigger(minute=30),  # A cada hora no minuto 30
        id="follow_up_job",
        name="Follow-up Automático",
        replace_existing=True,
    )
    
    logger.info("📅 Job registrado: Follow-up Automático (a cada hora, minuto 30)")


def start_scheduler():
    """
    Inicia o scheduler.
    
    CHAMADO POR: main.py no startup (depois de create_scheduler)
    """
    global scheduler
    
    if scheduler is None:
        logger.error("❌ Scheduler não foi criado. Chame create_scheduler() primeiro.")
        return
    
    if scheduler.running:
        logger.warning("⚠️ Scheduler já está rodando")
        return
    
    scheduler.start()
    logger.info("🚀 Scheduler iniciado!")
    
    # Lista jobs registrados
    jobs = scheduler.get_jobs()
    logger.info(f"📋 Jobs ativos: {len(jobs)}")
    for job in jobs:
        logger.info(f"   - {job.name} (próxima execução: {job.next_run_time})")


def stop_scheduler():
    """
    Para o scheduler.
    
    CHAMADO POR: main.py no shutdown
    """
    global scheduler
    
    if scheduler is None:
        return
    
    if not scheduler.running:
        return
    
    scheduler.shutdown(wait=False)
    logger.info("🛑 Scheduler parado")


def get_scheduler_status() -> dict:
    """
    Retorna status do scheduler.
    
    Útil para endpoint de health check.
    """
    global scheduler
    
    if scheduler is None:
        return {
            "running": False,
            "jobs": [],
            "error": "Scheduler não inicializado",
        }
    
    jobs_info = []
    for job in scheduler.get_jobs():
        jobs_info.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs_info,
    }


async def run_job_now(job_id: str) -> dict:
    """
    Executa um job imediatamente (fora do agendamento).
    
    Útil para testes ou execução manual pelo admin.
    """
    global scheduler
    
    if scheduler is None:
        return {"success": False, "error": "Scheduler não inicializado"}
    
    job = scheduler.get_job(job_id)
    
    if job is None:
        return {"success": False, "error": f"Job '{job_id}' não encontrado"}
    
    try:
        # Executa o job imediatamente
        if job_id == "follow_up_job":
            from src.infrastructure.jobs.follow_up_service import run_follow_up_job
            result = await run_follow_up_job()
            return {"success": True, "result": result}
        
        return {"success": False, "error": "Job não suporta execução manual"}
        
    except Exception as e:
        logger.error(f"❌ Erro ao executar job {job_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}