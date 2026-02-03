"""
SERVIÇO RAG PARA BASE DE CONHECIMENTO
======================================

Implementa busca semântica (RAG) em FAQ, documentos e regras de negócio.

Fluxo:
1. Cliente pergunta: "Como funciona o financiamento?"
2. Gera embedding da query (via OpenAI Embeddings API)
3. Busca por similaridade coseno no pgvector
4. Retorna top K FAQs/documentos mais relevantes
5. IA usa esse conhecimento para compor a resposta

Performance:
- Índice HNSW: ~1ms para buscar em 100k registros
- Embeddings: text-embedding-3-small (1536 dims, $0.02/1M tokens)
- Cache de hash evita regeneração desnecessária
"""

import hashlib
import logging
from typing import List, Dict, Optional, Any
from sqlalchemy import select, text, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.knowledge_embedding import KnowledgeEmbedding
from src.infrastructure.llm import LLMFactory

logger = logging.getLogger(__name__)


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

async def generate_embedding(text_content: str) -> Optional[List[float]]:
    """
    Gera embedding de um texto usando OpenAI Embeddings API.

    Modelo: text-embedding-3-small (1536 dimensões)
    Custo: $0.02 por 1M tokens
    """
    try:
        provider = LLMFactory.get_provider()

        # Chama API de embeddings
        embedding = await provider.generate_embeddings(text_content)

        if not embedding or len(embedding) != 1536:
            logger.error(f"Embedding inválido: {len(embedding) if embedding else 0} dimensões")
            return None

        return embedding

    except Exception as e:
        logger.error(f"Erro gerando embedding: {e}")
        return None


def compute_content_hash(title: str, content: str) -> str:
    """
    Calcula hash MD5 do conteúdo.
    Usado para detectar se precisa regenerar embedding.
    """
    full_content = f"{title or ''}|{content}"
    return hashlib.md5(full_content.encode()).hexdigest()


def build_searchable_text(title: str, content: str, metadata: Dict = None) -> str:
    """
    Constrói texto otimizado para embedding.

    Combina título e conteúdo de forma que maximize a relevância da busca.
    """
    parts = []

    if title:
        parts.append(f"Pergunta: {title}")

    if content:
        parts.append(f"Resposta: {content}")

    # Adiciona metadados relevantes
    if metadata:
        if metadata.get("category"):
            parts.append(f"Categoria: {metadata['category']}")
        if metadata.get("tags"):
            tags = metadata["tags"]
            if isinstance(tags, list):
                parts.append(f"Tags: {', '.join(tags)}")

    return "\n".join(parts)


# =============================================================================
# INDEXAÇÃO DE FAQ
# =============================================================================

async def index_faq_items(
    db: AsyncSession,
    tenant_id: int,
    faq_items: List[Dict],
    clear_existing: bool = False,
) -> Dict[str, int]:
    """
    Indexa itens do FAQ no banco de embeddings.

    Args:
        db: Sessão do banco de dados
        tenant_id: ID do tenant
        faq_items: Lista de {"question": "...", "answer": "...", "category": "..."}
        clear_existing: Se True, remove FAQs antigos antes de indexar

    Returns:
        Estatísticas: {"created": N, "updated": N, "skipped": N, "failed": N}
    """
    stats = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}

    if not faq_items:
        logger.info(f"📚 Nenhum FAQ para indexar (tenant {tenant_id})")
        return stats

    try:
        # Remove FAQs antigos se solicitado
        if clear_existing:
            await db.execute(
                delete(KnowledgeEmbedding)
                .where(KnowledgeEmbedding.tenant_id == tenant_id)
                .where(KnowledgeEmbedding.source_type == "faq")
            )
            await db.commit()
            logger.info(f"🗑️ FAQs antigos removidos (tenant {tenant_id})")

        for idx, item in enumerate(faq_items):
            question = (item.get("question") or "").strip()
            answer = (item.get("answer") or "").strip()
            category = item.get("category")

            # Valida item
            if not question or not answer:
                logger.warning(f"FAQ item {idx} inválido: falta pergunta ou resposta")
                stats["skipped"] += 1
                continue

            try:
                source_id = f"faq_{idx}"
                content_hash = compute_content_hash(question, answer)

                # Verifica se já existe
                result = await db.execute(
                    select(KnowledgeEmbedding)
                    .where(KnowledgeEmbedding.tenant_id == tenant_id)
                    .where(KnowledgeEmbedding.source_type == "faq")
                    .where(KnowledgeEmbedding.source_id == source_id)
                )
                existing = result.scalar_one_or_none()

                # Se existe e hash igual, pula (não mudou)
                if existing and existing.content_hash == content_hash:
                    logger.debug(f"FAQ {idx} não mudou, pulando")
                    stats["skipped"] += 1
                    continue

                # Monta texto para embedding
                metadata = {"index": idx}
                if category:
                    metadata["category"] = category

                searchable_text = build_searchable_text(question, answer, metadata)

                # Gera embedding
                embedding_vector = await generate_embedding(searchable_text)
                if not embedding_vector:
                    logger.error(f"Falha ao gerar embedding para FAQ {idx}")
                    stats["failed"] += 1
                    continue

                if existing:
                    # Atualiza existente
                    existing.title = question
                    existing.content = answer
                    existing.embedding = embedding_vector
                    existing.content_hash = content_hash
                    existing.metadata = metadata
                    existing.active = True
                    stats["updated"] += 1
                    logger.debug(f"FAQ {idx} atualizado")
                else:
                    # Cria novo
                    new_embedding = KnowledgeEmbedding(
                        tenant_id=tenant_id,
                        source_type="faq",
                        source_id=source_id,
                        title=question,
                        content=answer,
                        embedding=embedding_vector,
                        content_hash=content_hash,
                        metadata=metadata,
                    )
                    db.add(new_embedding)
                    stats["created"] += 1
                    logger.debug(f"FAQ {idx} criado")

                # Commit a cada item para não perder progresso
                await db.commit()

            except Exception as e:
                logger.error(f"Erro indexando FAQ item {idx}: {e}")
                stats["failed"] += 1
                await db.rollback()

        logger.info(f"📚 FAQ indexado (tenant {tenant_id}): {stats}")
        return stats

    except Exception as e:
        logger.error(f"Erro geral indexando FAQ: {e}")
        await db.rollback()
        return stats


async def index_document(
    db: AsyncSession,
    tenant_id: int,
    document_id: str,
    title: str,
    content: str,
    metadata: Dict = None,
) -> bool:
    """
    Indexa um documento na base de conhecimento.

    Args:
        document_id: ID único do documento
        title: Título do documento
        content: Conteúdo do documento
        metadata: Metadados adicionais (categoria, tags, etc)

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        content_hash = compute_content_hash(title, content)

        # Verifica se já existe
        result = await db.execute(
            select(KnowledgeEmbedding)
            .where(KnowledgeEmbedding.tenant_id == tenant_id)
            .where(KnowledgeEmbedding.source_type == "document")
            .where(KnowledgeEmbedding.source_id == document_id)
        )
        existing = result.scalar_one_or_none()

        # Se existe e hash igual, não precisa atualizar
        if existing and existing.content_hash == content_hash:
            logger.debug(f"Documento {document_id} não mudou")
            return True

        # Monta texto para embedding
        searchable_text = build_searchable_text(title, content, metadata)

        # Gera embedding
        embedding_vector = await generate_embedding(searchable_text)
        if not embedding_vector:
            logger.error(f"Falha ao gerar embedding para documento {document_id}")
            return False

        if existing:
            existing.title = title
            existing.content = content
            existing.embedding = embedding_vector
            existing.content_hash = content_hash
            existing.metadata = metadata or {}
            existing.active = True
        else:
            new_embedding = KnowledgeEmbedding(
                tenant_id=tenant_id,
                source_type="document",
                source_id=document_id,
                title=title,
                content=content,
                embedding=embedding_vector,
                content_hash=content_hash,
                metadata=metadata or {},
            )
            db.add(new_embedding)

        await db.commit()
        logger.info(f"📄 Documento indexado: {title[:50]}")
        return True

    except Exception as e:
        logger.error(f"Erro indexando documento: {e}")
        await db.rollback()
        return False


# =============================================================================
# BUSCA SEMÂNTICA (RAG)
# =============================================================================

async def search_knowledge(
    db: AsyncSession,
    tenant_id: int,
    query: str,
    top_k: int = 3,
    min_similarity: float = 0.6,
    source_types: List[str] = None,
) -> List[Dict]:
    """
    Busca conhecimento relevante para a query.

    Args:
        tenant_id: ID do tenant
        query: Pergunta/query do usuário
        top_k: Número máximo de resultados
        min_similarity: Similaridade mínima (0-1)
        source_types: Lista de tipos permitidos ('faq', 'document', 'rule')
                      Se None, busca em todos

    Returns:
        Lista de dicts com: id, title, content, similarity, source_type, metadata
    """
    try:
        # Gera embedding da query
        query_embedding = await generate_embedding(query)

        if not query_embedding:
            logger.error("Falha ao gerar embedding da query")
            return []

        # Monta filtro de source_type
        source_filter = ""
        if source_types:
            types_str = ", ".join([f"'{t}'" for t in source_types])
            source_filter = f"AND ke.source_type IN ({types_str})"

        # Converte embedding para formato pgvector (string com lista)
        # Formato: '[1.0,2.0,3.0,...]'
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

        # Query SQL com busca vetorial
        # Nota: asyncpg não suporta ::vector com named params, então usamos CAST
        sql = text(f"""
            SELECT
                ke.id,
                ke.title,
                ke.content,
                ke.source_type,
                ke.source_id,
                ke.metadata,
                1 - (ke.embedding <=> CAST(:query_embedding AS vector)) AS similarity
            FROM knowledge_embeddings ke
            WHERE ke.tenant_id = :tenant_id
                AND ke.active = true
                {source_filter}
                AND 1 - (ke.embedding <=> CAST(:query_embedding AS vector)) >= :min_similarity
            ORDER BY ke.embedding <=> CAST(:query_embedding AS vector) ASC
            LIMIT :top_k
        """)

        result = await db.execute(
            sql,
            {
                "query_embedding": embedding_str,
                "tenant_id": tenant_id,
                "min_similarity": min_similarity,
                "top_k": top_k,
            }
        )

        results = []
        for row in result:
            results.append({
                "id": row.id,
                "title": row.title,
                "content": row.content,
                "source_type": row.source_type,
                "source_id": row.source_id,
                "similarity": float(row.similarity),
                "metadata": row.metadata,
            })

        if results:
            logger.info(f"🔍 RAG: {len(results)} resultados para '{query[:50]}...' (min sim: {results[-1]['similarity']:.2f})")
        else:
            logger.debug(f"🔍 RAG: Nenhum resultado para '{query[:50]}...'")

        return results

    except Exception as e:
        logger.error(f"Erro na busca RAG: {e}")
        # Rollback para não corromper a sessão do banco
        # Sem isso, qualquer operação posterior (salvar mensagem, etc.) falha
        try:
            await db.rollback()
        except Exception:
            pass
        return []


# =============================================================================
# CONSTRUÇÃO DE CONTEXTO PARA PROMPT
# =============================================================================

def build_rag_context(results: List[Dict], max_chars: int = 2000) -> str:
    """
    Constrói contexto RAG para adicionar ao prompt da IA.
    Inclui citação de fontes.

    Args:
        results: Resultados da busca semântica
        max_chars: Tamanho máximo do contexto

    Returns:
        String formatada para adicionar ao prompt
    """
    if not results:
        return ""

    parts = [
        "📚 BASE DE CONHECIMENTO (use para responder):",
        ""
    ]

    total_chars = sum(len(p) for p in parts)

    for idx, item in enumerate(results, 1):
        source = item.get("source_type", "info")
        title = item.get("title", "")
        content = item.get("content", "")
        similarity = item.get("similarity", 0)

        # Formata a entrada
        entry_parts = []
        entry_parts.append(f"[{idx}] {source.upper()} (relevância: {similarity:.0%})")

        if title:
            entry_parts.append(f"   P: {title}")

        # Trunca conteúdo se muito longo
        if len(content) > 400:
            content = content[:400] + "..."
        entry_parts.append(f"   R: {content}")
        entry_parts.append("")

        entry_text = "\n".join(entry_parts)

        # Verifica se cabe no limite
        if total_chars + len(entry_text) > max_chars:
            parts.append(f"... (+{len(results) - idx + 1} resultados omitidos)")
            break

        parts.append(entry_text)
        total_chars += len(entry_text)

    parts.append("⚠️ Use estas informações para responder! Cite a fonte se relevante.")

    return "\n".join(parts)


# =============================================================================
# GESTÃO DE ÍNDICE
# =============================================================================

async def get_index_stats(db: AsyncSession, tenant_id: int) -> Dict[str, Any]:
    """
    Retorna estatísticas do índice de conhecimento.
    """
    try:
        # Total por tipo
        result = await db.execute(
            text("""
                SELECT source_type, COUNT(*) as count
                FROM knowledge_embeddings
                WHERE tenant_id = :tenant_id AND active = true
                GROUP BY source_type
            """),
            {"tenant_id": tenant_id}
        )

        by_type = {}
        total = 0
        for row in result:
            by_type[row.source_type] = row.count
            total += row.count

        return {
            "tenant_id": tenant_id,
            "total": total,
            "by_type": by_type,
        }

    except Exception as e:
        logger.error(f"Erro obtendo estatísticas: {e}")
        return {"tenant_id": tenant_id, "total": 0, "by_type": {}, "error": str(e)}


async def delete_by_source(
    db: AsyncSession,
    tenant_id: int,
    source_type: str,
    source_id: str = None,
) -> int:
    """
    Remove embeddings por fonte.

    Args:
        source_type: Tipo da fonte ('faq', 'document', etc)
        source_id: ID específico (se None, remove todos do tipo)

    Returns:
        Número de registros removidos
    """
    try:
        query = delete(KnowledgeEmbedding).where(
            KnowledgeEmbedding.tenant_id == tenant_id,
            KnowledgeEmbedding.source_type == source_type,
        )

        if source_id:
            query = query.where(KnowledgeEmbedding.source_id == source_id)

        result = await db.execute(query)
        await db.commit()

        deleted = result.rowcount
        logger.info(f"🗑️ Removidos {deleted} embeddings ({source_type}/{source_id or '*'})")

        return deleted

    except Exception as e:
        logger.error(f"Erro removendo embeddings: {e}")
        await db.rollback()
        return 0
