"""
SISTEMA DE QUALIFICAÇÃO INTELIGENTE DE LEADS - VERSÃO CORRIGIDA
=================================================================
CORREÇÃO: Regex simplificados para detectar orçamento e prazo corretamente.
"""

import re
import logging
from typing import List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LeadQualifier:
    """
    Qualifica leads baseado em análise contextual da conversa.
    
    VERSÃO CORRIGIDA: Padrões simplificados que realmente funcionam!
    """
    
    def __init__(self):
        # SINAIS DE LEAD QUENTE (cada um vale pontos)
        self.hot_patterns = {
            # ✅ ORÇAMENTO DEFINIDO (25 pontos) - SIMPLIFICADO
            r"tenho\s+\d+\s*k": 25,  # "tenho 550k"
            r"tenho\s+\d+\s+mil": 25,  # "tenho 550 mil"
            r"orçamento.*\d+\s*k": 20,  # "orçamento 550k"
            r"orçamento.*\d+\s+mil": 20,  # "orçamento 550 mil"
            r"orcamento.*\d+\s*k": 20,
            r"orcamento.*\d+\s+mil": 20,
            
            # Aprovado (25 pontos)
            r"aprovado.*banco": 25,
            r"financiamento.*aprovado": 25,
            r"nome saiu": 25,
            
            # ✅ URGÊNCIA COM PRAZO (25 pontos) - SIMPLIFICADO
            r"preciso.*mudar.*\d+\s+mes": 25,  # "preciso mudar em 2 meses"
            r"preciso.*me\s+mudar.*\d+\s+mes": 25,  # "preciso me mudar em 3 meses"
            r"mudar.*em.*\d+\s+mes": 20,  # "mudar em 3 meses"
            r"mudança.*\d+\s+mes": 20,  # "mudança em 3 meses"
            r"prazo.*\d+\s+mes": 20,  # "prazo de 2 meses"
            
            # Urgência extrema
            r"urgente": 20,
            r"preciso\s+(hoje|amanhã|logo|rapido|rápido)": 20,
            
            # Quer avançar (20 pontos)
            r"quando.*posso.*visitar": 20,
            r"quero.*visitar": 20,
            r"pode.*agendar": 15,
            
            # Pergunta sobre processo (15 pontos)
            r"que.*documentos.*preciso": 15,
            r"como.*funciona.*(compra|financiamento)": 15,
            
            # Tem recurso (20 pontos)
            r"tenho.*entrada": 20,
            r"vendendo.*imovel": 20,
            r"vou\s+receber": 15,
            
            # Decisão tomada
            r"já.*decid": 15,
            r"tenho\s+certeza": 15,
        }
        
        # SINAIS DE LEAD MORNO (cada um vale pontos)
        self.warm_patterns = {
            # ✅ ORÇAMENTO MENCIONADO (15 pontos) - SIMPLIFICADO
            r"até.*\d+\s*k": 15,  # "até 550k"
            r"até.*\d+\s+mil": 15,  # "até 550 mil"
            r"em\s+torno.*\d+\s+mil": 15,  # "em torno de 550 mil"
            r"cerca\s+de.*\d+\s+mil": 15,  # "cerca de 550 mil"
            
            # ✅ PRAZO MENCIONADO (10 pontos) - SIMPLIFICADO  
            r"mudar.*próximos.*\d+": 10,  # "mudar nos próximos 3 meses"
            r"mudança.*\d+\s+a\s+\d+\s+mes": 10,  # "mudança em 3 a 6 meses"
            
            # Pesquisando
            r"pesquisando": 10,
            r"procurando": 10,
            r"comparando": 10,
            
            # Precisa alinhar
            r"preciso.*conversar.*(esposa|marido|família)": 10,
            r"vou.*pensar": 5,
        }
        
        # SINAIS DE LEAD FRIO (cada um REMOVE pontos)
        self.cold_patterns = {
            r"só.*olhando": -20,
            r"só.*curiosidade": -20,
            r"talvez.*um\s+dia": -20,
            r"sem.*previsão": -15,
            r"muito\s+caro": -10,
        }
    
    def qualify(
        self,
        lead,
        messages: List,
        conversation_text: str = None
    ) -> Dict:
        """Qualifica o lead baseado na conversa."""
        
        # Prepara texto da conversa
        if not conversation_text:
            conversation_text = " ".join([
                m.content for m in messages 
                if hasattr(m, 'content') and m.content
            ])
        
        conversation_lower = conversation_text.lower()
        
        # Remove acentos para facilitar match
        conversation_normalized = self._normalize_text(conversation_lower)
        
        # Análise de pontuação
        score = 0
        signals = {"hot": [], "warm": [], "cold": []}
        reasons = []
        
        # 1. ANALISA PADRÕES QUENTES
        for pattern, points in self.hot_patterns.items():
            if re.search(pattern, conversation_normalized, re.IGNORECASE):
                score += points
                signals["hot"].append(pattern[:30])
                logger.info(f"✅ Hot pattern detectado: {pattern} (+{points})")
        
        # 2. ANALISA PADRÕES MORNOS
        for pattern, points in self.warm_patterns.items():
            if re.search(pattern, conversation_normalized, re.IGNORECASE):
                score += points
                signals["warm"].append(pattern[:30])
                logger.info(f"✅ Warm pattern detectado: {pattern} (+{points})")
        
        # 3. ANALISA PADRÕES FRIOS
        for pattern, points in self.cold_patterns.items():
            if re.search(pattern, conversation_normalized, re.IGNORECASE):
                score += points
                signals["cold"].append(pattern[:30])
                logger.info(f"⚠️ Cold pattern detectado: {pattern} ({points})")
        
        # 4. ANÁLISE DE ENGAJAMENTO (CORRIGIDA)
        engagement_score, engagement_reason = self._analyze_engagement(messages, lead)
        score += engagement_score
        if engagement_reason:
            reasons.append(engagement_reason)
        
        # ✅ CLASSIFICAÇÃO FINAL (THRESHOLDS AJUSTADOS)
        if score >= 35:  # ✅ REDUZIDO de 40 para 35
            qualification = "hot"
            confidence = min(score / 100, 1.0)
            reasons.insert(0, "Lead com orçamento e prazo definidos")
        elif score >= 15:  # ✅ REDUZIDO de 20 para 15
            qualification = "warm"
            confidence = min(score / 60, 0.9)
            reasons.insert(0, "Lead com interesse genuíno")
        else:
            qualification = "cold"
            confidence = max(0.3, 1.0 - abs(score) / 40)
            reasons.insert(0, "Lead em fase inicial")
        
        result = {
            "qualification": qualification,
            "score": score,
            "confidence": round(confidence, 2),
            "reasons": reasons[:3],
            "signals": {
                "hot": signals["hot"][:3],
                "warm": signals["warm"][:3],
                "cold": signals["cold"][:3],
            }
        }
        
        logger.info(f"🎯 Lead {lead.id} qualificado: {qualification.upper()} (score: {score}, confiança: {confidence:.2f})")
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Remove acentos para facilitar matching."""
        replacements = {
            'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
            'é': 'e', 'ê': 'e',
            'í': 'i',
            'ó': 'o', 'ô': 'o', 'õ': 'o',
            'ú': 'u', 'ü': 'u',
            'ç': 'c',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    def _analyze_engagement(self, messages: List, lead) -> tuple:
        """Analisa engajamento na conversa."""
        score = 0
        reason = None
        
        user_messages = [m for m in messages if m.role == "user"]
        
        # ✅ REDUZIDO impacto negativo para leads novos
        if len(user_messages) >= 6:
            score += 10
            reason = "Alto engajamento"
        elif len(user_messages) >= 4:
            score += 5
            reason = "Bom engajamento"
        elif len(user_messages) >= 2:
            score += 0  # Neutro
            reason = None
        else:
            score -= 0  # ✅ NÃO penaliza mais leads novos!
            reason = None
        
        # Tamanho médio das mensagens
        if user_messages:
            avg_length = sum(len(m.content) for m in user_messages) / len(user_messages)
            
            if avg_length > 60:  # ✅ Mensagem longa = mais interessado
                score += 5
        
        return score, reason
    
    def should_requalify(self, lead, last_qualification_at) -> bool:
        """Verifica se lead deve ser re-qualificado."""
        if not last_qualification_at:
            return True
        
        time_since_qualification = datetime.utcnow() - last_qualification_at
        
        # Re-qualifica a cada 24h
        if time_since_qualification > timedelta(hours=24):
            return True
        
        # Re-qualifica se teve atividade recente
        if hasattr(lead, 'last_message_at'):
            if lead.last_message_at > last_qualification_at:
                return True
        
        return False


# Instância global
qualifier = LeadQualifier()


def qualify_lead(lead, messages, conversation_text=None):
    """Helper function para usar o qualificador."""
    return qualifier.qualify(lead, messages, conversation_text)