import logging
import json
import sys
from typing import Any

class JSONFormatter(logging.Formatter):
    """
    Formatador de logs em JSON para facilitar ingestão por ferramentas de observabilidade (Datadog, CloudWatch, etc).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Adiciona campos extras passados no log
        if hasattr(record, "extra"):
            log_record.update(record.extra)  # type: ignore

        return json.dumps(log_record, default=str)

def setup_logging():
    """
    Configura o logging raiz da aplicação para usar JSON.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    # Remove handlers existentes para evitar duplicação
    logger.handlers = []
    logger.addHandler(handler)

    # Configura loggers de bibliotecas específicas para reduzir ruído
    logging.getLogger("uvicorn.access").handlers = []  # Deixa o uvicorn usar o root logger
    logging.getLogger("uvicorn.error").handlers = []
    logging.getLogger("multipart").setLevel(logging.WARNING)
