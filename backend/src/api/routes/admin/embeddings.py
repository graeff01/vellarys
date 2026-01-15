"""
ENDPOINT ADMIN - Gerenciamento de Embeddings
==========================================

Endpoints para:
- Gerar embeddings em massa
- Buscar imóveis semanticamente
- Status da indexação
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.infrastructure.database import get_db
from src.infrastructure.services.semantic_property_search import (
    bulk_generate_embeddings,
    search_similar_properties,
    create_or_update_embedding,
)
from src.domain.entities import Product
from src.api.dependencies import get_current_user_or_superadmin
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/embeddings", tags=["Admin - Embeddings"])


class BulkGenerateRequest(BaseModel):
    tenant_id: int
    force_regenerate: bool = False


class SearchRequest(BaseModel):
    tenant_id: int
    query: str
    top_k: int = 5


@router.post("/bulk-generate")
async def bulk_generate(
    request: BulkGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_or_superadmin),
):
    """
    Gera embeddings para todos os produtos de um tenant.
    
    **WARNING:** Pode demorar vários minutos para grandes catálogos!
    """
    try:
        stats = await bulk_generate_embeddings(
            db=db,
            tenant_id=request.tenant_id,
            force_regenerate=request.force_regenerate,
        )
        
        return {
            "success": True,
            "message": f"Embeddings gerados/atualizados",
            "stats": stats,
        }
        
    except Exception as e:
        logger.error(f"Erro no bulk generate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def semantic_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_or_superadmin),
):
    """
    Testa busca semântica de imóveis.
    
    Exemplo de query:
    - "Apartamento perto de escolas boas"
    - "Casa com quintal grande para cachorro"
    - "Imóvel moderno perto do mar"
    """
    try:
        results = await search_similar_properties(
            db=db,
            tenant_id=request.tenant_id,
            query=request.query,
            top_k=request.top_k,
        )
        
        return {
            "success": True,
            "query": request.query,
            "results_count": len(results),
            "results": results,
        }
        
    except Exception as e:
        logger.error(f"Erro na busca semântica: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-single/{product_id}")
async def generate_single(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_or_superadmin),
):
    """Gera/atualiza embedding de um único produto."""
    try:
        # Busca produto
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        # Gera embedding
        success = await create_or_update_embedding(db, product)
        
        if success:
            return {
                "success": True,
                "message": f"Embedding gerado para: {product.name}",
                "product_id": product_id,
            }
        else:
            raise HTTPException(status_code=500, detail="Falha ao gerar embedding")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro gerando embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{tenant_id}")
async def indexing_status(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_or_superadmin),
):
    """Verifica status da indexação de embeddings."""
    try:
        from sqlalchemy import func
        from src.domain.entities.property_embedding import PropertyEmbedding
        
        # Conta produtos totais
        result = await db.execute(
            select(func.count(Product.id))
            .where(Product.tenant_id == tenant_id)
            .where(Product.active == True)
        )
        total_products = result.scalar() or 0
        
        # Conta embeddings existentes
        result = await db.execute(
            select(func.count(PropertyEmbedding.id))
            .where(PropertyEmbedding.tenant_id == tenant_id)
        )
        total_embeddings = result.scalar() or 0
        
        coverage_pct = (total_embeddings / total_products * 100) if total_products > 0 else 0
        
        return {
            "tenant_id": tenant_id,
            "total_products": total_products,
            "total_embeddings": total_embeddings,
            "coverage_percentage": round(coverage_pct, 2),
            "status": "complete" if coverage_pct >= 100 else "partial",
        }
        
    except Exception as e:
        logger.error(f"Erro verificando status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
