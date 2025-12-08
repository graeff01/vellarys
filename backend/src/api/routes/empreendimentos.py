"""
ROTAS: EMPREENDIMENTOS
=======================

CRUD completo para gerenciar empreendimentos imobiliários.
Disponível APENAS para tenants com nicho "realestate" ou "imobiliaria".

Quando um lead envia mensagem contendo gatilhos do empreendimento,
a IA carrega automaticamente as informações e segue fluxo específico.
"""

import re
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import User, Tenant, Seller, Empreendimento
from src.api.dependencies import get_current_user, get_current_tenant


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/empreendimentos", tags=["Empreendimentos"])


# ==========================================
# CONSTANTES
# ==========================================

# Nichos que podem usar empreendimentos
NICHOS_IMOBILIARIOS = ["realestate", "imobiliaria", "real_estate", "imobiliario"]


# ==========================================
# SCHEMAS (Pydantic)
# ==========================================

class EmpreendimentoCreate(BaseModel):
    """Schema para criar empreendimento."""
    
    # Básico
    nome: str = Field(..., min_length=2, max_length=200)
    status: str = Field(default="lancamento")  # lancamento, em_obras, pronto_para_morar
    url_landing_page: Optional[str] = None
    imagem_destaque: Optional[str] = None
    
    # Gatilhos
    gatilhos: List[str] = Field(default_factory=list)
    prioridade: int = Field(default=0, ge=0, le=100)
    
    # Localização
    endereco: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = Field(None, max_length=2)
    cep: Optional[str] = Field(None, max_length=10)
    descricao_localizacao: Optional[str] = None
    
    # Características
    descricao: Optional[str] = None
    tipologias: List[str] = Field(default_factory=list)
    metragem_minima: Optional[int] = Field(None, ge=0)
    metragem_maxima: Optional[int] = Field(None, ge=0)
    torres: Optional[int] = Field(None, ge=0)
    andares: Optional[int] = Field(None, ge=0)
    unidades_por_andar: Optional[int] = Field(None, ge=0)
    total_unidades: Optional[int] = Field(None, ge=0)
    vagas_minima: Optional[int] = Field(None, ge=0)
    vagas_maxima: Optional[int] = Field(None, ge=0)
    previsao_entrega: Optional[str] = None
    
    # Valores
    preco_minimo: Optional[float] = Field(None, ge=0)
    preco_maximo: Optional[float] = Field(None, ge=0)
    aceita_financiamento: bool = True
    aceita_fgts: bool = True
    aceita_permuta: bool = False
    aceita_consorcio: bool = False
    condicoes_especiais: Optional[str] = None
    
    # Lazer e diferenciais
    itens_lazer: List[str] = Field(default_factory=list)
    diferenciais: List[str] = Field(default_factory=list)
    
    # Qualificação
    perguntas_qualificacao: List[str] = Field(default_factory=list)
    instrucoes_ia: Optional[str] = None
    
    # Destino leads
    vendedor_id: Optional[int] = None
    metodo_distribuicao: Optional[str] = None  # round_robin, especifico, gestor
    notificar_gestor: bool = False
    whatsapp_notificacao: Optional[str] = None


class EmpreendimentoUpdate(BaseModel):
    """Schema para atualizar empreendimento."""
    
    # Básico
    nome: Optional[str] = Field(None, min_length=2, max_length=200)
    status: Optional[str] = None
    url_landing_page: Optional[str] = None
    imagem_destaque: Optional[str] = None
    ativo: Optional[bool] = None
    
    # Gatilhos
    gatilhos: Optional[List[str]] = None
    prioridade: Optional[int] = Field(None, ge=0, le=100)
    
    # Localização
    endereco: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = Field(None, max_length=2)
    cep: Optional[str] = Field(None, max_length=10)
    descricao_localizacao: Optional[str] = None
    
    # Características
    descricao: Optional[str] = None
    tipologias: Optional[List[str]] = None
    metragem_minima: Optional[int] = Field(None, ge=0)
    metragem_maxima: Optional[int] = Field(None, ge=0)
    torres: Optional[int] = Field(None, ge=0)
    andares: Optional[int] = Field(None, ge=0)
    unidades_por_andar: Optional[int] = Field(None, ge=0)
    total_unidades: Optional[int] = Field(None, ge=0)
    vagas_minima: Optional[int] = Field(None, ge=0)
    vagas_maxima: Optional[int] = Field(None, ge=0)
    previsao_entrega: Optional[str] = None
    
    # Valores
    preco_minimo: Optional[float] = Field(None, ge=0)
    preco_maximo: Optional[float] = Field(None, ge=0)
    aceita_financiamento: Optional[bool] = None
    aceita_fgts: Optional[bool] = None
    aceita_permuta: Optional[bool] = None
    aceita_consorcio: Optional[bool] = None
    condicoes_especiais: Optional[str] = None
    
    # Lazer e diferenciais
    itens_lazer: Optional[List[str]] = None
    diferenciais: Optional[List[str]] = None
    
    # Qualificação
    perguntas_qualificacao: Optional[List[str]] = None
    instrucoes_ia: Optional[str] = None
    
    # Destino leads
    vendedor_id: Optional[int] = None
    metodo_distribuicao: Optional[str] = None
    notificar_gestor: Optional[bool] = None
    whatsapp_notificacao: Optional[str] = None


class EmpreendimentoResponse(BaseModel):
    """Schema de resposta do empreendimento."""
    id: int
    nome: str
    slug: str
    status: str
    ativo: bool
    gatilhos: List[str]
    cidade: Optional[str]
    bairro: Optional[str]
    tipologias: List[str]
    faixa_preco: str
    total_leads: int
    leads_qualificados: int
    vendedor_nome: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


# ==========================================
# HELPERS
# ==========================================

def generate_slug(nome: str) -> str:
    """Gera slug a partir do nome."""
    slug = nome.lower().strip()
    slug = re.sub(r'[àáâãäå]', 'a', slug)
    slug = re.sub(r'[èéêë]', 'e', slug)
    slug = re.sub(r'[ìíîï]', 'i', slug)
    slug = re.sub(r'[òóôõö]', 'o', slug)
    slug = re.sub(r'[ùúûü]', 'u', slug)
    slug = re.sub(r'[ç]', 'c', slug)
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug


def get_tenant_niche(tenant: Tenant) -> str:
    """Extrai o nicho do tenant das settings."""
    settings = tenant.settings or {}
    
    # Tenta formato novo
    basic = settings.get("basic", {})
    if basic.get("niche"):
        return basic["niche"]
    
    # Tenta formato antigo
    return settings.get("niche", "services")


def is_nicho_imobiliario(tenant: Tenant) -> bool:
    """Verifica se o tenant é do nicho imobiliário."""
    niche = get_tenant_niche(tenant)
    return niche.lower() in NICHOS_IMOBILIARIOS


def format_faixa_preco(preco_min: Optional[float], preco_max: Optional[float]) -> str:
    """Formata a faixa de preço para exibição."""
    if preco_min and preco_max:
        return f"R$ {preco_min:,.0f} a R$ {preco_max:,.0f}".replace(",", ".")
    elif preco_min:
        return f"A partir de R$ {preco_min:,.0f}".replace(",", ".")
    elif preco_max:
        return f"Até R$ {preco_max:,.0f}".replace(",", ".")
    return "Consulte-nos"


# ==========================================
# VERIFICAÇÃO DE ACESSO
# ==========================================

async def verify_imobiliario_access(tenant: Tenant):
    """Verifica se o tenant tem acesso a empreendimentos."""
    if not is_nicho_imobiliario(tenant):
        raise HTTPException(
            status_code=403,
            detail="Recurso disponível apenas para o nicho imobiliário. "
                   "Altere o nicho nas configurações para 'Imobiliário'."
        )


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/check-access")
async def check_empreendimentos_access(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    Verifica se o tenant tem acesso ao módulo de empreendimentos.
    Usado pelo frontend para mostrar/ocultar a aba.
    """
    niche = get_tenant_niche(tenant)
    has_access = is_nicho_imobiliario(tenant)
    
    return {
        "has_access": has_access,
        "niche": niche,
        "allowed_niches": NICHOS_IMOBILIARIOS,
        "message": "Acesso liberado" if has_access else "Disponível apenas para imobiliárias"
    }


@router.get("/stats")
async def empreendimentos_stats(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna estatísticas gerais dos empreendimentos.
    """
    await verify_imobiliario_access(tenant)
    
    # Total de empreendimentos
    total_result = await db.execute(
        select(func.count(Empreendimento.id))
        .where(Empreendimento.tenant_id == tenant.id)
    )
    total = total_result.scalar() or 0
    
    # Empreendimentos ativos
    ativos_result = await db.execute(
        select(func.count(Empreendimento.id))
        .where(Empreendimento.tenant_id == tenant.id)
        .where(Empreendimento.ativo == True)
    )
    ativos = ativos_result.scalar() or 0
    
    # Total de leads de empreendimentos
    leads_result = await db.execute(
        select(func.sum(Empreendimento.total_leads))
        .where(Empreendimento.tenant_id == tenant.id)
    )
    total_leads = leads_result.scalar() or 0
    
    # Leads qualificados
    qualificados_result = await db.execute(
        select(func.sum(Empreendimento.leads_qualificados))
        .where(Empreendimento.tenant_id == tenant.id)
    )
    leads_qualificados = qualificados_result.scalar() or 0
    
    # Por status
    status_result = await db.execute(
        select(Empreendimento.status, func.count(Empreendimento.id))
        .where(Empreendimento.tenant_id == tenant.id)
        .group_by(Empreendimento.status)
    )
    por_status = {row[0]: row[1] for row in status_result.all()}
    
    return {
        "total": total,
        "ativos": ativos,
        "inativos": total - ativos,
        "total_leads": total_leads,
        "leads_qualificados": leads_qualificados,
        "taxa_qualificacao": round((leads_qualificados / total_leads * 100), 1) if total_leads > 0 else 0,
        "por_status": {
            "lancamento": por_status.get("lancamento", 0),
            "em_obras": por_status.get("em_obras", 0),
            "pronto_para_morar": por_status.get("pronto_para_morar", 0),
        }
    }


@router.get("")
async def list_empreendimentos(
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    status: Optional[str] = Query(None, description="Filtrar por status do empreendimento"),
    search: Optional[str] = Query(None, description="Buscar por nome ou bairro"),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista todos os empreendimentos do tenant.
    """
    await verify_imobiliario_access(tenant)
    
    query = select(Empreendimento).where(Empreendimento.tenant_id == tenant.id)
    
    if ativo is not None:
        query = query.where(Empreendimento.ativo == ativo)
    
    if status:
        query = query.where(Empreendimento.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Empreendimento.nome.ilike(search_term),
                Empreendimento.bairro.ilike(search_term),
                Empreendimento.cidade.ilike(search_term),
            )
        )
    
    query = query.order_by(Empreendimento.prioridade.desc(), Empreendimento.nome)
    
    result = await db.execute(query)
    empreendimentos = result.scalars().all()
    
    # Busca nomes dos vendedores
    vendedor_ids = [e.vendedor_id for e in empreendimentos if e.vendedor_id]
    vendedores_map = {}
    
    if vendedor_ids:
        vendedores_result = await db.execute(
            select(Seller.id, Seller.name).where(Seller.id.in_(vendedor_ids))
        )
        vendedores_map = {row[0]: row[1] for row in vendedores_result.all()}
    
    return {
        "empreendimentos": [
            {
                "id": e.id,
                "nome": e.nome,
                "slug": e.slug,
                "status": e.status,
                "status_label": {
                    "lancamento": "Lançamento",
                    "em_obras": "Em Obras",
                    "pronto_para_morar": "Pronto para Morar",
                }.get(e.status, e.status),
                "ativo": e.ativo,
                "url_landing_page": e.url_landing_page,
                "imagem_destaque": e.imagem_destaque,
                "gatilhos": e.gatilhos or [],
                "prioridade": e.prioridade,
                "endereco": e.endereco,
                "bairro": e.bairro,
                "cidade": e.cidade,
                "estado": e.estado,
                "tipologias": e.tipologias or [],
                "faixa_preco": format_faixa_preco(e.preco_minimo, e.preco_maximo),
                "preco_minimo": e.preco_minimo,
                "preco_maximo": e.preco_maximo,
                "previsao_entrega": e.previsao_entrega,
                "total_leads": e.total_leads,
                "leads_qualificados": e.leads_qualificados,
                "leads_convertidos": e.leads_convertidos,
                "vendedor_id": e.vendedor_id,
                "vendedor_nome": vendedores_map.get(e.vendedor_id),
                "notificar_gestor": e.notificar_gestor,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in empreendimentos
        ],
        "total": len(empreendimentos),
    }


@router.post("")
async def create_empreendimento(
    payload: EmpreendimentoCreate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Cria um novo empreendimento.
    """
    await verify_imobiliario_access(tenant)
    
    # Gera slug
    slug = generate_slug(payload.nome)
    
    # Verifica se já existe com esse slug
    result = await db.execute(
        select(Empreendimento)
        .where(Empreendimento.tenant_id == tenant.id)
        .where(Empreendimento.slug == slug)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Adiciona sufixo numérico
        count_result = await db.execute(
            select(func.count(Empreendimento.id))
            .where(Empreendimento.tenant_id == tenant.id)
            .where(Empreendimento.slug.like(f"{slug}%"))
        )
        count = count_result.scalar() or 0
        slug = f"{slug}-{count + 1}"
    
    # Valida vendedor (se informado)
    if payload.vendedor_id:
        vendedor_result = await db.execute(
            select(Seller)
            .where(Seller.id == payload.vendedor_id)
            .where(Seller.tenant_id == tenant.id)
        )
        if not vendedor_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Vendedor não encontrado")
    
    # Cria empreendimento
    empreendimento = Empreendimento(
        tenant_id=tenant.id,
        nome=payload.nome,
        slug=slug,
        status=payload.status,
        url_landing_page=payload.url_landing_page,
        imagem_destaque=payload.imagem_destaque,
        gatilhos=payload.gatilhos,
        prioridade=payload.prioridade,
        endereco=payload.endereco,
        bairro=payload.bairro,
        cidade=payload.cidade,
        estado=payload.estado,
        cep=payload.cep,
        descricao_localizacao=payload.descricao_localizacao,
        descricao=payload.descricao,
        tipologias=payload.tipologias,
        metragem_minima=payload.metragem_minima,
        metragem_maxima=payload.metragem_maxima,
        torres=payload.torres,
        andares=payload.andares,
        unidades_por_andar=payload.unidades_por_andar,
        total_unidades=payload.total_unidades,
        vagas_minima=payload.vagas_minima,
        vagas_maxima=payload.vagas_maxima,
        previsao_entrega=payload.previsao_entrega,
        preco_minimo=payload.preco_minimo,
        preco_maximo=payload.preco_maximo,
        aceita_financiamento=payload.aceita_financiamento,
        aceita_fgts=payload.aceita_fgts,
        aceita_permuta=payload.aceita_permuta,
        aceita_consorcio=payload.aceita_consorcio,
        condicoes_especiais=payload.condicoes_especiais,
        itens_lazer=payload.itens_lazer,
        diferenciais=payload.diferenciais,
        perguntas_qualificacao=payload.perguntas_qualificacao,
        instrucoes_ia=payload.instrucoes_ia,
        vendedor_id=payload.vendedor_id,
        metodo_distribuicao=payload.metodo_distribuicao,
        notificar_gestor=payload.notificar_gestor,
        whatsapp_notificacao=payload.whatsapp_notificacao,
    )
    
    db.add(empreendimento)
    await db.commit()
    await db.refresh(empreendimento)
    
    logger.info(f"Empreendimento criado: {empreendimento.nome} (tenant: {tenant.slug})")
    
    return {
        "success": True,
        "message": "Empreendimento criado com sucesso",
        "empreendimento": {
            "id": empreendimento.id,
            "nome": empreendimento.nome,
            "slug": empreendimento.slug,
        }
    }


@router.get("/{empreendimento_id}")
async def get_empreendimento(
    empreendimento_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna detalhes completos de um empreendimento.
    """
    await verify_imobiliario_access(tenant)
    
    result = await db.execute(
        select(Empreendimento)
        .where(Empreendimento.id == empreendimento_id)
        .where(Empreendimento.tenant_id == tenant.id)
    )
    empreendimento = result.scalar_one_or_none()
    
    if not empreendimento:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado")
    
    # Busca nome do vendedor
    vendedor_nome = None
    if empreendimento.vendedor_id:
        vendedor_result = await db.execute(
            select(Seller.name).where(Seller.id == empreendimento.vendedor_id)
        )
        vendedor_nome = vendedor_result.scalar_one_or_none()
    
    return {
        "id": empreendimento.id,
        "nome": empreendimento.nome,
        "slug": empreendimento.slug,
        "status": empreendimento.status,
        "ativo": empreendimento.ativo,
        "url_landing_page": empreendimento.url_landing_page,
        "imagem_destaque": empreendimento.imagem_destaque,
        
        # Gatilhos
        "gatilhos": empreendimento.gatilhos or [],
        "prioridade": empreendimento.prioridade,
        
        # Localização
        "endereco": empreendimento.endereco,
        "bairro": empreendimento.bairro,
        "cidade": empreendimento.cidade,
        "estado": empreendimento.estado,
        "cep": empreendimento.cep,
        "descricao_localizacao": empreendimento.descricao_localizacao,
        "latitude": empreendimento.latitude,
        "longitude": empreendimento.longitude,
        
        # Características
        "descricao": empreendimento.descricao,
        "tipologias": empreendimento.tipologias or [],
        "metragem_minima": empreendimento.metragem_minima,
        "metragem_maxima": empreendimento.metragem_maxima,
        "faixa_metragem": f"{empreendimento.metragem_minima or '?'}m² a {empreendimento.metragem_maxima or '?'}m²" if empreendimento.metragem_minima or empreendimento.metragem_maxima else None,
        "torres": empreendimento.torres,
        "andares": empreendimento.andares,
        "unidades_por_andar": empreendimento.unidades_por_andar,
        "total_unidades": empreendimento.total_unidades,
        "vagas_minima": empreendimento.vagas_minima,
        "vagas_maxima": empreendimento.vagas_maxima,
        "previsao_entrega": empreendimento.previsao_entrega,
        
        # Valores
        "preco_minimo": empreendimento.preco_minimo,
        "preco_maximo": empreendimento.preco_maximo,
        "faixa_preco": format_faixa_preco(empreendimento.preco_minimo, empreendimento.preco_maximo),
        "aceita_financiamento": empreendimento.aceita_financiamento,
        "aceita_fgts": empreendimento.aceita_fgts,
        "aceita_permuta": empreendimento.aceita_permuta,
        "aceita_consorcio": empreendimento.aceita_consorcio,
        "condicoes_especiais": empreendimento.condicoes_especiais,
        
        # Lazer e diferenciais
        "itens_lazer": empreendimento.itens_lazer or [],
        "diferenciais": empreendimento.diferenciais or [],
        
        # Qualificação
        "perguntas_qualificacao": empreendimento.perguntas_qualificacao or [],
        "instrucoes_ia": empreendimento.instrucoes_ia,
        
        # Destino leads
        "vendedor_id": empreendimento.vendedor_id,
        "vendedor_nome": vendedor_nome,
        "metodo_distribuicao": empreendimento.metodo_distribuicao,
        "notificar_gestor": empreendimento.notificar_gestor,
        "whatsapp_notificacao": empreendimento.whatsapp_notificacao,
        
        # Métricas
        "total_leads": empreendimento.total_leads,
        "leads_qualificados": empreendimento.leads_qualificados,
        "leads_convertidos": empreendimento.leads_convertidos,
        "taxa_conversao": round((empreendimento.leads_convertidos / empreendimento.total_leads * 100), 1) if empreendimento.total_leads > 0 else 0,
        
        # Extras
        "dados_extras": empreendimento.dados_extras or {},
        
        # Timestamps
        "created_at": empreendimento.created_at.isoformat() if empreendimento.created_at else None,
        "updated_at": empreendimento.updated_at.isoformat() if empreendimento.updated_at else None,
    }


@router.patch("/{empreendimento_id}")
async def update_empreendimento(
    empreendimento_id: int,
    payload: EmpreendimentoUpdate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza um empreendimento.
    """
    await verify_imobiliario_access(tenant)
    
    result = await db.execute(
        select(Empreendimento)
        .where(Empreendimento.id == empreendimento_id)
        .where(Empreendimento.tenant_id == tenant.id)
    )
    empreendimento = result.scalar_one_or_none()
    
    if not empreendimento:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado")
    
    # Valida vendedor (se informado)
    update_data = payload.model_dump(exclude_unset=True)
    
    if "vendedor_id" in update_data and update_data["vendedor_id"]:
        vendedor_result = await db.execute(
            select(Seller)
            .where(Seller.id == update_data["vendedor_id"])
            .where(Seller.tenant_id == tenant.id)
        )
        if not vendedor_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Vendedor não encontrado")
    
    # Atualiza slug se nome mudou
    if "nome" in update_data:
        new_slug = generate_slug(update_data["nome"])
        if new_slug != empreendimento.slug:
            # Verifica se novo slug já existe
            slug_check = await db.execute(
                select(Empreendimento)
                .where(Empreendimento.tenant_id == tenant.id)
                .where(Empreendimento.slug == new_slug)
                .where(Empreendimento.id != empreendimento_id)
            )
            if slug_check.scalar_one_or_none():
                new_slug = f"{new_slug}-{empreendimento_id}"
            update_data["slug"] = new_slug
    
    # Atualiza campos
    for field, value in update_data.items():
        setattr(empreendimento, field, value)
    
    await db.commit()
    await db.refresh(empreendimento)
    
    logger.info(f"Empreendimento atualizado: {empreendimento.nome} (id: {empreendimento_id})")
    
    return {
        "success": True,
        "message": "Empreendimento atualizado com sucesso",
        "empreendimento": {
            "id": empreendimento.id,
            "nome": empreendimento.nome,
            "slug": empreendimento.slug,
            "ativo": empreendimento.ativo,
        }
    }


@router.delete("/{empreendimento_id}")
async def delete_empreendimento(
    empreendimento_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove um empreendimento.
    """
    await verify_imobiliario_access(tenant)
    
    result = await db.execute(
        select(Empreendimento)
        .where(Empreendimento.id == empreendimento_id)
        .where(Empreendimento.tenant_id == tenant.id)
    )
    empreendimento = result.scalar_one_or_none()
    
    if not empreendimento:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado")
    
    nome = empreendimento.nome
    
    await db.delete(empreendimento)
    await db.commit()
    
    logger.info(f"Empreendimento removido: {nome} (id: {empreendimento_id})")
    
    return {
        "success": True,
        "message": "Empreendimento removido com sucesso"
    }


@router.post("/{empreendimento_id}/toggle-status")
async def toggle_empreendimento_status(
    empreendimento_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Ativa/desativa um empreendimento.
    """
    await verify_imobiliario_access(tenant)
    
    result = await db.execute(
        select(Empreendimento)
        .where(Empreendimento.id == empreendimento_id)
        .where(Empreendimento.tenant_id == tenant.id)
    )
    empreendimento = result.scalar_one_or_none()
    
    if not empreendimento:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado")
    
    empreendimento.ativo = not empreendimento.ativo
    await db.commit()
    
    return {
        "success": True,
        "ativo": empreendimento.ativo,
        "message": f"Empreendimento {'ativado' if empreendimento.ativo else 'desativado'}"
    }


@router.get("/{empreendimento_id}/ai-context")
async def get_empreendimento_ai_context(
    empreendimento_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna o contexto do empreendimento formatado para a IA.
    Útil para debug e visualização do que a IA vai receber.
    """
    await verify_imobiliario_access(tenant)
    
    result = await db.execute(
        select(Empreendimento)
        .where(Empreendimento.id == empreendimento_id)
        .where(Empreendimento.tenant_id == tenant.id)
    )
    empreendimento = result.scalar_one_or_none()
    
    if not empreendimento:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado")
    
    return {
        "empreendimento_id": empreendimento.id,
        "ai_context": empreendimento.to_ai_context(),
    }


# ==========================================
# ENDPOINT PARA DETECÇÃO (usado internamente)
# ==========================================

@router.post("/detect")
async def detect_empreendimento_from_message(
    message: str = Query(..., description="Mensagem do lead"),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Detecta se a mensagem contém gatilhos de algum empreendimento.
    Retorna o empreendimento com maior prioridade que casou.
    
    Usado para debug - a detecção real acontece no process_message.
    """
    await verify_imobiliario_access(tenant)
    
    # Busca empreendimentos ativos
    result = await db.execute(
        select(Empreendimento)
        .where(Empreendimento.tenant_id == tenant.id)
        .where(Empreendimento.ativo == True)
        .order_by(Empreendimento.prioridade.desc())
    )
    empreendimentos = result.scalars().all()
    
    message_lower = message.lower()
    matched = None
    matched_trigger = None
    
    for emp in empreendimentos:
        if emp.gatilhos:
            for gatilho in emp.gatilhos:
                if gatilho.lower() in message_lower:
                    matched = emp
                    matched_trigger = gatilho
                    break
        if matched:
            break
    
    if matched:
        return {
            "detected": True,
            "empreendimento": {
                "id": matched.id,
                "nome": matched.nome,
                "slug": matched.slug,
            },
            "trigger_matched": matched_trigger,
            "message": f"Empreendimento '{matched.nome}' detectado pelo gatilho '{matched_trigger}'",
        }
    
    return {
        "detected": False,
        "empreendimento": None,
        "trigger_matched": None,
        "message": "Nenhum empreendimento detectado na mensagem",
    }