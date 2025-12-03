"""Casos de uso da aplicação."""

from .process_message import process_message, get_or_create_lead, get_conversation_history

__all__ = [
    "process_message",
    "get_or_create_lead", 
    "get_conversation_history",
]
