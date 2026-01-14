import logging
import json
import os
import asyncio
import numpy as np
from typing import List, Dict, Any, Optional
from src.infrastructure.llm.factory import LLMFactory

logger = logging.getLogger(__name__)

INDEX_PATH = os.path.join(os.getcwd(), "storage", "property_embeddings.json")

class SemanticSearchService:
    """
    Serviço de Busca Semântica usando Embeddings e Similaridade de Cosseno.
    Permite encontrar imóveis por intenção/contexto.
    """
    
    def __init__(self):
        self.index: Dict[str, List[float]] = {}
        self.properties: Dict[str, Dict] = {}
        self._load_index()

    def _load_index(self):
        """Carrega o índice do disco."""
        try:
            if os.path.exists(INDEX_PATH):
                with open(INDEX_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.index = data.get("embeddings", {})
                    self.properties = data.get("properties", {})
                logger.info(f"💾 Índice semântico carregado: {len(self.index)} itens")
            else:
                logger.info("🆕 Novo índice semântico será criado.")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar índice: {e}")

    def _save_index(self):
        """Salva o índice no disco."""
        try:
            os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
            with open(INDEX_PATH, 'w', encoding='utf-8') as f:
                json.dump({
                    "embeddings": self.index,
                    "properties": self.properties
                }, f, ensure_ascii=False, indent=2)
            logger.info("✅ Índice semântico salvo com sucesso.")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar índice: {e}")

    async def index_properties(self, properties: List[Dict]):
        """
        Gera embeddings para uma lista de imóveis e atualiza o índice.
        """
        provider = LLMFactory.get_provider()
        updated = False
        
        for prop in properties:
            codigo = str(prop.get("codigo"))
            if not codigo: continue
            
            # Se já indexado, pula (poderíamos adicionar lógica de hashes para mudar se a descrição mudar)
            if codigo in self.index:
                continue
                
            # Prepara texto para embedding (Título + Tipo + Bairro + Descrição)
            text_to_embed = f"{prop.get('titulo', '')} {prop.get('tipo', '')} em {prop.get('regiao', '')}. {prop.get('descricao', '')}"
            text_to_embed = text_to_embed.strip()
            
            if not text_to_embed: continue
            
            try:
                logger.info(f"🧠 Gerando embedding para imóvel {codigo}...")
                embedding = await provider.generate_embeddings(text_to_embed)
                self.index[codigo] = embedding
                self.properties[codigo] = prop
                updated = True
                
                # Pequeno delay para evitar rate limit massivo se for carga inicial grande
                # await asyncio.sleep(0.05) 
            except Exception as e:
                logger.error(f"❌ Falha ao indexar imóvel {codigo}: {e}")
        
        if updated:
            self._save_index()

    async def search(self, query: str, limit: int = 5, min_score: float = 0.7) -> List[Dict]:
        """
        Busca imóveis semanticamente similares à query.
        """
        if not self.index:
            logger.warning("⚠️ Busca semântica falhou: índice vazio.")
            return []
            
        try:
            provider = LLMFactory.get_provider()
            query_embedding = await provider.generate_embeddings(query)
            query_vec = np.array(query_embedding)
            
            results = []
            
            for codigo, embedding in self.index.items():
                prop_vec = np.array(embedding)
                
                # Similaridade de Cosseno = (A . B) / (||A|| * ||B||)
                norm_a = np.linalg.norm(query_vec)
                norm_b = np.linalg.norm(prop_vec)
                
                if norm_a == 0 or norm_b == 0:
                    score = 0
                else:
                    score = np.dot(query_vec, prop_vec) / (norm_a * norm_b)
                
                if score >= min_score:
                    prop_data = self.properties[codigo].copy()
                    prop_data["semantic_score"] = float(score)
                    results.append(prop_data)
            
            # Ordena por score descendente
            results.sort(key=lambda x: x["semantic_score"], reverse=True)
            
            logger.info(f"🔎 Busca semântica: '{query}' -> {len(results[:limit])} resultados")
            return results[:limit]
            
        except Exception as e:
            logger.error(f"❌ Erro na busca semântica: {e}")
            return []

# Singleton para uso global
semantic_search = SemanticSearchService()
