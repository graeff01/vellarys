"""
SCHEDULER NATIVO - SEM DEPENDÊNCIAS EXTERNAS
=============================================

Usa apenas threading e asyncio do Python.
Não precisa do APScheduler!

ÚLTIMA ATUALIZAÇÃO: 2025-12-26
"""

import asyncio
import threading
import logging
from datetime import datetime
from typing import Callable, Optional
import pytz

logger = logging.getLogger(__name__)

# ============================================
# SCHEDULER SIMPLES
# ============================================

class SimpleScheduler:
    """Scheduler simples usando threading nativo."""
    
    def __init__(self, timezone: str = "America/Sao_Paulo"):
        self.timezone = pytz.timezone(timezone)
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.jobs: dict[str, dict] = {}
        self._stop_event = threading.Event()
    
    def add_job(
        self,
        job_id: str,
        func: Callable,
        interval_minutes: int = 60,
        run_immediately: bool = False
    ):
        """Adiciona um job ao scheduler."""
        self.jobs[job_id] = {
            "func": func,
            "interval_minutes": interval_minutes,
            "last_run": None,
            "run_immediately": run_immediately,
        }
        print(f"📅 Job registrado: {job_id} (a cada {interval_minutes} minutos)")
    
    def start(self):
        """Inicia o scheduler em uma thread separada."""
        if self.running:
            print("⚠️ Scheduler já está rodando")
            return
        
        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("🚀 Scheduler nativo iniciado!")
    
    def stop(self):
        """Para o scheduler."""
        if not self.running:
            return
        
        self.running = False
        self._stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        print("🛑 Scheduler parado")
    
    def _run_loop(self):
        """Loop principal do scheduler."""
        print("🔄 Loop do scheduler iniciado")
        
        while not self._stop_event.is_set():
            try:
                now = datetime.now(self.timezone)
                
                for job_id, job in self.jobs.items():
                    should_run = False
                    
                    # Primeira execução
                    if job["last_run"] is None:
                        if job["run_immediately"]:
                            should_run = True
                        else:
                            # Agenda para o próximo intervalo
                            job["last_run"] = now
                    else:
                        # Verifica se passou o intervalo
                        elapsed = (now - job["last_run"]).total_seconds() / 60
                        if elapsed >= job["interval_minutes"]:
                            should_run = True
                    
                    if should_run:
                        print(f"⏰ Executando job: {job_id}")
                        job["last_run"] = now
                        
                        try:
                            # Executa a função (pode ser async ou sync)
                            func = job["func"]
                            if asyncio.iscoroutinefunction(func):
                                # Cria novo event loop para executar async
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    loop.run_until_complete(func())
                                finally:
                                    loop.close()
                            else:
                                func()
                            
                            print(f"✅ Job {job_id} executado com sucesso")
                        except Exception as e:
                            print(f"❌ Erro no job {job_id}: {e}")
                
                # Aguarda 60 segundos antes de verificar novamente
                self._stop_event.wait(60)
                
            except Exception as e:
                print(f"❌ Erro no loop do scheduler: {e}")
                self._stop_event.wait(60)
    
    def run_job_now(self, job_id: str) -> bool:
        """Executa um job imediatamente."""
        if job_id not in self.jobs:
            print(f"❌ Job não encontrado: {job_id}")
            return False
        
        job = self.jobs[job_id]
        print(f"🚀 Executando job manualmente: {job_id}")
        
        try:
            func = job["func"]
            if asyncio.iscoroutinefunction(func):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(func())
                finally:
                    loop.close()
            else:
                func()
            
            job["last_run"] = datetime.now(self.timezone)
            print(f"✅ Job {job_id} executado manualmente com sucesso")
            return True
        except Exception as e:
            print(f"❌ Erro ao executar job {job_id}: {e}")
            return False
    
    def get_status(self) -> dict:
        """Retorna status do scheduler."""
        jobs_status = {}
        for job_id, job in self.jobs.items():
            jobs_status[job_id] = {
                "interval_minutes": job["interval_minutes"],
                "last_run": job["last_run"].isoformat() if job["last_run"] else None,
            }
        
        return {
            "running": self.running,
            "timezone": str(self.timezone),
            "jobs": jobs_status,
        }


# ============================================
# INSTÂNCIA GLOBAL
# ============================================

_scheduler: Optional[SimpleScheduler] = None


def get_scheduler() -> SimpleScheduler:
    """Retorna a instância do scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SimpleScheduler()
    return _scheduler


def create_scheduler():
    """Cria e configura o scheduler."""
    from src.infrastructure.jobs.follow_up_service import run_follow_up_job
    
    print("🔧 Criando scheduler nativo...")
    
    scheduler = get_scheduler()
    
    # Registra o job de follow-up (a cada 60 minutos)
    scheduler.add_job(
        job_id="follow_up_job",
        func=run_follow_up_job,
        interval_minutes=60,
        run_immediately=False,
    )
    
    print("✅ Scheduler configurado!")
    return scheduler


def start_scheduler():
    """Inicia o scheduler."""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """Para o scheduler."""
    scheduler = get_scheduler()
    scheduler.stop()


def get_scheduler_status() -> dict:
    """Retorna status do scheduler."""
    scheduler = get_scheduler()
    return scheduler.get_status()


async def run_job_now(job_id: str) -> bool:
    """Executa um job manualmente."""
    scheduler = get_scheduler()
    return scheduler.run_job_now(job_id)