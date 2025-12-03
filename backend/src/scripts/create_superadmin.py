"""
Script para criar o tenant principal e o SUPERADMIN em produção.
Pode ser executado quantas vezes precisar: ele não duplica registros.
"""

import asyncio
from sqlalchemy import select

from src.infrastructure.database.connection import async_session
from src.domain.entities import Tenant, User
from src.domain.entities.enums import UserRole
from src.infrastructure.services.auth_service import hash_password


TENANT_NAME = "vellarys"
TENANT_SLUG = "vellarys"

ADMIN_EMAIL = "douglas@velocebm.com"
ADMIN_PASSWORD = "14180218Aab."
ADMIN_NAME = "Douglas Superadmin"


async def main():
    async with async_session() as session:
        # 1. Garantir tenant
        result = await session.execute(
            select(Tenant).where(Tenant.slug == TENANT_SLUG)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            tenant = Tenant(
            name=TENANT_NAME,
            slug=TENANT_SLUG,
            active=True,
            )   

            session.add(tenant)
            await session.flush()  # garante ID
            print(f"✅ Tenant criado: {tenant.name} ({tenant.slug})")
        else:
            print(f"ℹ️ Tenant já existe: {tenant.name} ({tenant.slug})")

        # 2. Garantir usuário superadmin
        result = await session.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                name=ADMIN_NAME,
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PASSWORD),
                role=UserRole.SUPERADMIN,
                active=True,
                tenant_id=tenant.id,
            )
            session.add(user)
            print(f"✅ Superadmin criado: {ADMIN_EMAIL}")
        else:
            # Atualiza para garantir que é SUPERADMIN e está ativo
            user.role = UserRole.SUPERADMIN
            user.is_active = True
            user.tenant_id = tenant.id
            print(f"ℹ️ Superadmin já existia, dados atualizados: {ADMIN_EMAIL}")

        await session.commit()
        print("💾 Commit concluído!")


if __name__ == "__main__":
    asyncio.run(main())
