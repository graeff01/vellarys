from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union


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
        max_tokens: int = 500,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Gera uma completude de chat com suporte a function calling.

        Args:
            messages: Lista de mensagens [{'role': 'user', 'content': '...'}]
            model: Nome do modelo (opcional)
            temperature: Criatividade (0.0 a 1.0)
            max_tokens: Limite de tokens na resposta
            tools: Lista de ferramentas disponíveis para function calling
            tool_choice: Controle de uso de tools:
                - "auto": modelo decide se usa tool
                - "none": não usa tools
                - "required": deve usar alguma tool
                - {"type": "function", "function": {"name": "..."}} : força tool específica

        Returns:
            Dict com:
            - 'content': str (resposta textual, pode ser None se tool_call)
            - 'tokens_used': int
            - 'tool_calls': List[Dict] ou None (lista de chamadas de função)
            - 'finish_reason': str ("stop", "tool_calls", etc)
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
