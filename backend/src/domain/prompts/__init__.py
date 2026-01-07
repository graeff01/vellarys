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
    company_name: str = "Velaris"
    
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


def build_system_prompt(*args, **kwargs) -> str:
    """
    Função legacy - não usa mais.
    Prompts agora são inline no process_message.py
    """
    return ""


__all__ = [
    "NicheConfig",
    "NICHE_TEMPLATES",
    "NICHE_SPECIFIC_TEMPLATES",
    "get_niche_config",
    "get_available_niches",
    "build_system_prompt",
]