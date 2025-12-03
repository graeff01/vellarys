"""
LGPD SERVICE - Serviço de Compliance LGPD
==========================================

Implementa os direitos dos titulares de dados:
- Direito de acesso (ver seus dados)
- Direito de retificação (corrigir dados)
- Direito de exclusão (apagar dados)
- Direito de portabilidade (exportar dados)
- Consentimento (gerenciar consentimento)

Lei Geral de Proteção de Dados (Lei nº 13.709/2018)
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Lead, Message


class LGPDDataExport:
    """Estrutura de exportação de dados LGPD."""
    
    def __init__(
        self,
        lead_id: int,
        export_date: datetime,
        personal_data: Dict[str, Any],
        messages: List[Dict[str, Any]],
        consent_history: List[Dict[str, Any]],
        processing_activities: List[str],
    ):
        self.lead_id = lead_id
        self.export_date = export_date
        self.personal_data = personal_data
        self.messages = messages
        self.consent_history = consent_history
        self.processing_activities = processing_activities
    
    def to_dict(self) -> dict:
        return {
            "export_info": {
                "lead_id": self.lead_id,
                "export_date": self.export_date.isoformat(),
                "format_version": "1.0",
                "legal_basis": "LGPD - Lei nº 13.709/2018",
            },
            "personal_data": self.personal_data,
            "messages": self.messages,
            "consent_history": self.consent_history,
            "processing_activities": self.processing_activities,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


async def get_lead_by_phone(
    db: AsyncSession,
    tenant_id: int,
    phone: str,
) -> Optional[Lead]:
    """
    Busca lead por telefone.
    """
    # Normaliza telefone (remove caracteres especiais)
    normalized_phone = ''.join(filter(str.isdigit, phone))
    
    result = await db.execute(
        select(Lead)
        .where(Lead.tenant_id == tenant_id)
        .where(Lead.phone.contains(normalized_phone[-8:]))  # Últimos 8 dígitos
    )
    return result.scalar_one_or_none()


async def get_lead_by_email(
    db: AsyncSession,
    tenant_id: int,
    email: str,
) -> Optional[Lead]:
    """
    Busca lead por email.
    """
    result = await db.execute(
        select(Lead)
        .where(Lead.tenant_id == tenant_id)
        .where(Lead.email == email.lower())
    )
    return result.scalar_one_or_none()


async def export_lead_data(
    db: AsyncSession,
    lead: Lead,
) -> LGPDDataExport:
    """
    Exporta todos os dados do lead (Direito de Portabilidade).
    
    Art. 18, V - portabilidade dos dados a outro fornecedor
    """
    
    # Busca todas as mensagens
    messages_result = await db.execute(
        select(Message)
        .where(Message.lead_id == lead.id)
        .order_by(Message.created_at.asc())
    )
    messages = messages_result.scalars().all()
    
    # Monta dados pessoais
    personal_data = {
        "nome": lead.name,
        "telefone": lead.phone,
        "email": lead.email,
        "cidade": lead.city,
        "data_cadastro": lead.created_at.isoformat() if lead.created_at else None,
        "ultima_interacao": lead.last_message_at.isoformat() if lead.last_message_at else None,
        "fonte": lead.source,
        "campanha": lead.campaign,
        "dados_adicionais": lead.custom_data or {},
    }
    
    # Monta histórico de mensagens
    messages_data = [
        {
            "data": msg.created_at.isoformat() if msg.created_at else None,
            "tipo": "enviada" if msg.role == "user" else "recebida",
            "conteudo": msg.content,
        }
        for msg in messages
    ]
    
    # Atividades de processamento
    processing_activities = [
        "Coleta de dados para atendimento via WhatsApp",
        "Qualificação automática por IA",
        "Armazenamento de histórico de conversas",
        "Transferência para equipe de vendas (quando aplicável)",
    ]
    
    # Histórico de consentimento (simplificado)
    consent_history = [
        {
            "data": lead.created_at.isoformat() if lead.created_at else None,
            "tipo": "consentimento_implicito",
            "descricao": "Consentimento dado ao iniciar conversa via WhatsApp",
        }
    ]
    
    return LGPDDataExport(
        lead_id=lead.id,
        export_date=datetime.now(),
        personal_data=personal_data,
        messages=messages_data,
        consent_history=consent_history,
        processing_activities=processing_activities,
    )


async def anonymize_lead(
    db: AsyncSession,
    lead: Lead,
) -> bool:
    """
    Anonimiza dados do lead (mantém registro mas remove dados pessoais).
    
    Usado quando não é possível deletar completamente por questões legais.
    """
    
    lead.name = "[ANONIMIZADO]"
    lead.phone = f"[ANON-{lead.id}]"
    lead.email = None
    lead.city = None
    lead.custom_data = {"_anonymized": True, "_anonymized_at": datetime.now().isoformat()}
    lead.summary = "[Dados anonimizados a pedido do titular]"
    
    await db.flush()
    return True


async def delete_lead_data(
    db: AsyncSession,
    lead: Lead,
    hard_delete: bool = False,
) -> Dict[str, Any]:
    """
    Exclui dados do lead (Direito de Eliminação).
    
    Art. 18, VI - eliminação dos dados pessoais tratados
    
    Args:
        lead: Lead a ser excluído
        hard_delete: Se True, deleta registros. Se False, anonimiza.
    
    Returns:
        Resumo da exclusão
    """
    
    lead_id = lead.id
    messages_count = 0
    
    if hard_delete:
        # Deleta todas as mensagens
        messages_result = await db.execute(
            select(Message).where(Message.lead_id == lead_id)
        )
        messages = messages_result.scalars().all()
        messages_count = len(messages)
        
        for msg in messages:
            await db.delete(msg)
        
        # Deleta o lead
        await db.delete(lead)
        
        await db.flush()
        
        return {
            "action": "hard_delete",
            "lead_id": lead_id,
            "messages_deleted": messages_count,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }
    else:
        # Anonimiza ao invés de deletar
        await anonymize_lead(db, lead)
        
        # Anonimiza mensagens
        messages_result = await db.execute(
            select(Message).where(Message.lead_id == lead_id)
        )
        messages = messages_result.scalars().all()
        messages_count = len(messages)
        
        for msg in messages:
            if msg.role == "user":
                msg.content = "[Mensagem removida a pedido do titular]"
        
        await db.flush()
        
        return {
            "action": "anonymize",
            "lead_id": lead_id,
            "messages_anonymized": messages_count,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }


async def rectify_lead_data(
    db: AsyncSession,
    lead: Lead,
    corrections: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Corrige dados do lead (Direito de Retificação).
    
    Art. 18, III - correção de dados incompletos, inexatos ou desatualizados
    """
    
    changes = {}
    
    if "name" in corrections:
        changes["name"] = {"old": lead.name, "new": corrections["name"]}
        lead.name = corrections["name"]
    
    if "phone" in corrections:
        changes["phone"] = {"old": lead.phone, "new": corrections["phone"]}
        lead.phone = corrections["phone"]
    
    if "email" in corrections:
        changes["email"] = {"old": lead.email, "new": corrections["email"]}
        lead.email = corrections["email"]
    
    if "city" in corrections:
        changes["city"] = {"old": lead.city, "new": corrections["city"]}
        lead.city = corrections["city"]
    
    # Campos customizados
    if "custom_data" in corrections:
        if not lead.custom_data:
            lead.custom_data = {}
        for key, value in corrections["custom_data"].items():
            changes[f"custom_data.{key}"] = {
                "old": lead.custom_data.get(key),
                "new": value
            }
            lead.custom_data[key] = value
    
    await db.flush()
    
    return {
        "action": "rectify",
        "lead_id": lead.id,
        "changes": changes,
        "status": "completed",
        "timestamp": datetime.now().isoformat(),
    }


async def get_processing_info(tenant_id: int) -> Dict[str, Any]:
    """
    Retorna informações sobre o tratamento de dados.
    
    Art. 18, I - confirmação da existência de tratamento
    Art. 18, II - acesso aos dados
    """
    
    return {
        "controlador": {
            "nome": "Velaris",
            "contato": "suporte@velaris.com.br",
        },
        "finalidades": [
            "Atendimento automatizado via WhatsApp",
            "Qualificação de leads para equipe comercial",
            "Melhoria contínua do serviço de atendimento",
        ],
        "base_legal": "Execução de contrato e legítimo interesse (Art. 7º, V e IX)",
        "compartilhamento": [
            "Equipe comercial do contratante (quando lead qualificado)",
            "OpenAI (processamento de linguagem natural)",
        ],
        "retencao": {
            "periodo": "Enquanto durar a relação comercial",
            "apos_encerramento": "12 meses para compliance",
        },
        "direitos": [
            "Acesso aos dados",
            "Correção de dados",
            "Exclusão de dados",
            "Portabilidade de dados",
            "Revogação de consentimento",
        ],
        "como_exercer": "Envie uma mensagem com 'LGPD' ou 'meus dados' para exercer seus direitos.",
    }


# =============================================================================
# DETECÇÃO DE SOLICITAÇÕES LGPD VIA CHAT
# =============================================================================

LGPD_TRIGGERS = {
    "access": [
        r"quero\s+(ver|acessar)\s+(meus\s+)?dados",
        r"quais\s+dados\s+vocês?\s+tem\s+(sobre\s+mim|meus)",
        r"minhas?\s+informações",
        r"meus\s+dados\s+pessoais",
        r"lgpd\s+acesso",
    ],
    "delete": [
        r"(apague?r?|excluir?|deletar?|remover?)\s+(meus\s+)?dados",
        r"quero\s+ser\s+esquecido",
        r"direito\s+ao\s+esquecimento",
        r"não\s+quero\s+mais\s+(meus\s+)?dados",
        r"lgpd\s+(exclu|delet|apag)",
    ],
    "export": [
        r"exportar?\s+(meus\s+)?dados",
        r"portabilidade",
        r"quero\s+(uma\s+)?cópia\s+(dos\s+)?(meus\s+)?dados",
        r"baixar\s+(meus\s+)?dados",
        r"lgpd\s+export",
    ],
    "rectify": [
        r"corrigir?\s+(meus\s+)?dados",
        r"(meus\s+)?dados\s+(estão\s+)?errados?",
        r"atualizar?\s+(meus\s+)?dados",
        r"retificar?",
        r"lgpd\s+corrig",
    ],
    "info": [
        r"lgpd",
        r"proteção\s+de\s+dados",
        r"como\s+vocês?\s+usam?\s+(meus\s+)?dados",
        r"política\s+de\s+privacidade",
        r"termos\s+de\s+uso",
    ],
}


import re

def detect_lgpd_request(message: str) -> Optional[str]:
    """
    Detecta se a mensagem é uma solicitação LGPD.
    
    Returns:
        Tipo de solicitação ('access', 'delete', 'export', 'rectify', 'info') ou None
    """
    message_lower = message.lower()
    
    for request_type, patterns in LGPD_TRIGGERS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                return request_type
    
    return None


def get_lgpd_response(request_type: str, tenant_name: str = "nossa empresa") -> str:
    """
    Retorna resposta apropriada para solicitação LGPD.
    """
    
    responses = {
        "access": (
            f"Você tem o direito de acessar seus dados! 📋\n\n"
            f"Para receber uma cópia dos dados que {tenant_name} possui sobre você, "
            f"por favor confirme enviando 'CONFIRMAR ACESSO'.\n\n"
            f"Enviaremos um relatório com todos os seus dados em até 15 dias."
        ),
        "delete": (
            f"Você tem o direito de solicitar a exclusão dos seus dados. 🗑️\n\n"
            f"⚠️ Atenção: Esta ação é irreversível e removerá:\n"
            f"- Seu histórico de conversas\n"
            f"- Seus dados pessoais\n\n"
            f"Para confirmar a exclusão, envie 'CONFIRMAR EXCLUSÃO'.\n\n"
            f"Processaremos sua solicitação em até 15 dias."
        ),
        "export": (
            f"Você tem o direito de portabilidade dos seus dados! 📤\n\n"
            f"Para receber seus dados em formato digital (JSON), "
            f"envie 'CONFIRMAR EXPORTAÇÃO'.\n\n"
            f"Enviaremos o arquivo em até 15 dias."
        ),
        "rectify": (
            f"Você tem o direito de corrigir seus dados! ✏️\n\n"
            f"Por favor, me diga quais informações estão incorretas e qual o valor correto:\n\n"
            f"Exemplo: 'Meu nome correto é João Silva'\n\n"
            f"Farei a correção imediatamente."
        ),
        "info": (
            f"📜 *Seus Direitos - LGPD*\n\n"
            f"{tenant_name} respeita sua privacidade e a Lei Geral de Proteção de Dados.\n\n"
            f"*Você pode:*\n"
            f"• Ver seus dados - envie 'VER MEUS DADOS'\n"
            f"• Corrigir dados - envie 'CORRIGIR DADOS'\n"
            f"• Exportar dados - envie 'EXPORTAR DADOS'\n"
            f"• Excluir dados - envie 'EXCLUIR DADOS'\n\n"
            f"Para mais informações, acesse nossa política de privacidade."
        ),
    }
    
    return responses.get(request_type, responses["info"])