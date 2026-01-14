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
        pass
