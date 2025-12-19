"""
SISTEMA DE QUALIFICAÇÃO INTELIGENTE DE LEADS
=============================================
Analisa contexto real da conversa para qualificar leads corretamente.
"""

import re
import logging
from typing import List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LeadQualifier:
    """
    Qualifica leads baseado em análise contextual da conversa.
    
    Não se baseia apenas em palavras-chave, mas analisa:
    - Orçamento definido vs indefinido
    - Urgência real vs apenas interesse
    - Engajamento na conversa
    - Sinais de decisão
    """
    
    def __init__(self):
        # SINAIS DE LEAD QUENTE (cada um vale pontos)
        self.hot_patterns = {
            # Orçamento aprovado (25 pontos)
            r"(tenho|possuo|consegui|saiu|aprovado|aprovada).{0,20}(entrada|dinheiro|recurso|grana)": 25,
            r"(aprovado|aprovada|pré-aprovado).{0,20}(banco|financiamento|crédito)": 25,
            r"nome saiu.{0,30}(compra assistida|minha casa minha vida|programa)": 25,
            
            # Urgência real com prazo (20 pontos)
            r"preciso.{0,20}mudar.{0,20}em.{0,20}[0-9]+.{0,10}(mes|meses|semana)": 20,
            r"(casamento|mudança|trabalho novo).{0,20}em.{0,20}(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)": 20,
            r"urgente|preciso.{0,10}(hoje|amanhã|essa semana|logo)": 15,
            
            # Quer avançar no processo (20 pontos)
            r"quando.{0,20}(posso|podemos|dá pra|pode).{0,20}(visitar|conhecer|ver)": 20,
            r"(quero|gostaria de|preciso).{0,20}(visitar|conhecer|agendar)": 20,
            
            # Pergunta sobre documentação/processo (15 pontos)
            r"(que|quais).{0,20}documentos?.{0,20}(preciso|necessário|precisa)": 15,
            r"como.{0,20}(funciona|é|faz).{0,20}(compra|financiamento|processo)": 15,
            r"o que preciso.{0,20}para.{0,20}(comprar|alugar)": 15,
            
            # Tem recurso disponível (20 pontos)
            r"(tenho|possuo).{0,20}[0-9]+.{0,10}(mil|k|reais).{0,20}(guardado|disponível|de entrada)": 20,
            r"(vendendo|vendi).{0,20}(meu|minha).{0,20}(casa|apartamento|imóvel)": 20,
            r"vou receber.{0,20}(herança|venda|indenização)": 15,
            
            # Decisão tomada (15 pontos)
            r"(já|ja).{0,20}decid(i|imos)": 15,
            r"(tenho certeza|com certeza|definitivamente)": 15,
        }
        
        # SINAIS DE LEAD MORNO (cada um vale pontos)
        self.warm_patterns = {
            r"(estou|to).{0,20}(pesquisando|procurando|vendo|buscando)": 10,
            r"(comparando|avaliando).{0,20}(opções|imóveis|preços)": 10,
            r"(próximos|nos próximos).{0,20}[0-9]+.{0,20}meses": 10,
            r"preciso.{0,20}(conversar|falar).{0,20}(esposa|marido|família)": 10,
            r"(vou|vamos).{0,20}pensar": 5,
        }
        
        # SINAIS DE LEAD FRIO (cada um REMOVE pontos)
        self.cold_patterns = {
            r"só.{0,20}(olhando|vendo|curiosidade)": -20,
            r"(talvez|quem sabe|pode ser).{0,20}(um dia|futuramente|ano que vem)": -20,
            r"sem.{0,20}(previsão|prazo|data|urgência)": -15,
            r"(muito caro|tá caro|caro demais)": -10,  # Objeção sem solução
            r"^(ok|sim|não sei|talvez)$": -5,  # Respostas curtas
        }
    
    def qualify(
        self,
        lead,
        messages: List,
        conversation_text: str = None
    ) -> Dict:
        """
        Qualifica o lead baseado na conversa.
        
        Args:
            lead: Objeto Lead
            messages: Lista de mensagens da conversa
            conversation_text: Texto completo da conversa (opcional)
        
        Returns:
            {
                "qualification": "hot|warm|cold",
                "score": 0-100,
                "confidence": 0.0-1.0,
                "reasons": ["razão 1", "razão 2"],
                "signals": {"hot": [], "warm": [], "cold": []}
            }
        """
        
        # Prepara texto da conversa
        if not conversation_text:
            conversation_text = " ".join([
                m.content for m in messages 
                if hasattr(m, 'content') and m.content
            ])
        
        conversation_lower = conversation_text.lower()
        
        # Análise de pontuação
        score = 0
        signals = {"hot": [], "warm": [], "cold": []}
        reasons = []
        
        # 1. ANALISA PADRÕES QUENTES
        for pattern, points in self.hot_patterns.items():
            matches = re.finditer(pattern, conversation_lower, re.IGNORECASE)
            for match in matches:
                score += points
                signal = match.group(0)[:50]  # Limita tamanho
                signals["hot"].append(signal)
                logger.debug(f"Hot signal encontrado: {signal} (+{points})")
        
        # 2. ANALISA PADRÕES MORNOS
        for pattern, points in self.warm_patterns.items():
            matches = re.finditer(pattern, conversation_lower, re.IGNORECASE)
            for match in matches:
                score += points
                signal = match.group(0)[:50]
                signals["warm"].append(signal)
                logger.debug(f"Warm signal encontrado: {signal} (+{points})")
        
        # 3. ANALISA PADRÕES FRIOS
        for pattern, points in self.cold_patterns.items():
            matches = re.finditer(pattern, conversation_lower, re.IGNORECASE)
            for match in matches:
                score += points  # Já é negativo
                signal = match.group(0)[:50]
                signals["cold"].append(signal)
                logger.debug(f"Cold signal encontrado: {signal} ({points})")
        
        # 4. ANÁLISE DE ORÇAMENTO
        budget_score, budget_reason = self._analyze_budget(conversation_lower, lead)
        score += budget_score
        if budget_reason:
            reasons.append(budget_reason)
        
        # 5. ANÁLISE DE ENGAJAMENTO
        engagement_score, engagement_reason = self._analyze_engagement(messages, lead)
        score += engagement_score
        if engagement_reason:
            reasons.append(engagement_reason)
        
        # 6. ANÁLISE DE URGÊNCIA
        urgency_score, urgency_reason = self._analyze_urgency(conversation_lower)
        score += urgency_score
        if urgency_reason:
            reasons.append(urgency_reason)
        
        # CLASSIFICAÇÃO FINAL
        if score >= 40:
            qualification = "hot"
            confidence = min(score / 100, 1.0)
        elif score >= 15:
            qualification = "warm"
            confidence = min(score / 60, 0.8)
        else:
            qualification = "cold"
            confidence = max(0.3, 1.0 - abs(score) / 40)
        
        # Monta razões principais
        if not reasons:
            if qualification == "hot":
                reasons = ["Múltiplos sinais de compra identificados"]
            elif qualification == "warm":
                reasons = ["Interesse genuíno sem urgência"]
            else:
                reasons = ["Baixo engajamento ou interesse inicial"]
        
        result = {
            "qualification": qualification,
            "score": score,
            "confidence": round(confidence, 2),
            "reasons": reasons[:3],  # Top 3 razões
            "signals": {
                "hot": signals["hot"][:3],
                "warm": signals["warm"][:3],
                "cold": signals["cold"][:3],
            }
        }
        
        logger.info(f"Lead {lead.id} qualificado: {qualification} (score: {score}, confiança: {confidence:.2f})")
        
        return result
    
    def _analyze_budget(self, text: str, lead) -> tuple:
        """Analisa menções de orçamento."""
        score = 0
        reason = None
        
        # Busca menções de valores
        budget_patterns = [
            r"[0-9]+\s*(mil|k|reais)",
            r"r\$\s*[0-9]+",
            r"orçamento.{0,20}[0-9]+",
            r"até.{0,20}[0-9]+.{0,10}(mil|reais)",
        ]
        
        for pattern in budget_patterns:
            if re.search(pattern, text):
                score += 15
                reason = "Orçamento definido"
                break
        
        # Se tem orçamento no lead
        if hasattr(lead, 'budget') and lead.budget:
            score += 10
            reason = f"Orçamento: R$ {lead.budget:,.0f}"
        
        return score, reason
    
    def _analyze_engagement(self, messages: List, lead) -> tuple:
        """Analisa engajamento na conversa."""
        score = 0
        reason = None
        
        user_messages = [m for m in messages if m.role == "user"]
        
        # Quantidade de mensagens
        if len(user_messages) >= 8:
            score += 15
            reason = "Alto engajamento (8+ mensagens)"
        elif len(user_messages) >= 5:
            score += 10
            reason = "Engajamento moderado"
        elif len(user_messages) <= 2:
            score -= 10
            reason = "Baixo engajamento"
        
        # Tamanho médio das mensagens
        if user_messages:
            avg_length = sum(len(m.content) for m in user_messages) / len(user_messages)
            if avg_length > 100:
                score += 10  # Respostas detalhadas
            elif avg_length < 20:
                score -= 5  # Respostas muito curtas
        
        # Tempo de resposta (se disponível)
        if len(user_messages) >= 2:
            response_times = []
            for i in range(1, len(user_messages)):
                time_diff = user_messages[i].created_at - messages[messages.index(user_messages[i-1]) - 1].created_at
                response_times.append(time_diff.total_seconds())
            
            avg_response_time = sum(response_times) / len(response_times)
            
            # Responde rápido = mais interessado
            if avg_response_time < 300:  # < 5 min
                score += 5
        
        return score, reason
    
    def _analyze_urgency(self, text: str) -> tuple:
        """Analisa urgência mencionada."""
        score = 0
        reason = None
        
        # Urgência extrema
        extreme_urgency = [
            "urgente", "hoje", "amanhã", "essa semana",
            "preciso logo", "o mais rápido possível"
        ]
        
        for word in extreme_urgency:
            if word in text:
                score += 15
                reason = "Urgência alta"
                break
        
        # Prazo definido
        if re.search(r"(em|dentro de|até).{0,20}[0-9]+.{0,10}(dia|semana|mes)", text):
            score += 10
            if not reason:
                reason = "Prazo definido"
        
        # Sem urgência
        no_urgency = ["sem pressa", "sem urgência", "com calma", "quando der"]
        for phrase in no_urgency:
            if phrase in text:
                score -= 10
                reason = "Sem urgência"
                break
        
        return score, reason
    
    def should_requalify(self, lead, last_qualification_at) -> bool:
        """
        Verifica se lead deve ser re-qualificado.
        
        Re-qualifica se:
        - Última qualificação foi há mais de 24h
        - Lead teve novas mensagens
        - Mudança significativa na conversa
        """
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