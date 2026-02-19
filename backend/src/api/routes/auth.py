"""
ROTAS: AUTENTICAÇÃO
====================

Login, registro e informações do usuário.
"""

import logging
import re
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field, field_validator

from src.infrastructure.database import get_db
from src.infrastructure.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
)
from src.infrastructure.services.rate_limit_service import (
    check_rate_limit,
    log_login_attempt,
    MAX_ATTEMPTS,
    LOCKOUT_MINUTES,
)
from src.domain.entities import User, Tenant, Channel
from src.domain.entities.enums import UserRole
from src.api.schemas import LoginRequest, TokenResponse
from src.api.dependencies import get_current_user
from src.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Autenticação"])

# Regex para slugs válidos: letras minúsculas, números e hífens, 3-30 caracteres
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,30}$")
# Mínimo de caracteres para senha
MIN_PASSWORD_LENGTH = 8


# ============================================
# SCHEMAS
# ============================================

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=128)
    company_name: str = Field(..., min_length=2, max_length=100)
    company_slug: str = Field(..., min_length=3, max_length=30)
    niche: str = "services"

    @field_validator("company_slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v = v.lower().strip()
        if not SLUG_PATTERN.match(v):
            raise ValueError("Slug deve conter apenas letras minúsculas, números e hífens (3-30 caracteres).")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=128)


# ============================================
# HELPERS
# ============================================

def mask_email(email: str) -> str:
    """Mascara email para logs (LGPD). Ex: user@email.com -> u***@email.com"""
    if not email or "@" not in email:
        return "***"
    local, domain = email.rsplit("@", 1)
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"


def get_client_ip(request: Request) -> Optional[str]:
    """Extrai IP do cliente da requisição."""
    # Verifica headers de proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # IP direto
    if request.client:
        return request.client.host
    
    return None


# ============================================
# ROTAS
# ============================================

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Faz login e retorna token JWT.
    
    Inclui proteção contra força bruta:
    - Máximo de {MAX_ATTEMPTS} tentativas em {LOCKOUT_MINUTES} minutos
    - Bloqueio temporário após exceder limite
    """
    
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")[:500]
    
    # Verifica rate limiting
    is_allowed, remaining, unlock_time = await check_rate_limit(
        db, 
        payload.email, 
        ip_address
    )
    
    if not is_allowed:
        # Registra tentativa bloqueada
        await log_login_attempt(
            db,
            email=payload.email,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason="rate_limited",
        )
        await db.commit()
        
        # Calcula tempo restante
        if unlock_time:
            from datetime import datetime
            remaining_seconds = int((unlock_time - datetime.now()).total_seconds())
            remaining_minutes = max(1, remaining_seconds // 60)
        else:
            remaining_minutes = LOCKOUT_MINUTES
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas de login. Tente novamente em {remaining_minutes} minuto(s).",
            headers={"Retry-After": str(remaining_minutes * 60)}
        )
    
    # Busca usuário por email
    result = await db.execute(
        select(User).where(User.email == payload.email)
    )
    user = result.scalar_one_or_none()
    
    # Usuário não encontrado
    if not user:
        await log_login_attempt(
            db,
            email=payload.email,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason="user_not_found",
        )
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Email ou senha incorretos. Tentativas restantes: {remaining - 1}",
        )
    
    # Verifica senha com captura de erro robusta para PRD
    try:
        is_valid, needs_upgrade = verify_password(payload.password, user.password_hash)
    except Exception as e:
        logger.error(f"Erro na verificação de senha ({mask_email(payload.email)}): {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erro ao processar sua autenticação. Nossa equipe foi notificada."
        )
    
    if not is_valid:
        await log_login_attempt(
            db,
            email=payload.email,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason="invalid_password",
        )
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Email ou senha incorretos. Tentativas restantes: {remaining - 1}",
        )
    
    # Se a senha for válida mas o hash for antigo/fraco, fazemos o upgrade agora
    if needs_upgrade:
        logger.info(f"Upgrade automático de hash para usuário ID={user.id}")
        user.password_hash = hash_password(payload.password)
        # O commit será feito ao final do processo de login logo abaixo
    
    # Usuário inativo
    if not user.active:
        await log_login_attempt(
            db,
            email=payload.email,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason="user_inactive",
        )
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo. Entre em contato com o suporte.",
        )
    
    # Login bem-sucedido!
    await log_login_attempt(
        db,
        email=payload.email,
        success=True,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # Busca tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    # Gera token
    access_token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(user.tenant_id)}
    )
    
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
            } if tenant else None,
        },
    )


@router.post("/register")
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Usado no onboarding de novos clientes.
    Recebe dados via JSON body (nunca query params — protege senhas em logs/URLs).
    """
    # Rate limiting: máximo 10 registros globais por hora (proteção contra spam massivo)
    from sqlalchemy import func
    from datetime import datetime, timedelta
    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent_count_result = await db.execute(
        select(func.count(Tenant.id)).where(Tenant.created_at >= one_hour_ago)
    )
    recent_count = recent_count_result.scalar() or 0
    if recent_count >= 10:
        logger.warning(f"Rate limit de registro atingido ({recent_count} registros na última hora)")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitos cadastros recentes. Tente novamente em alguns minutos.",
            headers={"Retry-After": "3600"},
        )

    # Slugs reservados
    reserved_slugs = {"admin", "api", "auth", "dashboard", "master", "root", "system", "vellarys", "superadmin", "www", "app", "mail", "ftp"}
    if payload.company_slug in reserved_slugs:
        raise HTTPException(
            status_code=400,
            detail="Este nome de empresa não pode ser usado."
        )

    logger.info(f"Nova tentativa de registro: {mask_email(payload.email)}")

    # Verifica se email já existe
    result = await db.execute(
        select(User).where(User.email == payload.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado",
        )

    # Verifica se slug já existe
    result = await db.execute(
        select(Tenant).where(Tenant.slug == payload.company_slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slug já está em uso",
        )

    # Cria tenant
    tenant = Tenant(
        name=payload.company_name,
        slug=payload.company_slug,
        plan="starter",
        settings={
            "niche": payload.niche,
            "company_name": payload.company_name,
            "tone": "cordial",
            "custom_questions": [],
            "custom_rules": [],
        },
        active=True,
    )
    db.add(tenant)
    await db.flush()

    # Cria usuário
    user = User(
        tenant_id=tenant.id,
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN.value,
        active=True,
    )
    db.add(user)

    # Cria canal WhatsApp padrão
    channel = Channel(
        tenant_id=tenant.id,
        type="whatsapp",
        name="WhatsApp Principal",
        config={},
        active=True,
    )
    db.add(channel)

    await db.commit()

    # Gera token
    access_token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(tenant.id)}
    )

    return {
        "success": True,
        "message": "Cadastro realizado com sucesso",
        "access_token": access_token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
        },
    }





@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Altera a senha do usuário logado.
    """
    
    # Verifica senha atual
    is_valid, _ = verify_password(data.current_password, current_user.password_hash)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta",
        )
    
    # Atualiza senha
    current_user.password_hash = hash_password(data.new_password)
    await db.commit()
    
    return {"success": True, "message": "Senha alterada com sucesso"}


@router.get("/me")
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna dados do usuário autenticado.
    """
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_superadmin": user.role == UserRole.SUPERADMIN.value,
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan,
            "settings": tenant.settings,
        } if tenant else None,
    }