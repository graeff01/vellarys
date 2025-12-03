from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.infrastructure.database.connection import get_db
from src.domain.entities import Tenant, User
from src.domain.entities.enums import UserRole
from src.infrastructure.services.auth_service import hash_password

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/create-superadmin")
async def create_superadmin(
    email: str,
    password: str,
    tenant_name: str,
    tenant_slug: str,
    db: AsyncSession = Depends(get_db),
):
    # Tenant
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = result.scalar_one_or_none()

    if not tenant:
        tenant = Tenant(
            name=tenant_name,
            slug=tenant_slug,
            active=True,
        )
        db.add(tenant)
        await db.flush()

    # User
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            name="Superadmin",
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.SUPERADMIN,
            active=True,
            tenant_id=tenant.id,
        )
        db.add(user)
    else:
        user.role = UserRole.SUPERADMIN
        user.active = True
        user.tenant_id = tenant.id

    await db.commit()
    return {"message": "Superadmin criado/atualizado com sucesso!"}
