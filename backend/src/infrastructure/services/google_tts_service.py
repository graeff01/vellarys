"""
SERVIÇO DE TEXT-TO-SPEECH - GOOGLE CLOUD
=========================================

Converte texto em áudio usando Google Cloud TTS.
Vozes em português brasileiro nativo.

Vozes disponíveis (pt-BR):
- pt-BR-Standard-A: Feminina (padrão)
- pt-BR-Standard-B: Masculina
- pt-BR-Neural2-A: Feminina Neural (melhor qualidade)
- pt-BR-Neural2-B: Masculina Neural (melhor qualidade)
- pt-BR-Neural2-C: Feminina Neural 2

Custo: ~US$ 0.016 / 1000 chars (Neural)
       ~US$ 0.004 / 1000 chars (Standard)
"""

import os
import uuid
import logging
import base64
from typing import Optional, Literal

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Diretório temporário para áudios gerados
TEMP_AUDIO_DIR = "temp_audio"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

# Vozes disponíveis
AVAILABLE_VOICES = {
    "camila": "pt-BR-Neural2-A",      # Feminina Neural (recomendada)
    "vitoria": "pt-BR-Neural2-C",     # Feminina Neural 2
    "ricardo": "pt-BR-Neural2-B",     # Masculina Neural
    "ana": "pt-BR-Standard-A",        # Feminina Standard (mais barato)
    "carlos": "pt-BR-Standard-B",     # Masculina Standard (mais barato)
}

VoiceType = Literal["camila", "vitoria", "ricardo", "ana", "carlos"]


class GoogleTTSService:
    """Serviço de Text-to-Speech usando Google Cloud."""

    def __init__(self):
        # Importa apenas se Google TTS estiver configurado
        try:
            from google.cloud import texttospeech
            self.client = texttospeech.TextToSpeechClient()
            self.available = True
            logger.info("✅ Google Cloud TTS inicializado")
        except Exception as e:
            logger.warning(f"⚠️ Google Cloud TTS não disponível: {e}")
            self.client = None
            self.available = False

        self.default_voice = "camila"  # Voz feminina Neural
        self.default_speed = 1.0

    async def generate_audio_bytes(
        self,
        text: str,
        voice: VoiceType = "camila",
        speed: float = 1.0,
    ) -> Optional[bytes]:
        """
        Gera áudio a partir de texto.

        Args:
            text: Texto para converter em áudio
            voice: Voz a usar (camila, vitoria, ricardo, ana, carlos)
            speed: Velocidade (0.25 a 4.0, padrão 1.0)

        Returns:
            Bytes do áudio MP3 ou None se falhar
        """
        if not self.available or not self.client:
            logger.error("❌ Google TTS não configurado")
            return None

        if not text or not text.strip():
            logger.warning("⚠️ Google TTS: Texto vazio, ignorando")
            return None

        # Valida voz
        google_voice_name = AVAILABLE_VOICES.get(voice)
        if not google_voice_name:
            logger.warning(f"⚠️ Google TTS: Voz '{voice}' inválida, usando 'camila'")
            google_voice_name = AVAILABLE_VOICES["camila"]

        # Valida velocidade
        speed = max(0.25, min(4.0, speed))

        try:
            from google.cloud import texttospeech

            logger.info(f"🎙️ Google TTS: Gerando áudio com voz '{voice}' ({len(text)} chars)")

            # Configura entrada de texto
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Configura voz
            voice_params = texttospeech.VoiceSelectionParams(
                language_code="pt-BR",
                name=google_voice_name,
            )

            # Configura áudio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speed,
            )

            # Gera áudio
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config,
            )

            if response.audio_content:
                logger.info(f"✅ Google TTS: Áudio gerado ({len(response.audio_content)} bytes)")
                return response.audio_content
            else:
                logger.error("❌ Google TTS: Áudio vazio")
                return None

        except Exception as e:
            logger.error(f"❌ Google TTS: Erro ao gerar áudio: {e}")
            return None

    @staticmethod
    def get_voice_options() -> list:
        """Retorna opções de voz disponíveis com descrições."""
        return [
            {
                "id": "camila",
                "name": "Camila",
                "description": "Feminina, brasileira e natural (Recomendada)",
                "gender": "female",
                "recommended": True,
                "provider": "google",
            },
            {
                "id": "vitoria",
                "name": "Vitória",
                "description": "Feminina, brasileira e jovem",
                "gender": "female",
                "recommended": False,
                "provider": "google",
            },
            {
                "id": "ricardo",
                "name": "Ricardo",
                "description": "Masculina, brasileiro e profissional",
                "gender": "male",
                "recommended": False,
                "provider": "google",
            },
            {
                "id": "ana",
                "name": "Ana",
                "description": "Feminina, brasileira e clara (Econômica)",
                "gender": "female",
                "recommended": False,
                "provider": "google",
            },
            {
                "id": "carlos",
                "name": "Carlos",
                "description": "Masculina, brasileiro e claro (Econômico)",
                "gender": "male",
                "recommended": False,
                "provider": "google",
            },
        ]


# Instância singleton
_google_tts_service: Optional[GoogleTTSService] = None


def get_google_tts_service() -> GoogleTTSService:
    """Retorna instância singleton do serviço Google TTS."""
    global _google_tts_service
    if _google_tts_service is None:
        _google_tts_service = GoogleTTSService()
    return _google_tts_service
