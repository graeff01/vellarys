"""
ADMIN: Gerenciar Nichos
========================

CRUD completo de nichos de atendimento.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.infrastructure.database import get_db
from src.domain.entities import Niche, Tenant, User, AdminLog
from src.api.routes.admin.deps import get_current_superadmin

router = APIRouter(prefix="/admin/niches", tags=["Admin - Nichos"])


# ============================================
# SCHEMAS
# ============================================

class NicheCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    prompt_template: str
    required_fields: List[str] = []
    optional_fields: List[str] = []
    qualification_rules: dict = {}
    context_rules: dict = {}
    objection_responses: dict = {}
    active: bool = True
    is_default: bool = False


class NicheUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    prompt_template: Optional[str] = None
    required_fields: Optional[List[str]] = None
    optional_fields: Optional[List[str]] = None
    qualification_rules: Optional[dict] = None
    context_rules: Optional[dict] = None
    objection_responses: Optional[dict] = None
    active: Optional[bool] = None
    is_default: Optional[bool] = None


# ============================================
# ROTAS
# ============================================

@router.get("")
async def list_niches(
    active_only: bool = Query(False, description="Listar apenas nichos ativos"),
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os nichos."""
    
    query = select(Niche)
    
    if active_only:
        query = query.where(Niche.active == True)
    
    query = query.order_by(Niche.name)
    
    result = await db.execute(query)
    niches = result.scalars().all()
    
    niches_data = []
    for niche in niches:
        niches_data.append({
            "id": niche.id,
            "slug": niche.slug,
            "name": niche.name,
            "description": niche.description,
            "icon": niche.icon,
            "active": niche.active,
            "is_default": niche.is_default,
            "required_fields": niche.required_fields,
            "optional_fields": niche.optional_fields,
            "created_at": niche.created_at.isoformat() if niche.created_at else None,
        })
    
    return {"niches": niches_data, "total": len(niches_data)}


@router.get("/{niche_id}")
async def get_niche(
    niche_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Retorna detalhes de um nicho específico."""
    
    result = await db.execute(
        select(Niche).where(Niche.id == niche_id)
    )
    niche = result.scalar_one_or_none()
    
    if not niche:
        raise HTTPException(status_code=404, detail="Nicho não encontrado")
    
    return {
        "id": niche.id,
        "slug": niche.slug,
        "name": niche.name,
        "description": niche.description,
        "icon": niche.icon,
        "prompt_template": niche.prompt_template,
        "required_fields": niche.required_fields,
        "optional_fields": niche.optional_fields,
        "qualification_rules": niche.qualification_rules,
        "context_rules": niche.context_rules,
        "objection_responses": niche.objection_responses,
        "active": niche.active,
        "is_default": niche.is_default,
        "created_at": niche.created_at.isoformat() if niche.created_at else None,
        "updated_at": niche.updated_at.isoformat() if niche.updated_at else None,
    }


@router.post("")
async def create_niche(
    data: NicheCreate,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Cria um novo nicho."""
    
    # Verifica se slug já existe
    existing = await db.execute(
        select(Niche).where(Niche.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug já existe")
    
    # Se é default, remove default dos outros
    if data.is_default:
        result = await db.execute(select(Niche).where(Niche.is_default == True))
        for niche in result.scalars().all():
            niche.is_default = False
    
    niche = Niche(
        slug=data.slug,
        name=data.name,
        description=data.description,
        icon=data.icon,
        prompt_template=data.prompt_template,
        required_fields=data.required_fields,
        optional_fields=data.optional_fields,
        qualification_rules=data.qualification_rules,
        context_rules=data.context_rules,
        objection_responses=data.objection_responses,
        active=data.active,
        is_default=data.is_default,
    )
    db.add(niche)
    await db.flush()
    
    # Log da ação
    log = AdminLog(
        admin_id=current_user.id,
        admin_email=current_user.email,
        action="create_niche",
        target_type="niche",
        target_id=niche.id,
        target_name=niche.name,
        details={"slug": niche.slug},
    )
    db.add(log)
    
    await db.commit()
    
    return {
        "success": True,
        "niche": {
            "id": niche.id,
            "slug": niche.slug,
            "name": niche.name,
        }
    }


@router.patch("/{niche_id}")
async def update_niche(
    niche_id: int,
    data: NicheUpdate,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza um nicho."""
    
    result = await db.execute(
        select(Niche).where(Niche.id == niche_id)
    )
    niche = result.scalar_one_or_none()
    
    if not niche:
        raise HTTPException(status_code=404, detail="Nicho não encontrado")
    
    changes = {}
    
    if data.name is not None:
        changes["name"] = {"old": niche.name, "new": data.name}
        niche.name = data.name
    
    if data.description is not None:
        niche.description = data.description
    
    if data.icon is not None:
        niche.icon = data.icon
    
    if data.prompt_template is not None:
        changes["prompt_template"] = "atualizado"
        niche.prompt_template = data.prompt_template
    
    if data.required_fields is not None:
        niche.required_fields = data.required_fields
    
    if data.optional_fields is not None:
        niche.optional_fields = data.optional_fields
    
    if data.qualification_rules is not None:
        niche.qualification_rules = data.qualification_rules
    
    if data.context_rules is not None:
        niche.context_rules = data.context_rules
    
    if data.objection_responses is not None:
        niche.objection_responses = data.objection_responses
    
    if data.active is not None:
        changes["active"] = {"old": niche.active, "new": data.active}
        niche.active = data.active
    
    if data.is_default is not None:
        if data.is_default:
            result = await db.execute(select(Niche).where(Niche.is_default == True))
            for n in result.scalars().all():
                n.is_default = False
        niche.is_default = data.is_default
    
    # Log da ação
    log = AdminLog(
        admin_id=current_user.id,
        admin_email=current_user.email,
        action="update_niche",
        target_type="niche",
        target_id=niche.id,
        target_name=niche.name,
        details=changes,
    )
    db.add(log)
    
    await db.commit()
    
    return {"success": True, "changes": changes}


@router.delete("/{niche_id}")
async def delete_niche(
    niche_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Deleta um nicho (soft delete - apenas desativa)."""
    
    result = await db.execute(
        select(Niche).where(Niche.id == niche_id)
    )
    niche = result.scalar_one_or_none()
    
    if not niche:
        raise HTTPException(status_code=404, detail="Nicho não encontrado")
    
    if niche.is_default:
        raise HTTPException(status_code=400, detail="Não é possível deletar o nicho padrão")
    
    # Soft delete
    niche.active = False
    
    # Log da ação
    log = AdminLog(
        admin_id=current_user.id,
        admin_email=current_user.email,
        action="delete_niche",
        target_type="niche",
        target_id=niche.id,
        target_name=niche.name,
        details={"soft_delete": True},
    )
    db.add(log)
    
    await db.commit()
    
    return {"success": True, "message": "Nicho desativado"}


@router.post("/seed-defaults")
async def seed_default_niches(
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """
    Popula o banco com os nichos padrão.
    
    Use apenas uma vez na configuração inicial.
    """
    
    default_niches = [
        {
            "slug": "real_estate",
            "name": "Imobiliária",
            "description": "Compra, venda e aluguel de imóveis",
            "icon": "🏠",
            "required_fields": ["name", "phone", "interest_type", "city"],
            "optional_fields": ["property_type", "neighborhood", "bedrooms", "budget", "financing"],
            "qualification_rules": {
                "hot": ["quer comprar agora", "urgente", "já tem entrada", "pré-aprovado", "quer visitar"],
                "warm": ["pesquisando", "próximos 6 meses", "ainda decidindo", "comparando"],
                "cold": ["só curiosidade", "sem previsão", "apenas olhando"]
            },
            "is_default": False,
        },
        {
            "slug": "healthcare",
            "name": "Clínica / Saúde",
            "description": "Clínicas médicas, odontológicas, estéticas",
            "icon": "🏥",
            "required_fields": ["name", "phone", "specialty", "urgency"],
            "optional_fields": ["insurance", "preferred_date", "symptoms"],
            "qualification_rules": {
                "hot": ["urgente", "dor", "emergência", "hoje", "amanhã", "quer agendar"],
                "warm": ["essa semana", "consulta de rotina", "retorno"],
                "cold": ["só informação", "só preço", "sem previsão"]
            },
            "is_default": False,
        },
        {
            "slug": "fitness",
            "name": "Academia / Fitness",
            "description": "Academias, personal trainers, estúdios",
            "icon": "💪",
            "required_fields": ["name", "phone", "goal"],
            "optional_fields": ["experience", "preferred_time", "health_issues"],
            "qualification_rules": {
                "hot": ["quero começar agora", "essa semana", "já decidi", "qual o valor"],
                "warm": ["pesquisando academias", "pensando em começar", "comparando"],
                "cold": ["só preço", "talvez no futuro", "muito caro"]
            },
            "is_default": False,
        },
        {
            "slug": "education",
            "name": "Educação / Cursos",
            "description": "Escolas, cursos, treinamentos",
            "icon": "📚",
            "required_fields": ["name", "phone", "course_interest"],
            "optional_fields": ["current_level", "availability", "payment_preference"],
            "qualification_rules": {
                "hot": ["quero me matricular", "começar agora", "já decidi"],
                "warm": ["comparando escolas", "esse semestre", "pesquisando"],
                "cold": ["só informação", "ano que vem", "só preço"]
            },
            "is_default": False,
        },
        {
            "slug": "services",
            "name": "Serviços Gerais",
            "description": "Prestadores de serviço diversos",
            "icon": "🔧",
            "required_fields": ["name", "phone", "service_type", "city"],
            "optional_fields": ["description", "urgency", "budget"],
            "qualification_rules": {
                "hot": ["urgente", "preciso pra hoje", "orçamento aprovado"],
                "warm": ["essa semana", "pegando orçamentos"],
                "cold": ["só cotação", "sem previsão"]
            },
            "is_default": True,
        },
    ]
    
    created = 0
    skipped = 0
    
    for niche_data in default_niches:
        # Verifica se já existe
        existing = await db.execute(
            select(Niche).where(Niche.slug == niche_data["slug"])
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        
        # Cria prompt template básico
        prompt_template = f"""Você é um assistente virtual especializado em {niche_data["name"]}.

Seu objetivo é:
1. Atender o cliente de forma cordial e profissional
2. Coletar as informações necessárias: {", ".join(niche_data["required_fields"])}
3. Qualificar o lead (identificar urgência e interesse real)
4. Encaminhar para um atendente humano quando apropriado

Informações opcionais que podem ser coletadas: {", ".join(niche_data["optional_fields"])}

Seja sempre educado, objetivo e focado em ajudar o cliente."""
        
        niche = Niche(
            slug=niche_data["slug"],
            name=niche_data["name"],
            description=niche_data["description"],
            icon=niche_data["icon"],
            prompt_template=prompt_template,
            required_fields=niche_data["required_fields"],
            optional_fields=niche_data["optional_fields"],
            qualification_rules=niche_data["qualification_rules"],
            context_rules={},
            objection_responses={},
            active=True,
            is_default=niche_data.get("is_default", False),
        )
        db.add(niche)
        created += 1
    
    # Log da ação
    log = AdminLog(
        admin_id=current_user.id,
        admin_email=current_user.email,
        action="seed_niches",
        target_type="niche",
        target_id=None,
        target_name=None,
        details={"created": created, "skipped": skipped},
    )
    db.add(log)
    
    await db.commit()
    
    return {
        "success": True,
        "created": created,
        "skipped": skipped,
        "message": f"{created} nichos criados, {skipped} já existiam"
    }