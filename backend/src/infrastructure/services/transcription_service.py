"""
SERVIÇO DE TRANSCRIÇÃO - WHISPER
=================================
Gerencia o download de áudios e a chamada para o Whisper.
"""

import os
import uuid
import logging
import httpx
from typing import Optional
from src.infrastructure.llm import LLMFactory

logger = logging.getLogger(__name__)

# Diretório temporário para áudios
TEMP_AUDIO_DIR = "temp_audio"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

async def transcribe_audio_url(url: str, prompt: Optional[str] = None) -> Optional[str]:
    """
    Baixa um arquivo de áudio de uma URL e o transcreve via Whisper.
    """
    temp_file = os.path.join(TEMP_AUDIO_DIR, f"{uuid.uuid4()}.oga")
    
    try:
        # 1. Download do arquivo
        logger.info(f"🎙️ Baixando áudio de: {url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            if response.status_code != 200:
                logger.error(f"❌ Erro ao baixar áudio: {response.status_code}")
                return None
            
            with open(temp_file, "wb") as f:
                f.write(response.content)
        
        # 2. Transcrição via LLM Provider
        logger.info(f"🎙️ Enviando para Whisper: {temp_file} | Prompt: {prompt[:50] if prompt else 'N/A'}")
        provider = LLMFactory.get_provider()
        text = await provider.transcribe(temp_file, prompt=prompt)
        
        logger.info(f"✅ Transcrição concluída: \"{text[:50]}...\"")
        return text
        
    except Exception as e:
        logger.error(f"❌ Erro no serviço de transcrição: {e}")
        return None
        
    finally:
        # 3. Limpeza do arquivo temporário
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                logger.info(f"🗑️ Arquivo temporário removido: {temp_file}")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível remover {temp_file}: {e}")
