from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class LLMProvider(ABC):
    """
    Interface abstrata para provedores de LLM.
    Permite trocar entre OpenAI, Anthropic, etc. sem afetar o código de negócio.
    """

    @abstractmethod
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """
        Gera uma completude de chat.
        
        Args:
            messages: Lista de mensagens [{'role': 'user', 'content': '...'}]
            model: Nome do modelo (opcional)
            temperature: Criatividade (0.0 a 1.0)
            max_tokens: Limite de tokens na resposta
            
        Returns:
            Dict com 'content' (str) e 'tokens_used' (int)
        """
    @abstractmethod
    async def transcribe(self, audio_file_path: str, prompt: Optional[str] = None) -> str:
        """
        Transcreve um arquivo de áudio para texto.
        
        Args:
            audio_file_path: Caminho local do arquivo de áudio.
            
        Returns:
            Texto transcrito.
        """
        pass

    @abstractmethod
    async def generate_embeddings(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """
        Gera embeddings vetoriais para um texto.
        """
        pass

    @abstractmethod
    async def analyze_image(self, image_url: str, prompt: str) -> str:
        """
        Analisa uma imagem via URL e retorna uma descrição/resposta.
        """
        pass
