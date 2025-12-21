"""
SISTEMA DE QUALIFICAÇÃO INTELIGENTE DE LEADS - VERSÃO ULTRA GENÉRICA
=====================================================================
CORREÇÃO FINAL: Padrões que detectam QUALQUER variação!
"""

import re
import logging
from typing import List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LeadQualifier:
    """
    Qualifica leads baseado em análise contextual da conversa.
    
    VERSÃO ULTRA GENÉRICA: Pega qualquer variação de orçamento/urgência!
    """
    
    def __init__(self):
        # SINAIS DE LEAD QUENTE (cada um vale pontos)
        self.hot_patterns = {
            # ═══════════════════════════════════════════════════════════
            # ORÇAMENTO DEFINIDO (30 pontos) - ULTRA GENÉRICO
            # ═══════════════════════════════════════════════════════════
            r"tenho\s+\d+": 30,  # "tenho 800", "tenho 600 mil", "tenho 550k"
            r"\d+\s+mil.*guardado": 30,  # "800 mil guardado"
            r"\d+\s+mil.*entrada": 30,  # "600 mil de entrada"
            r"\d+\s+mil.*disponivel": 30,  # "500 mil disponível"
            r"orcamento.*\d+": 25,  # "orçamento 550k", "orçamento de 600 mil"
            
            # ═══════════════════════════════════════════════════════════
            # APROVAÇÕES (30 pontos)
            # ═══════════════════════════════════════════════════════════
            r"financiamento.*aprovado": 30,
            r"aprovado.*banco": 30,
            r"aprovado.*caixa": 30,
            r"pre.*aprovado": 30,
            r"credito.*aprovado": 30,
            r"nome\s+saiu": 30,
            
            # ═══════════════════════════════════════════════════════════
            # URGÊNCIA (30 pontos) - DIAS OU MESES
            # ═══════════════════════════════════════════════════════════
            r"urgente": 25,
            r"urgencia": 25,
            
            # DIAS
            r"em\s+\d+\s+dia": 30,  # "em 15 dias", "em 30 dias"
            r"\d+\s+dia.*prazo": 30,  # "15 dias de prazo"
            r"preciso.*\d+\s+dia": 30,  # "preciso em 15 dias"
            
            # MESES
            r"em\s+\d+\s+mes": 25,  # "em 2 meses", "em 1 mes"
            r"\d+\s+mes.*prazo": 25,  # "2 meses de prazo"
            r"preciso.*\d+\s+mes": 25,  # "preciso em 2 meses"
            r"mudar.*\d+\s+mes": 25,  # "mudar em 3 meses"
            
            # HOJE/AMANHÃ
            r"preciso\s+(hoje|amanha|agora|ja)": 30,
            r"quero\s+(hoje|amanha|agora|ja)": 25,
            
            # ═══════════════════════════════════════════════════════════
            # VISITAS (25 pontos)
            # ═══════════════════════════════════════════════════════════
            r"agendar.*visita": 25,
            r"visita.*amanha": 30,
            r"visita.*hoje": 30,
            r"posso.*visitar": 25,
            r"quero.*visitar": 25,
            r"quando.*visitar": 20,
            r"marcar.*visita": 25,
            
            # ═══════════════════════════════════════════════════════════
            # DECISÃO (20 pontos)
            # ═══════════════════════════════════════════════════════════
            r"quero\s+comprar": 25,
            r"vou\s+comprar": 25,
            r"ja.*decid": 25,
            r"fecho.*negocio": 30,
            r"aceito.*proposta": 25,
            r"estou\s+pronto": 20,
            
            # ═══════════════════════════════════════════════════════════
            # PROCESSO (15 pontos)
            # ═══════════════════════════════════════════════════════════
            r"quais.*documentos": 15,
            r"que.*documentos": 15,
            r"como.*funciona.*(compra|financiamento)": 15,
            r"como.*comprar": 15,
            
            # ═══════════════════════════════════════════════════════════
            # RECURSOS (20 pontos)
            # ═══════════════════════════════════════════════════════════
            r"tenho.*entrada": 25,
            r"vendendo.*imovel": 20,
            r"vou.*receber.*fgts": 20,
            r"tenho.*fgts": 20,
        }
        
        # SINAIS DE LEAD MORNO (cada um vale pontos)
        self.warm_patterns = {
            # Orçamento vago
            r"ate.*\d+": 15,  # "até 550k"
            r"em\s+torno.*\d+": 15,  # "em torno de 550 mil"
            r"cerca.*\d+": 15,  # "cerca de 500 mil"
            r"mais.*menos.*\d+": 15,  # "mais ou menos 600 mil"
            
            # Prazo vago
            r"proximos.*mes": 10,  # "próximos meses"
            r"alguns.*mes": 10,  # "alguns meses"
            
            # Pesquisando
            r"pesquisando": 10,
            r"procurando": 10,
            r"comparando": 10,
            r"analisando": 10,
            
            # Precisa alinhar
            r"conversar.*(esposa|marido|familia)": 10,
            r"decidir.*(esposa|marido|familia)": 10,
            r"vou.*pensar": 5,
            r"preciso.*analisar": 5,
        }
        
        # SINAIS DE LEAD FRIO (cada um REMOVE pontos)
        self.cold_patterns = {
            r"so.*olhando": -20,
            r"so.*curiosidade": -20,
            r"talvez.*um\s+dia": -20,
            r"sem.*previsao": -15,
            r"muito\s+caro": -10,
            r"nao.*tenho.*dinheiro": -25,
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
        
        logger.info(f"🔍 Analisando texto (primeiros 200 chars): {conversation_normalized[:200]}")
        
        # Análise de pontuação
        score = 0
        signals = {"hot": [], "warm": [], "cold": []}
        reasons = []
        matched_patterns = []
        
        # 1. ANALISA PADRÕES QUENTES
        for pattern, points in self.hot_patterns.items():
            matches = re.findall(pattern, conversation_normalized, re.IGNORECASE)
            if matches:
                score += points
                signals["hot"].append(pattern[:40])
                matched_patterns.append(f"HOT: {pattern[:40]} → +{points}")
                logger.info(f"🔥 HOT: {pattern[:50]} (+{points}) | Matches: {matches[:2]}")
        
        # 2. ANALISA PADRÕES MORNOS
        for pattern, points in self.warm_patterns.items():
            matches = re.findall(pattern, conversation_normalized, re.IGNORECASE)
            if matches:
                score += points
                signals["warm"].append(pattern[:40])
                matched_patterns.append(f"WARM: {pattern[:40]} → +{points}")
                logger.info(f"🌡️ WARM: {pattern[:50]} (+{points}) | Matches: {matches[:2]}")
        
        # 3. ANALISA PADRÕES FRIOS
        for pattern, points in self.cold_patterns.items():
            matches = re.findall(pattern, conversation_normalized, re.IGNORECASE)
            if matches:
                score += points
                signals["cold"].append(pattern[:40])
                matched_patterns.append(f"COLD: {pattern[:40]} → {points}")
                logger.info(f"❄️ COLD: {pattern[:50]} ({points}) | Matches: {matches[:2]}")
        
        # 4. ANÁLISE DE ENGAJAMENTO
        engagement_score, engagement_reason = self._analyze_engagement(messages, lead)
        score += engagement_score
        if engagement_reason:
            reasons.append(engagement_reason)
            logger.info(f"💬 Engajamento: {engagement_reason} (+{engagement_score})")
        
        # Log de padrões detectados
        if matched_patterns:
            logger.info(f"📊 Padrões detectados ({len(matched_patterns)}):")
            for p in matched_patterns[:10]:
                logger.info(f"   {p}")
        else:
            logger.warning(f"⚠️ NENHUM padrão detectado!")
        
        # ✅ CLASSIFICAÇÃO FINAL
        if score >= 40:  # Threshold para QUENTE
            qualification = "hot"
            confidence = min(score / 100, 1.0)
            reasons.insert(0, "Lead pronto para comprar")
        elif score >= 15:  # Threshold para MORNO
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
                "hot": signals["hot"][:5],
                "warm": signals["warm"][:5],
                "cold": signals["cold"][:3],
            }
        }
        
        logger.info(
            f"🎯 Lead {lead.id} qualificado: {qualification.upper()} "
            f"(score: {score}, confiança: {confidence:.2f})"
        )
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Remove acentos para facilitar matching."""
        replacements = {
            'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
            'é': 'e', 'ê': 'e', 'è': 'e',
            'í': 'i', 'ì': 'i',
            'ó': 'o', 'ô': 'o', 'õ': 'o', 'ò': 'o',
            'ú': 'u', 'ü': 'u', 'ù': 'u',
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
        
        if len(user_messages) >= 6:
            score += 10
            reason = "Alto engajamento (6+ mensagens)"
        elif len(user_messages) >= 4:
            score += 5
            reason = "Bom engajamento (4+ mensagens)"
        elif len(user_messages) >= 2:
            score += 2
            reason = None
        
        # Tamanho médio das mensagens
        if user_messages:
            avg_length = sum(len(m.content) for m in user_messages) / len(user_messages)
            
            if avg_length > 80:
                score += 10
            elif avg_length > 60:
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