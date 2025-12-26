"""
Services de aplicação.
"""

from .ai_context_builder import (
    # Data Classes
    AIContext,
    LeadContext,
    EmpreendimentoContext,
    ImovelPortalContext,
    PromptBuildResult,
    
    # Funções principais
    migrate_settings_if_needed,
    extract_ai_context,
    build_complete_prompt,
    
    # Funções de construção de contexto
    build_empreendimento_context,
    build_imovel_portal_context,
    build_lead_info_context,
    build_security_instructions,
    
    # Funções de conversão
    empreendimento_to_context,
    lead_to_context,
    imovel_dict_to_context,
    
    # Funções de detecção
    detect_hot_lead_signals,
    analyze_qualification_from_message,
)

__all__ = [
    "AIContext",
    "LeadContext", 
    "EmpreendimentoContext",
    "ImovelPortalContext",
    "PromptBuildResult",
    "migrate_settings_if_needed",
    "extract_ai_context",
    "build_complete_prompt",
    "build_empreendimento_context",
    "build_imovel_portal_context",
    "build_lead_info_context",
    "build_security_instructions",
    "empreendimento_to_context",
    "lead_to_context",
    "imovel_dict_to_context",
    "detect_hot_lead_signals",
    "analyze_qualification_from_message",
]