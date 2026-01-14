import logging
from typing import Optional
from src.config import get_settings
from .interface import LLMProvider
from .openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)
settings = get_settings()

class LLMFactory:
    """
    Fábrica para criar instâncias de provedores LLM.
    """
    
    _instance: Optional[LLMProvider] = None

    @staticmethod
    def get_provider(provider_type: str = "openai") -> LLMProvider:
        """
        Retorna uma instância do provedor solicitado.
        Por enquanto suporta apenas 'openai', mas preparado para expansão.
        """
        if LLMFactory._instance:
            return LLMFactory._instance
            
        # Aqui poderíamos ler de settings.llm_provider
        if provider_type.lower() == "openai":
            logger.info("Inicializando OpenAI Provider")
            LLMFactory._instance = OpenAIProvider()
            return LLMFactory._instance
        
        # Futuro: if provider_type == "anthropic": ...
        
        raise ValueError(f"Provedor LLM desconhecido: {provider_type}")
