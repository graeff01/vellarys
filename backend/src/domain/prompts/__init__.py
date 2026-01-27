"""
Módulo de prompts - DEPRECATED
================================
Prompts foram movidos para inline no process_message.py (GPT-4o).
Este arquivo existe apenas para compatibilidade com código legado.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class NicheConfig:
    """Configuração legacy de nicho."""
    name: str
    tone: str = "cordial"
    company_name: str = "Vellarys"
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "tone": self.tone,
            "company_name": self.company_name,
        }


# Templates vazios para compatibilidade
NICHE_SPECIFIC_TEMPLATES: Dict[str, NicheConfig] = {
    "real_estate": NicheConfig(name="real_estate", tone="cordial"),
    "healthcare": NicheConfig(name="healthcare", tone="cordial"),
    "fitness": NicheConfig(name="fitness", tone="informal"),
    "education": NicheConfig(name="education", tone="cordial"),
    "services": NicheConfig(name="services", tone="cordial"),
}

# Alias para compatibilidade
NICHE_TEMPLATES = NICHE_SPECIFIC_TEMPLATES


def get_niche_config(niche: str = "services", **kwargs) -> Dict[str, Any]:
    """
    Retorna configuração básica de nicho (versão compatibilidade).
    
    NOTA: Esta função é legacy. Novos prompts estão inline no process_message.py
    """
    config = NICHE_SPECIFIC_TEMPLATES.get(niche, NICHE_SPECIFIC_TEMPLATES["services"])
    
    return {
        "tone": config.tone,
        "company_name": kwargs.get("company_name", config.company_name),
        "niche": niche,
    }


def get_available_niches() -> List[str]:
    """Retorna lista de nichos disponíveis (legacy)."""
    return list(NICHE_SPECIFIC_TEMPLATES.keys())


def build_system_prompt(
    niche_id: str,
    company_name: str,
    tone: str = "cordial",
    custom_questions: List[str] = None,
    custom_rules: List[str] = None,
    custom_prompt: Optional[str] = None,
    faq_items: List[Dict] = None,
    scope_description: str = "",
    lead_context: Optional[Any] = None,
    identity: Optional[Dict] = None,
    scope_config: Optional[Dict] = None,
    niche_template: Optional[str] = None,
) -> str:
    """
    Esta é a 'alma' do Vellarys. Centraliza persona e regras.
    """
    
    # 1. PERSONA E IDENTIDADE
    persona_rules = []
    if niche_id in ["realestate", "imobiliaria", "real_estate", "imobiliario"]:
        persona_rules = [
            f"Você é um Corretor de Imóveis especialista da {company_name}, em Canoas/RS.",
            "Sua missão é conduzir o cliente para o fechamento ou agendamento de visita.",
            "Postura: Consultiva (ajude a entender o mercado), Ágil (respostas curtas) e Humana.",
        ]
    else:
        persona_rules = [
            f"Você é um assistente especialista da {company_name}.",
            "Sua missão é fornecer um atendimento de excelência e converter leads.",
            f"Tom de voz: {tone}.",
        ]

    # 2. REGRAS DE NEGÓCIO (CUSTOMIZADAS)
    business_rules = custom_rules or []
    if identity and identity.get("business_rules"):
        business_rules.extend(identity.get("business_rules"))
    
    # 3. PERGUNTAS DE QUALIFICAÇÃO
    questions_to_ask = custom_questions or []
    if identity and identity.get("required_questions"):
        questions_to_ask.extend(identity.get("required_questions"))

    # --- NOVO: Se houver um template de nicho, use-o como base! ---
    if niche_template:
        system_base = niche_template
        # Injeta variáveis básicas no template ({{campo}})
        replacements = {
            "company_name": company_name,
            "tone": tone,
            "niche": niche_id,
        }
        for key, val in replacements.items():
            placeholder = "{{" + key + "}}"
            if placeholder in system_base:
                system_base = system_base.replace(placeholder, str(val))
        
        prompt_lines = [system_base]
    else:
        # Fallback para o prompt hardcoded (legado)
        prompt_lines = [
            "# PERSONA",
            "\n".join(persona_rules),
            "",
            "# REGRAS DE OURO",
            "- NUNCA negocie descontos.",
            "- NUNCA diga endereço exato do imóvel (se for imobiliário).",
            "- SEJA DIRETO: No WhatsApp, menos é mais. Máximo 3 parágrafos.",
            "- NÃO peça o telefone de volta (você já está no WhatsApp!).",
        ]

    if business_rules:
        prompt_lines.append("\n# REGRAS ESPECÍFICAS")
        for rule in business_rules:
            prompt_lines.append(f"- {rule}")

    if questions_to_ask:
        prompt_lines.append("\n# O QUE VOCÊ PRECISA DESCOBRIR")
        for q in questions_to_ask:
            prompt_lines.append(f"- {q}")

    if custom_prompt:
        prompt_lines.append("\n# INSTRUÇÕES ADICIONAIS DO TENANT")
        prompt_lines.append(custom_prompt)

    if faq_items:
        prompt_lines.append("\n# FAQ / CONHECIMENTO")
        for item in faq_items[:5]: # Limita a 5 itens para não explodir tokens
            prompt_lines.append(f"P: {item.get('question')}\nR: {item.get('answer')}\n")

    return "\n".join(prompt_lines)


__all__ = [
    "NicheConfig",
    "NICHE_TEMPLATES",
    "NICHE_SPECIFIC_TEMPLATES",
    "get_niche_config",
    "get_available_niches",
    "build_system_prompt",
]