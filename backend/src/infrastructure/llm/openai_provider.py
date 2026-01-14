import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from src.config import get_settings
from .interface import LLMProvider

logger = logging.getLogger(__name__)
settings = get_settings()

class OpenAIProvider(LLMProvider):
    """
    Implementação do provedor OpenAI usando a lib oficial.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.openai_api_key
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.default_model = settings.openai_model

    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        try:
            response = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return {
                "content": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
        except Exception as e:
            logger.error(f"Erro na chamada OpenAI: {e}")
            raise e

    async def transcribe(self, audio_file_path: str, prompt: Optional[str] = None) -> str:
        """Transcreve áudio usando OpenAI Whisper."""
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    prompt=prompt,
                    response_format="text"
                )
            return transcript
        except Exception as e:
            logger.error(f"Erro na transcrição Whisper: {e}")
            raise e

    async def generate_embeddings(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """Gera embeddings usando OpenAI API."""
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erro ao gerar embeddings OpenAI: {e}")
            raise e

    async def analyze_image(self, image_url: str, prompt: str) -> str:
        """Analisa imagem usando GPT-4o Vision."""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini", # Mini agora suporta visão e é mais barato/rápido
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                max_tokens=300,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erro ao analisar imagem OpenAI: {e}")
            return f"[Erro na análise de imagem: {e}]"
