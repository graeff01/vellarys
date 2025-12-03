"""
DEPENDENCIES (Dependências)
============================

Funções que são injetadas nas rotas para validação.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.services.auth_service import decode_access_token
from src.domain.entities import User, Tenant

# Esquema de autenticação Bearer
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Valida o token e retorna o usuário autenticado.
    
    Uso nas rotas:
        @router.get("/rota-protegida")
        async def rota(user: User = Depends(get_current_user)):
            # user está disponível aqui
    """
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    
    # Busca usuário no banco
    result = await db.execute(
        select(User).where(User.id == int(user_id)).where(User.active == True)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )
    
    return user


async def get_current_tenant(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """
    Retorna o tenant do usuário autenticado.
    """
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id).where(Tenant.active == True)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant não encontrado ou inativo",
        )
    
    return tenant