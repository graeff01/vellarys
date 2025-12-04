"""
Script para criar o tenant principal e o SUPERADMIN em produção.
Pode ser executado quantas vezes precisar: ele não duplica registros.
"""

import asyncio
from sqlalchemy import select

from src.config import get_settings
from src.infrastructure.database.connection import async_session
from src.domain.entities import Tenant, User
from src.domain.entities.enums import UserRole
from src.infrastructure.services.auth_service import hash_password


settings = get_settings()


async def main():
    async with async_session() as session:
        # 1️⃣ Garantir tenant principal
        result = await session.execute(
            select(Tenant).where(Tenant.slug == settings.superadmin_tenant_slug)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            tenant = Tenant(
                name=settings.superadmin_tenant_name,
                slug=settings.superadmin_tenant_slug,
                active=True
            )
            session.add(tenant)
            await session.flush()  # Gera ID
            print(f"✅ Tenant criado: {tenant.name} ({tenant.slug})")
        else:
            print(f"ℹ️ Tenant já existe: {tenant.name} ({tenant.slug})")

        # 2️⃣ Garantir SUPERADMIN
        result = await session.execute(
            select(User).where(User.email == settings.superadmin_email)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                name="Superadmin",
                email=settings.superadmin_email,
                password_hash=hash_password(settings.superadmin_password),
                role=UserRole.SUPERADMIN.value,
                active=True,
                tenant_id=tenant.id
            )
            session.add(user)
            print(f"✅ Superadmin criado: {settings.superadmin_email}")
        else:
            user.role = UserRole.SUPERADMIN.value
            user.active = True
            user.tenant_id = tenant.id
            print(f"ℹ️ Superadmin já existia, dados atualizados: {settings.superadmin_email}")

        await session.commit()
        print("💾 Commit concluído!")


if __name__ == "__main__":
    asyncio.run(main())

