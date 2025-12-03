"""Templates de prompts por nicho."""

from .niche_templates import (
    NicheConfig,
    NICHE_TEMPLATES,
    get_niche_config,
    get_available_niches,
    build_system_prompt,
)

__all__ = [
    "NicheConfig",
    "NICHE_TEMPLATES", 
    "get_niche_config",
    "get_available_niches",
    "build_system_prompt",
]
