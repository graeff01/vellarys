"""
SERVIÇO DE TEXT-TO-SPEECH (TTS) - OPENAI
=========================================

Converte texto em áudio usando OpenAI TTS.
Usado para responder leads com áudio quando eles enviam áudio.

Vozes disponíveis (OpenAI):
- alloy: Neutra, equilibrada
- echo: Masculina, grave
- fable: Britânica, expressiva
- onyx: Masculina, profunda
- nova: Feminina, jovem (RECOMENDADA para atendimento)
- shimmer: Feminina, suave

Configuração por tenant:
- voice_response.enabled: True/False
- voice_response.voice: "nova" (padrão)
- voice_response.speed: 1.0 (0.25 a 4.0)
"""

import os
import uuid
import logging
import httpx
from typing import Optional, Literal
from openai import AsyncOpenAI

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Diretório temporário para áudios gerados
TEMP_AUDIO_DIR = "temp_audio"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

# Vozes disponíveis
AVAILABLE_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

# Tipo de voz
VoiceType = Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


class TTSService:
    """Serviço de Text-to-Speech usando OpenAI."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.default_voice = "nova"  # Voz feminina, jovem, ideal para atendimento
        self.default_speed = 1.0
        self.model = "tts-1-hd"  # tts-1-hd para melhor qualidade e som mais natural

    async def generate_audio(
        self,
        text: str,
        voice: VoiceType = "nova",
        speed: float = 1.0,
        output_format: str = "opus",  # opus é melhor para WhatsApp
    ) -> Optional[str]:
        """
        Gera áudio a partir de texto.

        Args:
            text: Texto para converter em áudio
            voice: Voz a usar (nova, alloy, echo, fable, onyx, shimmer)
            speed: Velocidade (0.25 a 4.0, padrão 1.0)
            output_format: Formato do áudio (opus, mp3, aac, flac, wav, pcm)

        Returns:
            Caminho do arquivo de áudio gerado ou None se falhar
        """
        if not text or not text.strip():
            logger.warning("⚠️ TTS: Texto vazio, ignorando")
            return None

        # Limita tamanho do texto (OpenAI aceita até 4096 chars)
        if len(text) > 4096:
            text = text[:4093] + "..."
            logger.warning(f"⚠️ TTS: Texto truncado para 4096 caracteres")

        # Valida voz
        if voice not in AVAILABLE_VOICES:
            logger.warning(f"⚠️ TTS: Voz '{voice}' inválida, usando 'nova'")
            voice = "nova"

        # Valida velocidade
        speed = max(0.25, min(4.0, speed))

        # Gera nome único para o arquivo
        file_extension = "ogg" if output_format == "opus" else output_format
        temp_file = os.path.join(TEMP_AUDIO_DIR, f"tts_{uuid.uuid4()}.{file_extension}")

        try:
            logger.info(f"🎙️ TTS: Gerando áudio com voz '{voice}' ({len(text)} chars)")

            # Chama OpenAI TTS
            response = await self.client.audio.speech.create(
                model=self.model,
                voice=voice,
                input=text,
                speed=speed,
                response_format=output_format,
            )

            # Salva o áudio (stream_to_file é o método correto)
            response.stream_to_file(temp_file)

            # Verifica se o arquivo foi criado
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                file_size = os.path.getsize(temp_file)
                logger.info(f"✅ TTS: Áudio gerado com sucesso ({file_size} bytes) -> {temp_file}")
                return temp_file
            else:
                logger.error("❌ TTS: Arquivo de áudio vazio ou não criado")
                return None

        except Exception as e:
            logger.error(f"❌ TTS: Erro ao gerar áudio: {e}")
            # Limpa arquivo se existir
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            return None

    async def generate_audio_bytes(
        self,
        text: str,
        voice: VoiceType = "nova",
        speed: float = 1.0,
        output_format: str = "opus",
    ) -> Optional[bytes]:
        """
        Gera áudio e retorna como bytes (sem salvar arquivo).
        Útil para envio direto.

        Returns:
            Bytes do áudio ou None se falhar
        """
        if not text or not text.strip():
            return None

        if len(text) > 4096:
            text = text[:4093] + "..."

        if voice not in AVAILABLE_VOICES:
            voice = "nova"

        speed = max(0.25, min(4.0, speed))

        try:
            logger.info(f"🎙️ TTS: Gerando áudio bytes com voz '{voice}'")

            response = await self.client.audio.speech.create(
                model=self.model,
                voice=voice,
                input=text,
                speed=speed,
                response_format=output_format,
            )

            # Lê os bytes diretamente (nova API da OpenAI)
            audio_bytes = response.content

            if audio_bytes:
                logger.info(f"✅ TTS: Áudio gerado ({len(audio_bytes)} bytes)")
                return audio_bytes
            else:
                logger.error("❌ TTS: Áudio vazio")
                return None

        except Exception as e:
            logger.error(f"❌ TTS: Erro ao gerar áudio bytes: {e}")
            return None

    @staticmethod
    def cleanup_audio_file(file_path: str) -> bool:
        """
        Remove arquivo de áudio temporário.

        Returns:
            True se removido com sucesso
        """
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"🗑️ TTS: Arquivo removido: {file_path}")
                return True
            except Exception as e:
                logger.warning(f"⚠️ TTS: Erro ao remover arquivo: {e}")
                return False
        return False

    @staticmethod
    def get_voice_options() -> list:
        """Retorna opções de voz disponíveis com descrições."""
        return [
            {
                "id": "nova",
                "name": "Nova",
                "description": "Feminina, jovem e acolhedora (Recomendada)",
                "gender": "female",
                "recommended": True,
            },
            {
                "id": "shimmer",
                "name": "Shimmer",
                "description": "Feminina, suave e profissional",
                "gender": "female",
                "recommended": False,
            },
            {
                "id": "alloy",
                "name": "Alloy",
                "description": "Neutra, equilibrada e versátil",
                "gender": "neutral",
                "recommended": False,
            },
            {
                "id": "echo",
                "name": "Echo",
                "description": "Masculina, grave e confiante",
                "gender": "male",
                "recommended": False,
            },
            {
                "id": "onyx",
                "name": "Onyx",
                "description": "Masculina, profunda e séria",
                "gender": "male",
                "recommended": False,
            },
            {
                "id": "fable",
                "name": "Fable",
                "description": "Expressiva, britânica e articulada",
                "gender": "neutral",
                "recommended": False,
            },
        ]


# Instância singleton
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Retorna instância singleton do serviço TTS."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service


# Função helper para uso direto
async def text_to_speech(
    text: str,
    voice: str = "nova",
    speed: float = 1.0,
) -> Optional[str]:
    """
    Helper function para converter texto em áudio.

    Returns:
        Caminho do arquivo de áudio ou None
    """
    service = get_tts_service()
    return await service.generate_audio(text, voice, speed)
