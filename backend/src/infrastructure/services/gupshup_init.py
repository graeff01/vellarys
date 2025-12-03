"""
INICIALIZAÇÃO GUPSHUP
======================

Configura o serviço Gupshup no startup da aplicação.
Chamado pelo main.py no evento de startup.
"""

import logging
from src.config import get_settings
from src.infrastructure.services.gupshup_service import (
    GupshupConfig,
    configure_gupshup_service,
    get_gupshup_service,
)

logger = logging.getLogger(__name__)


def init_gupshup_service():
    """
    Inicializa o serviço Gupshup com as configurações do .env
    
    Deve ser chamado no startup da aplicação (main.py).
    Se as variáveis não estiverem configuradas, o serviço
    funcionará em modo mock (não envia mensagens reais).
    """
    settings = get_settings()
    
    if settings.gupshup_configured:
        config = GupshupConfig(
            api_key=settings.gupshup_api_key,
            app_name=settings.gupshup_app_name,
            source_phone=settings.gupshup_source_phone,
            webhook_secret=settings.gupshup_webhook_secret,
        )
        
        service = configure_gupshup_service(config)
        logger.info(f"✅ Gupshup configurado - App: {config.app_name}, Phone: {config.source_phone}")
        
        return service
    else:
        logger.warning("⚠️ Gupshup não configurado - rodando em modo MOCK")
        logger.warning("   Configure GUPSHUP_API_KEY, GUPSHUP_APP_NAME e GUPSHUP_SOURCE_PHONE no .env")
        
        # Retorna serviço em modo mock
        return get_gupshup_service()


async def shutdown_gupshup_service():
    """
    Fecha conexões do Gupshup no shutdown da aplicação.
    """
    service = get_gupshup_service()
    await service.close()
    logger.info("Gupshup service encerrado")