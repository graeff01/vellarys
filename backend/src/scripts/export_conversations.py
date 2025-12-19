"""
EXPORT CONVERSAS PARA AUDITORIA
=================================
Extrai todas as conversas do banco formatadas para análise.
"""

import asyncio
import json
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.infrastructure.database import async_session
from src.domain.entities import Lead, Message, Tenant


async def export_conversations(tenant_slug: str = None, output_format: str = "txt"):
    """
    Exporta conversas do banco.
    
    Args:
        tenant_slug: Se informado, filtra por tenant. Se None, pega todos.
        output_format: 'txt', 'json' ou 'md'
    """
    
    async with async_session() as session:
        # Busca leads com suas mensagens
        query = (
            select(Lead)
            .options(selectinload(Lead.messages))
            .options(selectinload(Lead.tenant))
        )
        
        # Filtra por tenant se informado
        if tenant_slug:
            tenant_result = await session.execute(
                select(Tenant).where(Tenant.slug == tenant_slug)
            )
            tenant = tenant_result.scalar_one_or_none()
            if not tenant:
                print(f"❌ Tenant '{tenant_slug}' não encontrado!")
                return
            
            query = query.where(Lead.tenant_id == tenant.id)
            print(f"✅ Filtrando por tenant: {tenant.name}")
        
        # Ordena por data
        query = query.order_by(Lead.created_at.desc())
        
        result = await session.execute(query)
        leads = result.scalars().all()
        
        print(f"\n📊 Total de leads encontrados: {len(leads)}")
        
        # Exporta
        if output_format == "txt":
            export_txt(leads)
        elif output_format == "json":
            export_json(leads)
        elif output_format == "md":
            export_markdown(leads)
        else:
            print(f"❌ Formato '{output_format}' inválido. Use: txt, json ou md")


def export_txt(leads):
    """Exporta conversas em formato texto legível."""
    
    filename = f"conversas_auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("AUDITORIA DE CONVERSAS DA IA\n")
        f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        total_mensagens = 0
        leads_com_conversa = 0
        
        for lead in leads:
            # Ordena mensagens por data
            messages = sorted(lead.messages, key=lambda m: m.created_at)
            
            if not messages:
                continue
            
            leads_com_conversa += 1
            total_mensagens += len(messages)
            
            # Cabeçalho do lead
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"LEAD #{lead.id}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Nome: {lead.name or 'Não informado'}\n")
            f.write(f"Telefone: {lead.phone or 'Não informado'}\n")
            f.write(f"Qualificação: {lead.qualification or 'Não qualificado'}\n")
            f.write(f"Status: {lead.status}\n")
            f.write(f"Data: {lead.created_at.strftime('%d/%m/%Y %H:%M')}\n")
            f.write(f"Tenant: {lead.tenant.name}\n")
            
            if lead.summary:
                f.write(f"\n📝 RESUMO DA IA:\n{lead.summary}\n")
            
            f.write("\n" + "-" * 80 + "\n")
            f.write("CONVERSA:\n")
            f.write("-" * 80 + "\n\n")
            
            # Mensagens
            for msg in messages:
                timestamp = msg.created_at.strftime("%H:%M:%S")
                
                if msg.role == "user":
                    f.write(f"[{timestamp}] 👤 LEAD:\n")
                    f.write(f"{msg.content}\n\n")
                else:
                    f.write(f"[{timestamp}] 🤖 IA:\n")
                    f.write(f"{msg.content}\n\n")
            
            f.write("\n")
        
        # Estatísticas finais
        f.write("\n" + "=" * 80 + "\n")
        f.write("ESTATÍSTICAS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total de leads: {len(leads)}\n")
        f.write(f"Leads com conversa: {leads_com_conversa}\n")
        f.write(f"Total de mensagens: {total_mensagens}\n")
        f.write(f"Média msgs/lead: {total_mensagens / leads_com_conversa if leads_com_conversa > 0 else 0:.1f}\n")
        f.write("=" * 80 + "\n")
    
    print(f"\n✅ Arquivo gerado: {filename}")
    print(f"📊 {leads_com_conversa} conversas exportadas")
    print(f"💬 {total_mensagens} mensagens no total")


def export_json(leads):
    """Exporta conversas em formato JSON."""
    
    filename = f"conversas_auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    data = {
        "gerado_em": datetime.now().isoformat(),
        "total_leads": len(leads),
        "conversas": []
    }
    
    for lead in leads:
        messages = sorted(lead.messages, key=lambda m: m.created_at)
        
        if not messages:
            continue
        
        conversa = {
            "lead_id": lead.id,
            "nome": lead.name,
            "telefone": lead.phone,
            "qualificacao": lead.qualification,
            "status": lead.status,
            "data": lead.created_at.isoformat(),
            "tenant": lead.tenant.name,
            "resumo": lead.summary,
            "mensagens": [
                {
                    "timestamp": msg.created_at.isoformat(),
                    "role": msg.role,
                    "conteudo": msg.content
                }
                for msg in messages
            ]
        }
        
        data["conversas"].append(conversa)
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Arquivo JSON gerado: {filename}")


def export_markdown(leads):
    """Exporta conversas em formato Markdown."""
    
    filename = f"conversas_auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# 🔍 Auditoria de Conversas da IA\n\n")
        f.write(f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        for lead in leads:
            messages = sorted(lead.messages, key=lambda m: m.created_at)
            
            if not messages:
                continue
            
            f.write(f"## Lead #{lead.id}\n\n")
            f.write(f"- **Nome:** {lead.name or 'Não informado'}\n")
            f.write(f"- **Telefone:** {lead.phone or 'Não informado'}\n")
            f.write(f"- **Qualificação:** `{lead.qualification or 'Não qualificado'}`\n")
            f.write(f"- **Status:** `{lead.status}`\n")
            f.write(f"- **Data:** {lead.created_at.strftime('%d/%m/%Y %H:%M')}\n")
            f.write(f"- **Tenant:** {lead.tenant.name}\n\n")
            
            if lead.summary:
                f.write(f"> **Resumo da IA:** {lead.summary}\n\n")
            
            f.write("### 💬 Conversa\n\n")
            
            for msg in messages:
                timestamp = msg.created_at.strftime("%H:%M:%S")
                
                if msg.role == "user":
                    f.write(f"**[{timestamp}] 👤 Lead:**\n")
                    f.write(f"> {msg.content}\n\n")
                else:
                    f.write(f"**[{timestamp}] 🤖 IA:**\n")
                    f.write(f"> {msg.content}\n\n")
            
            f.write("---\n\n")
    
    print(f"\n✅ Arquivo Markdown gerado: {filename}")


# ===================================
# EXECUTAR
# ===================================
if __name__ == "__main__":
    import sys
    
    # Argumentos
    tenant_slug = sys.argv[1] if len(sys.argv) > 1 else None
    output_format = sys.argv[2] if len(sys.argv) > 2 else "txt"
    
    print("\n🔍 EXPORTANDO CONVERSAS PARA AUDITORIA\n")
    
    asyncio.run(export_conversations(tenant_slug, output_format))


