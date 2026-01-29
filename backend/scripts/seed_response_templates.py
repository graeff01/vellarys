#!/usr/bin/env python3
"""
Script para popular templates de respostas rápidas.

Cria templates pré-definidos para vendedores em categorias:
- Saudação
- Follow-up
- Documentos
- Disponibilidade
- Agradecimento
- Proposta
- Objeção
"""

import asyncio
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.domain.entities.response_template import ResponseTemplate
from src.domain.entities.models import Tenant

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL não configurado")
    sys.exit(1)

# Converter postgresql:// para postgresql+asyncpg://
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# =============================================================================
# TEMPLATES PRÉ-DEFINIDOS
# =============================================================================

TEMPLATES = [
    # =========================================================================
    # SAUDAÇÃO
    # =========================================================================
    {
        "name": "Saudação Inicial",
        "shortcut": "/oi",
        "category": "saudacao",
        "content": "Olá {{lead_name}}! 👋\n\nMeu nome é {{seller_name}} e estou aqui para te ajudar.\n\nComo posso ser útil hoje?"
    },
    {
        "name": "Saudação Manhã",
        "shortcut": "/bomdia",
        "category": "saudacao",
        "content": "Bom dia, {{lead_name}}! ☀️\n\nEspero que esteja tendo um ótimo início de dia.\n\nSou {{seller_name}} da {{company_name}} e gostaria de conversar sobre como podemos ajudar sua empresa.\n\nTem alguns minutos agora?"
    },
    {
        "name": "Saudação Tarde",
        "shortcut": "/boatarde",
        "category": "saudacao",
        "content": "Boa tarde, {{lead_name}}! 😊\n\nSou {{seller_name}} da {{company_name}}.\n\nVi que você demonstrou interesse em nossa solução. Podemos conversar?"
    },
    {
        "name": "Retorno de Conversa",
        "shortcut": "/retorno",
        "category": "saudacao",
        "content": "Oi {{lead_name}}, tudo bem? 😊\n\nRetornando nossa conversa anterior...\n\nJá teve tempo de pensar sobre nossa proposta?"
    },

    # =========================================================================
    # FOLLOW-UP
    # =========================================================================
    {
        "name": "Follow-up Gentil",
        "shortcut": "/followup",
        "category": "followup",
        "content": "Oi {{lead_name}}! 👋\n\nNotei que não conseguimos finalizar nossa conversa.\n\nAinda tem interesse em conhecer nossa solução? Posso te ajudar com alguma dúvida?"
    },
    {
        "name": "Follow-up Proposta",
        "shortcut": "/followupproposta",
        "category": "followup",
        "content": "Olá {{lead_name}}!\n\nEnviei uma proposta há alguns dias e gostaria de saber sua opinião.\n\nTeve tempo de analisar? Tem alguma dúvida que eu possa esclarecer?"
    },
    {
        "name": "Follow-up Reunião",
        "shortcut": "/followupreuniao",
        "category": "followup",
        "content": "Oi {{lead_name}}! 😊\n\nSó passando para confirmar nossa reunião.\n\nContinua disponível para conversarmos?"
    },
    {
        "name": "Reengajamento",
        "shortcut": "/reengajar",
        "category": "followup",
        "content": "Olá {{lead_name}}! 👋\n\nFaz um tempo que não conversamos.\n\nGostaria de saber se ainda tem interesse em otimizar [benefício principal] na sua empresa?\n\nTemos novidades que podem te interessar!"
    },

    # =========================================================================
    # DOCUMENTOS
    # =========================================================================
    {
        "name": "Solicitar Documentos",
        "shortcut": "/docs",
        "category": "documentos",
        "content": "Oi {{lead_name}}! 📄\n\nPara darmos continuidade, vou precisar de alguns documentos:\n\n• [Documento 1]\n• [Documento 2]\n• [Documento 3]\n\nPode me enviar quando tiver disponível?"
    },
    {
        "name": "Enviar Catálogo",
        "shortcut": "/catalogo",
        "category": "documentos",
        "content": "Oi {{lead_name}}! 📋\n\nSegue nosso catálogo completo com todas as soluções que oferecemos.\n\n[Link do catálogo]\n\nQual dessas opções faz mais sentido para sua empresa?"
    },
    {
        "name": "Enviar Proposta",
        "shortcut": "/enviarproposta",
        "category": "documentos",
        "content": "Olá {{lead_name}}! 📊\n\nConforme conversamos, segue a proposta personalizada para {{company_name}}.\n\nAnalisei suas necessidades e montei um plano que vai [benefício principal].\n\nQualquer dúvida, estou à disposição!"
    },

    # =========================================================================
    # DISPONIBILIDADE
    # =========================================================================
    {
        "name": "Confirmar Disponibilidade",
        "shortcut": "/disponivel",
        "category": "disponibilidade",
        "content": "Oi {{lead_name}}! 📅\n\nPara alinharmos os próximos passos, qual horário funciona melhor para você?\n\nTenho disponibilidade:\n• Amanhã às [horário]\n• [Dia] às [horário]\n• [Dia] às [horário]\n\nQual prefere?"
    },
    {
        "name": "Reagendar",
        "shortcut": "/reagendar",
        "category": "disponibilidade",
        "content": "Oi {{lead_name}}! 🔄\n\nSem problemas! Entendo que imprevistos acontecem.\n\nPodemos reagendar para:\n• [Data/Hora 1]\n• [Data/Hora 2]\n• [Data/Hora 3]\n\nQual funciona melhor?"
    },
    {
        "name": "Confirmar Horário",
        "shortcut": "/confirmar",
        "category": "disponibilidade",
        "content": "Oi {{lead_name}}! ⏰\n\nSó confirmando: nossa conversa está marcada para [dia] às [horário].\n\nNos vemos lá! 😊"
    },

    # =========================================================================
    # AGRADECIMENTO
    # =========================================================================
    {
        "name": "Obrigado Interesse",
        "shortcut": "/obrigado",
        "category": "agradecimento",
        "content": "Muito obrigado pelo seu interesse, {{lead_name}}! 🙏\n\nEstou à disposição para qualquer dúvida.\n\nVamos construir algo incrível juntos!"
    },
    {
        "name": "Obrigado Compra",
        "shortcut": "/obrigadocompra",
        "category": "agradecimento",
        "content": "{{lead_name}}, muito obrigado pela confiança! 🎉\n\nEstou muito feliz em ter você como cliente.\n\nVamos fazer acontecer! Qualquer coisa, pode contar comigo."
    },
    {
        "name": "Obrigado Indicação",
        "shortcut": "/obrigadoindicacao",
        "category": "agradecimento",
        "content": "{{lead_name}}, muito obrigado pela indicação! 🌟\n\nÉ uma honra ter sua confiança.\n\nVou cuidar do seu contato com todo carinho!"
    },

    # =========================================================================
    # PROPOSTA
    # =========================================================================
    {
        "name": "Apresentar Solução",
        "shortcut": "/solucao",
        "category": "proposta",
        "content": "Oi {{lead_name}}! 💡\n\nBaseado no que conversamos, nossa solução vai:\n\n✅ [Benefício 1]\n✅ [Benefício 2]\n✅ [Benefício 3]\n\nInvestimento: R$ [valor]/mês\n\nVamos agendar uma demo?"
    },
    {
        "name": "Proposta Personalizada",
        "shortcut": "/proposta",
        "category": "proposta",
        "content": "Olá {{lead_name}}! 📊\n\nMontei uma proposta personalizada para {{company_name}} considerando:\n\n• [Necessidade 1]\n• [Necessidade 2]\n• [Necessidade 3]\n\nEntrega em [prazo] por R$ [valor].\n\nO que acha?"
    },
    {
        "name": "Condições Especiais",
        "shortcut": "/especial",
        "category": "proposta",
        "content": "{{lead_name}}, tenho uma condição especial para você! 🎁\n\nSe fecharmos até {{current_date}}, consigo:\n\n• [Benefício 1]\n• [Benefício 2]\n• [Benefício 3]\n\nVamos aproveitar?"
    },

    # =========================================================================
    # OBJEÇÃO
    # =========================================================================
    {
        "name": "Resposta Preço Alto",
        "shortcut": "/preco",
        "category": "objecao",
        "content": "Entendo sua preocupação com o investimento, {{lead_name}}! 💰\n\nMas veja só: nossa solução vai [economia/resultado] e se paga em [tempo].\n\nAlém disso, temos condições flexíveis de pagamento.\n\nQue tal conversarmos sobre as opções?"
    },
    {
        "name": "Resposta Tempo",
        "shortcut": "/semtempo",
        "category": "objecao",
        "content": "Entendo que seu tempo é valioso, {{lead_name}}! ⏰\n\nJustamente por isso nossa solução vai te ajudar a [ganhar tempo/automatizar].\n\nPodemos fazer uma conversa rápida de 15 minutos? Você escolhe o melhor horário."
    },
    {
        "name": "Resposta Concorrente",
        "shortcut": "/concorrente",
        "category": "objecao",
        "content": "Que bom que está pesquisando, {{lead_name}}! 🔍\n\nNosso diferencial é:\n\n✅ [Diferencial 1]\n✅ [Diferencial 2]\n✅ [Diferencial 3]\n\nE mais: [benefício único]\n\nVale a pena conhecer!"
    },
    {
        "name": "Resposta Pensar",
        "shortcut": "/pensar",
        "category": "objecao",
        "content": "Claro, {{lead_name}}! É importante pensar bem. 🤔\n\nPara te ajudar na decisão, posso esclarecer alguma dúvida específica?\n\nOu prefere que eu envie mais informações sobre [aspecto específico]?"
    },

    # =========================================================================
    # ENCERRAMENTO
    # =========================================================================
    {
        "name": "Finalizar Positivo",
        "shortcut": "/fechar",
        "category": "encerramento",
        "content": "Perfeito, {{lead_name}}! 🎉\n\nVou preparar tudo para começarmos.\n\nQualquer dúvida, estou aqui.\n\nBem-vindo(a) à {{company_name}}!"
    },
    {
        "name": "Manter Contato",
        "shortcut": "/mantercontato",
        "category": "encerramento",
        "content": "Tudo bem, {{lead_name}}! 😊\n\nSem pressão! Quando quiser retomar, é só me chamar.\n\nVou deixar meu contato caso precise: [contato]\n\nFique à vontade!"
    },
]


# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

async def seed_templates():
    """Popula templates para todos os tenants."""

    print("\n" + "="*80)
    print("🌱 SEED: RESPONSE TEMPLATES")
    print("="*80)

    async with AsyncSessionLocal() as session:
        # Buscar todos os tenants
        stmt = select(Tenant).where(Tenant.active == True)
        result = await session.execute(stmt)
        tenants = result.scalars().all()

        if not tenants:
            print("⚠️  Nenhum tenant ativo encontrado")
            return

        print(f"\n📋 Encontrados {len(tenants)} tenants ativos")

        for tenant in tenants:
            print(f"\n🏢 Processando tenant: {tenant.name} (ID: {tenant.id})")

            # Verificar se já tem templates
            check = await session.execute(
                select(ResponseTemplate).where(ResponseTemplate.tenant_id == tenant.id)
            )
            existing = check.scalars().all()

            if existing:
                print(f"   ℹ️  Já existem {len(existing)} templates. Pulando...")
                continue

            # Criar templates
            created_count = 0
            for template_data in TEMPLATES:
                template = ResponseTemplate(
                    tenant_id=tenant.id,
                    created_by_user_id=None,  # Templates do sistema
                    name=template_data["name"],
                    shortcut=template_data["shortcut"],
                    content=template_data["content"],
                    category=template_data["category"],
                    is_active=True,
                    usage_count=0,
                )
                session.add(template)
                created_count += 1

            await session.commit()
            print(f"   ✅ Criados {created_count} templates!")

        print("\n" + "="*80)
        print("✅ SEED CONCLUÍDO COM SUCESSO!")
        print("="*80)

        # Mostrar resumo por categoria
        print("\n📊 RESUMO POR CATEGORIA:")
        categories = {}
        for t in TEMPLATES:
            cat = t["category"]
            categories[cat] = categories.get(cat, 0) + 1

        for category, count in sorted(categories.items()):
            print(f"   • {category.capitalize()}: {count} templates")


async def main():
    try:
        await seed_templates()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
