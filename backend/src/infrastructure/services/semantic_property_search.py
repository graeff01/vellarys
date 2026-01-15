"""
SERVIÇO DE BUSCA SEMÂNTICA - RAG com pgvector
==============================================

Implementa busca por similaridade usando embeddings.

Fluxo:
1. Cliente pergunta: "Quero apartamento perto de escolas boas"
2. Gera embedding da query (via OpenAI Embeddings API)
3. Busca por similaridade coseno no pgvector
4. Retorna top K imóveis mais relevantes
5. IA usa esses imóveis para compor a resposta

Performance:
- Índice HNSW: ~1ms para buscar em 100k registros
- Embeddings: text-embedding-3-small (1536 dims, $0.02/1M tokens)
"""

import hashlib
import logging
from typing import List, Dict, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Product
from src.domain.entities.property_embedding import PropertyEmbedding
from src.infrastructure.llm import LLMFactory

logger = logging.getLogger(__name__)


async def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Gera embedding de um texto usando OpenAI Embeddings API.
    
    Modelo: text-embedding-3-small (1536 dimensões)
    Custo: $0.02 por 1M tokens
    """
    try:
        provider = LLMFactory.get_provider()
        
        # Chama API de embeddings
        embedding = await provider.generate_embedding(text)
        
        if not embedding or len(embedding) != 1536:
            logger.error(f"Embedding inválido: {len(embedding) if embedding else 0} dimensõ es")
            return None
        
        return embedding
        
    except Exception as e:
        logger.error(f"Erro gerando embedding: {e}")
        return None


def compute_content_hash(product: Product) -> str:
    """
    Calcula hash MD5 do conteúdo relevante do produto.
    Usado para detectar se precisa regenerar embedding.
    """
    # Concatena todos os campos relevantes
    content_parts = [
        product.name or "",
        product.description or "",
        str(product.attributes or {}),
    ]
    
    content = "|".join(content_parts)
    return hashlib.md5(content.encode()).hexdigest()


def build_searchable_text(product: Product) -> str:
    """
    Constrói texto otimizado para embedding.
    
    Inclui:
    - Nome do produto
    - Descrição
    - Atributos relevantes (bairro, tipo, etc.)
    """
    parts = []
    
    # Nome
    if product.name:
        parts.append(f"Nome: {product.name}")
    
    # Descrição
    if product.description:
        parts.append(f"Descrição: {product.description}")
    
    # Atributos estruturados
    if product.attributes:
        attrs = product.attributes
        
        # Tipo de imóvel
        if attrs.get("tipo"):
            parts.append(f"Tipo: {attrs['tipo']}")
        
        # Localização
        if attrs.get("bairro"):
            parts.append(f"Bairro: {attrs['bairro']}")
        if attrs.get("cidade"):
            parts.append(f"Cidade: {attrs['cidade']}")
        
        # Características
        if attrs.get("quartos"):
            parts.append(f"{attrs['quartos']} quartos")
        if attrs.get("banheiros"):
            parts.append(f"{attrs['banheiros']} banheiros")
        if attrs.get("vagas"):
            parts.append(f"{attrs['vagas']} vagas")
        
        # Diferenciais
        if attrs.get("diferenciais"):
            difs = attrs['diferenciais']
            if isinstance(difs, list):
                parts.append(f"Diferenciais: {', '.join(difs)}")
            else:
                parts.append(f"Diferenciais: {difs}")
    
    return ". ".join(parts)


async def create_or_update_embedding(
    db: AsyncSession,
    product: Product,
) -> bool:
    """
    Cria ou atualiza embedding de um produto.
    
    - Verifica se embedding existe
    - Se content_hash mudou, regenera
    - Se não existe, cria novo
    """
    try:
        # Calcula hash do conteúdo atual
        current_hash = compute_content_hash(product)
        
        # Busca embedding existente
        result = await db.execute(
            select(PropertyEmbedding)
            .where(PropertyEmbedding.product_id == product.id)
        )
        existing = result.scalar_one_or_none()
        
        # Se existe e hash não mudou, não precisa regenerar
        if existing and existing.content_hash == current_hash:
            logger.debug(f"Embedding já atualizado para produto {product.id}")
            return True
        
        # Gera texto para embedding
        searchable_text = build_searchable_text(product)
        
        if not searchable_text or len(searchable_text) < 10:
            logger.warning(f"Texto insuficiente para produto {product.id}")
            return False
        
        # Gera embedding
        logger.info(f"Gerando embedding para: {product.name} ({len(searchable_text)} chars)")
        embedding_vector = await generate_embedding(searchable_text)
        
        if not embedding_vector:
            logger.error(f"Falha ao gerar embedding para produto {product.id}")
            return False
        
        # Cria ou atualiza
        if existing:
            # Atualiza
            existing.embedding = embedding_vector
            existing.content_hash = current_hash
            existing.metadata = {
                "text_length": len(searchable_text),
                "regenerated": True,
            }
            logger.info(f"✅ Embedding atualizado: {product.name}")
        else:
            # Cria novo
            new_embedding = PropertyEmbedding(
                tenant_id=product.tenant_id,
                product_id=product.id,
                embedding=embedding_vector,
                content_hash=current_hash,
                metadata={
                    "text_length": len(searchable_text),
                },
            )
            db.add(new_embedding)
            logger.info(f"✅ Embedding criado: {product.name}")
        
        await db.commit()
        return True
        
    except Exception as e:
        logger.error(f"Erro criando/atualizando embedding: {e}")
        await db.rollback()
        return False


async def search_similar_properties(
    db: AsyncSession,
    tenant_id: int,
    query: str,
    top_k: int = 5,
    min_similarity: float = 0.5,
) -> List[Dict]:
    """
    Busca imóveis similares usando busca vetorial.
    
    Args:
        tenant_id: ID do tenant
        query: Query do usuário ("apartamento perto de escolas")
        top_k: Número máximo de resultados
        min_similarity: Similaridade mínima (0-1, cosine similarity)
    
    Returns:
        Lista de dicts com product_id e similarity_score
    """
    try:
        # 1. Gera embedding da query
        query_embedding = await generate_embedding(query)
        
        if not query_embedding:
            logger.error("Falha ao gerar embedding da query")
            return []
        
        # 2. Busca por similaridade usando pgvector
        # Similaridade coseno: 1 - (embedding <=> query_embedding)
        # Onde <=> é o operador de distância coseno do pgvector
        
        sql = text("""
            SELECT 
                pe.product_id,
                p.name,
                p.description,
                p.attributes,
                1 - (pe.embedding <=> :query_embedding::vector) AS similarity
            FROM property_embeddings pe
            JOIN products p ON p.id = pe.product_id
            WHERE pe.tenant_id = :tenant_id
                AND p.active = true
                AND 1 - (pe.embedding <=> :query_embedding::vector) >= :min_similarity
            ORDER BY pe.embedding <=> :query_embedding::vector ASC
            LIMIT :top_k
        """)
        
        result = await db.execute(
            sql,
            {
                "query_embedding": str(query_embedding),
                "tenant_id": tenant_id,
                "min_similarity": min_similarity,
                "top_k": top_k,
            }
        )
        
        results = []
        for row in result:
            results.append({
                "product_id": row.product_id,
                "name": row.name,
                "description": row.description,
                "attributes": row.attributes,
                "similarity_score": float(row.similarity),
            })
        
        logger.info(f"🔍 Busca semântica: {len(results)} resultados para '{query[:50]}...'")
        
        return results
        
    except Exception as e:
        logger.error(f"Erro na busca semântica: {e}")
        return []


async def bulk_generate_embeddings(
    db: AsyncSession,
    tenant_id: int,
    force_regenerate: bool = False,
) -> Dict[str, int]:
    """
    Gera embeddings para todos os produtos de um tenant.
    
    Útil para:
    - Primeira configuração
    - Re-indexação completa
    
    Returns:
        Dict com estatísticas: created, updated, failed, skipped
    """
    stats = {"created": 0, "updated": 0, "failed": 0, "skipped": 0}
    
    try:
        # Busca todos os produtos ativos
        result = await db.execute(
            select(Product)
            .where(Product.tenant_id == tenant_id)
            .where(Product.active == True)
        )
        products = result.scalars().all()
        
        logger.info(f"📦 Gerando embeddings para {len(products)} produtos...")
        
        for idx, product in enumerate(products, 1):
            logger.info(f"[{idx}/{len(products)}] Processando: {product.name}")
            
            # Verifica se precisa gerar
            if not force_regenerate:
                current_hash = compute_content_hash(product)
                existing_result = await db.execute(
                    select(PropertyEmbedding)
                    .where(PropertyEmbedding.product_id == product.id)
                )
                existing = existing_result.scalar_one_or_none()
                
                if existing and existing.content_hash == current_hash:
                    logger.debug(f"  ⏭️ Pulando (já atualizado)")
                    stats["skipped"] += 1
                    continue
            
            # Gera/atualiza
            success = await create_or_update_embedding(db, product)
            
            if success:
                # Check if was update or create
                check_result = await db.execute(
                    select(PropertyEmbedding.id)
                    .where(PropertyEmbedding.product_id == product.id)
                )
                if check_result.scalar():
                    stats["updated"] += 1
                else:
                    stats["created"] += 1
            else:
                stats["failed"] += 1
        
        logger.info(f"✅ Embeddings gerados: {stats}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Erro no bulk generation: {e}")
        return stats
