"""Templates de prompts por nicho."""
from .niche_templates import (
    NicheConfig,
    NICHE_SPECIFIC_TEMPLATES,
    get_niche_config,
    get_available_niches,
    build_system_prompt,
)

# Alias para compatibilidade atualizado 
NICHE_TEMPLATES = NICHE_SPECIFIC_TEMPLATES

__all__ = [
    "NicheConfig",
    "NICHE_TEMPLATES",
    "NICHE_SPECIFIC_TEMPLATES",
    "get_niche_config",
    "get_available_niches",
    "build_system_prompt",
]