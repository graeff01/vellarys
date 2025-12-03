"""
ROTAS DE EXPORTAÇÃO
====================

Endpoints para exportar dados em diferentes formatos.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import io

from src.infrastructure.database import get_db
from src.domain.entities import Tenant, User
from src.api.dependencies import get_current_user
from src.infrastructure.services.export_service import (
    export_to_excel,
    export_to_csv,
    export_to_pdf,
)

router = APIRouter(prefix="/export", tags=["Export"])


class ExportRequest(BaseModel):
    """Request para exportação."""
    period: str = "month"  # week, month, quarter, year, all, custom
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD
    include_metrics: bool = True
    include_leads: bool = True


def get_date_range(period: str, start_date: str = None, end_date: str = None):
    """Calcula range de datas baseado no período."""
    now = datetime.now()
    
    if period == "custom" and start_date and end_date:
        return (
            datetime.strptime(start_date, "%Y-%m-%d"),
            datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        )
    elif period == "week":
        start = now - timedelta(days=7)
    elif period == "month":
        start = now - timedelta(days=30)
    elif period == "quarter":
        start = now - timedelta(days=90)
    elif period == "year":
        start = now - timedelta(days=365)
    else:  # all
        return None, None
    
    return start, now


@router.get("/excel")
async def export_excel(
    period: str = Query("month", description="Período: week, month, quarter, year, all, custom"),
    start_date: Optional[str] = Query(None, description="Data início (YYYY-MM-DD) para período custom"),
    end_date: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD) para período custom"),
    include_metrics: bool = Query(True, description="Incluir aba de métricas"),
    include_leads: bool = Query(True, description="Incluir aba de leads"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exporta dados para Excel (.xlsx).
    
    - Múltiplas abas: Resumo e Leads
    - Formatação profissional
    - Filtros e formatação condicional
    """
    
    # Busca tenant do usuário
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # Calcula datas
    start, end = get_date_range(period, start_date, end_date)
    
    try:
        # Gera Excel
        excel_bytes = await export_to_excel(
            db=db,
            tenant=tenant,
            start_date=start,
            end_date=end,
            include_metrics=include_metrics,
            include_leads=include_leads,
        )
        
        # Nome do arquivo
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"velaris_{tenant.slug}_{date_str}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar Excel: {str(e)}")


@router.get("/csv")
async def export_csv(
    period: str = Query("month", description="Período: week, month, quarter, year, all, custom"),
    start_date: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exporta leads para CSV.
    
    - Formato simples para importação em outros sistemas
    - Separador: ponto e vírgula (;)
    - Encoding: UTF-8 com BOM
    """
    
    # Busca tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # Calcula datas
    start, end = get_date_range(period, start_date, end_date)
    
    try:
        # Gera CSV
        csv_bytes = await export_to_csv(
            db=db,
            tenant=tenant,
            start_date=start,
            end_date=end,
        )
        
        # Nome do arquivo
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"velaris_{tenant.slug}_{date_str}.csv"
        
        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar CSV: {str(e)}")


@router.get("/pdf")
async def export_pdf(
    period: str = Query("month", description="Período: week, month, quarter, year, all, custom"),
    start_date: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    include_leads: bool = Query(True, description="Incluir lista de leads"),
    max_leads: int = Query(50, description="Máximo de leads na lista (1-100)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exporta relatório para PDF.
    
    - Visual profissional para apresentações
    - Métricas destacadas
    - Lista resumida de leads
    """
    
    # Busca tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # Calcula datas
    start, end = get_date_range(period, start_date, end_date)
    
    # Limita max_leads
    max_leads = min(max(1, max_leads), 100)
    
    try:
        # Gera PDF
        pdf_bytes = await export_to_pdf(
            db=db,
            tenant=tenant,
            start_date=start,
            end_date=end,
            include_leads=include_leads,
            max_leads=max_leads,
        )
        
        # Nome do arquivo
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"relatorio_velaris_{tenant.slug}_{date_str}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")


@router.get("/preview")
async def export_preview(
    period: str = Query("month", description="Período para preview"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna preview dos dados que serão exportados.
    
    Útil para mostrar ao usuário o que será incluído no export.
    """
    from src.infrastructure.services.export_service import (
        get_leads_for_export,
        get_metrics_for_export,
    )
    
    # Busca tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # Calcula datas
    start, end = get_date_range(period)
    
    # Busca dados
    leads = await get_leads_for_export(db, tenant.id, start, end)
    metrics = await get_metrics_for_export(db, tenant.id, start, end)
    
    return {
        "period": period,
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
        "total_leads": len(leads),
        "metrics": metrics,
        "sample_leads": leads[:5],  # Apenas 5 leads como amostra
    }