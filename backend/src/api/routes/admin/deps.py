"""
Dependências do Admin
======================

Verifica se o usuário é superadmin.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.api.dependencies import get_current_user
from src.domain.entities import User
from src.domain.entities.enums import UserRole


async def get_current_superadmin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Verifica se o usuário atual é superadmin.
    
    Raises:
        HTTPException 403: Se não for superadmin
    """
    if current_user.role != UserRole.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas superadmins podem acessar este recurso."
        )
    return current_user