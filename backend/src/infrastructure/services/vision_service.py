import logging
from src.infrastructure.llm.factory import LLMFactory

logger = logging.getLogger(__name__)

async def analyze_property_image(image_url: str) -> str:
    """
    Analisa uma imagem enviada pelo lead para extrair contexto imobiliário.
    """
    provider = LLMFactory.get_provider()
    
    prompt = """
Analise esta imagem enviada por um cliente de uma imobiliária.
OBJETIVO: Identificar o que é e extrair informações úteis.

Possíveis cenários:
1. Print de um imóvel em um portal (tente ler código, preço, bairro, quartos).
2. Foto de uma planta baixa (descreva brevemente a disposição).
3. Foto de uma fachada ou cômodo (identifique o tipo de imóvel e estado de conservação).
4. Print de uma conversa ou documento.

Retorne uma descrição curta e técnica do que você vê, focada em ajudar o corretor a entender o interesse do cliente.
Se houver um CÓDIGO de imóvel visível, destaque-o como 'CÓDIGO: XXXXXX'.
"""
    
    try:
        logger.info(f"👁️ Analisando imagem: {image_url}")
        description = await provider.analyze_image(image_url, prompt)
        return description
    except Exception as e:
        logger.error(f"❌ Erro no VisionService: {e}")
        return "[Falha ao analisar imagem]"
