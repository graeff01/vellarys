"""
Script para criar oportunidade de teste
========================================
"""
import asyncio
from sqlalchemy import select
from src.infrastructure.database import async_session
from src.domain.entities import Opportunity, Lead, Seller, Tenant, User

async def create_test_opportunity():
    async with async_session() as db:
        # 1. Buscar tenant (pega o primeiro)
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print("❌ Nenhum tenant encontrado!")
            return
        
        print(f"✅ Tenant: {tenant.name} (ID: {tenant.id})")
        
        # 2. Buscar ou criar lead de teste
        result = await db.execute(
            select(Lead).where(Lead.tenant_id == tenant.id).limit(1)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            # Criar lead de teste
            lead = Lead(
                tenant_id=tenant.id,
                name="João Silva (TESTE)",
                phone="+5551999998888",
                platform="whatsapp",
                status="active"
            )
            db.add(lead)
            await db.flush()
        
        print(f"✅ Lead: {lead.name} (ID: {lead.id})")
        
        # 3. Buscar seller
        result = await db.execute(
            select(Seller).where(Seller.tenant_id == tenant.id).limit(1)
        )
        seller = result.scalar_one_or_none()
        
        print(f"✅ Seller: {seller.name if seller else 'N/A'} (ID: {seller.id if seller else 'N/A'})")
        
        # 4. Criar oportunidade de teste
        opportunity = Opportunity(
            tenant_id=tenant.id,
            lead_id=lead.id,
            seller_id=seller.id if seller else None,
            title="Imóvel Casa 3 Quartos Canoas - TESTE",
            status="new",
            value=45000000,  # R$ 450.000,00 em centavos
            product_name="Casa em Canoas - Código 722585",
            product_data={
                "codigo": "722585",
                "tipo": "Casa",
                "regiao": "Canoas",
                "preco": 45000000,
                "quartos": 3,
                "banheiros": 2,
                "vagas": 2,
                "metragem": 120,
                "descricao": "Linda casa com 3 quartos, 2 banheiros e 2 vagas de garagem. Localizada em bairro nobre de Canoas."
            }
        )
        
        db.add(opportunity)
        await db.commit()
        await db.refresh(opportunity)
        
        print(f"\n✅ OPORTUNIDADE CRIADA COM SUCESSO!")
        print(f"   ID: {opportunity.id}")
        print(f"   Título: {opportunity.title}")
        print(f"   Status: {opportunity.status}")
        print(f"   Valor: R$ {opportunity.value / 100:,.2f}")
        print(f"   Lead: {lead.name}")
        print(f"   Seller: {seller.name if seller else 'Sem vendedor'}")
        print(f"\n🔗 Acesse: http://localhost:3000/dashboard/opportunities")

if __name__ == "__main__":
    asyncio.run(create_test_opportunity())
