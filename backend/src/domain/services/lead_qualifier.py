"""
SISTEMA DE QUALIFICAÇÃO INTELIGENTE DE LEADS - VERSÃO MELHORADA
=================================================================
Analisa contexto real da conversa para qualificar leads corretamente.

MELHORIAS:
- ✅ Detecção precisa de orçamento ("550 mil", "em torno de", "até")
- ✅ Detecção de prazo ("me mudar em 3 meses", "até 3 meses")
- ✅ Engajamento corrigido (4 mensagens = positivo)
- ✅ Thresholds ajustados (warm >= 20, hot >= 40)
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
            r"(tenho|possuo|consegui|saiu|aprovado|aprovada).{0,30}(entrada|dinheiro|recurso|grana|valor)": 25,
            r"(aprovado|aprovada|pré-aprovado|pre-aprovado).{0,30}(banco|financiamento|crédito|credito)": 25,
            r"nome saiu.{0,40}(compra assistida|minha casa|programa)": 25,
            
            # Urgência real com prazo (20 pontos)
            r"(preciso|quero|tenho que).{0,20}mudar.{0,20}(em|até|dentro de).{0,20}[0-9]+.{0,15}(dia|semana|mes|meses)": 20,
            r"(casamento|mudança|trabalho novo|novo emprego).{0,30}(em|até|dentro de).{0,20}[0-9]+.{0,15}(mes|meses)": 20,
            r"urgente|preciso.{0,15}(hoje|amanhã|essa semana|logo|rapido|rápido)": 15,
            r"prazo.{0,20}(curto|apertado|urgente)": 15,
            
            # Quer avançar no processo (20 pontos)
            r"quando.{0,20}(posso|podemos|dá pra|pode).{0,20}(visitar|conhecer|ver|agendar)": 20,
            r"(quero|gostaria de|preciso).{0,20}(visitar|conhecer|agendar|ver)": 20,
            r"pode.{0,20}agendar": 15,
            
            # Pergunta sobre documentação/processo (15 pontos)
            r"(que|quais).{0,30}documentos?.{0,30}(preciso|necessário|precisa|necessita)": 15,
            r"como.{0,20}(funciona|é|faz|fazer).{0,30}(compra|financiamento|processo|aquisição)": 15,
            r"o que preciso.{0,30}para.{0,30}(comprar|alugar|adquirir)": 15,
            
            # Tem recurso disponível (20 pontos)
            r"(tenho|possuo|disponho|dispor).{0,30}[0-9]+.{0,15}(mil|k|reais).{0,30}(guardado|disponível|de entrada|entrada)": 20,
            r"(vendendo|vendi|vou vender).{0,30}(meu|minha).{0,30}(casa|apartamento|imóvel|imovel)": 20,
            r"vou receber.{0,30}(herança|venda|indenização|indenizacao)": 15,
            
            # Decisão tomada (15 pontos)
            r"(já|ja).{0,20}decid(i|imos|ido)": 15,
            r"(tenho certeza|com certeza|definitivamente|decidido)": 15,
        }
        
        # SINAIS DE LEAD MORNO (cada um vale pontos)
        self.warm_patterns = {
            # Pesquisando ativamente
            r"(estou|to|tô).{0,20}(pesquisando|procurando|vendo|buscando|olhando)": 10,
            r"(comparando|avaliando|analisando).{0,30}(opções|imóveis|imoveis|preços|precos)": 10,
            
            # Prazo médio/longo
            r"(próximos|proximos|nos próximos|nos proximos).{0,20}[0-9]+.{0,20}(mes|meses|semana)": 10,
            
            # Precisa alinhar com terceiros
            r"preciso.{0,30}(conversar|falar|discutir).{0,30}(esposa|marido|família|familia|cônjuge|conjuge)": 10,
            r"(vou|vamos).{0,20}pensar": 5,
            
            # ✅ NOVO - Orçamento mencionado (não aprovado, mas definido)
            r"(orçamento|orcamento).{0,30}(de|é|eh|fica|em torno|cerca|aproximadamente).{0,30}[0-9]+": 15,
            r"(até|ate|em torno|cerca de).{0,30}[0-9]+.{0,15}(mil|k|reais)": 15,
            
            # ✅ NOVO - Prazo mencionado (não urgente, mas definido)
            r"(me mudar|mudar|mudança|mudanca).{0,30}(em|até|ate|dentro de).{0,30}[0-9]+": 10,
            r"(ideia|plano|pretendo).{0,30}(mudar|me mudar).{0,30}(em|até|ate).{0,30}[0-9]+": 10,
        }
        
        # SINAIS DE LEAD FRIO (cada um REMOVE pontos)
        self.cold_patterns = {
            r"só.{0,20}(olhando|vendo|curiosidade|curioso)": -20,
            r"(talvez|quem sabe|pode ser|sei lá|sei la).{0,30}(um dia|futuramente|ano que vem|no futuro)": -20,
            r"sem.{0,20}(previsão|previsao|prazo|data|urgência|urgencia)": -15,
            r"(muito caro|tá caro|ta caro|caro demais)": -10,
            r"^(ok|sim|não sei|nao sei|talvez)$": -5,
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
                signal = match.group(0)[:50]
                signals["hot"].append(signal)
                logger.debug(f"Hot signal: {signal} (+{points})")
        
        # 2. ANALISA PADRÕES MORNOS
        for pattern, points in self.warm_patterns.items():
            matches = re.finditer(pattern, conversation_lower, re.IGNORECASE)
            for match in matches:
                score += points
                signal = match.group(0)[:50]
                signals["warm"].append(signal)
                logger.debug(f"Warm signal: {signal} (+{points})")
        
        # 3. ANALISA PADRÕES FRIOS
        for pattern, points in self.cold_patterns.items():
            matches = re.finditer(pattern, conversation_lower, re.IGNORECASE)
            for match in matches:
                score += points
                signal = match.group(0)[:50]
                signals["cold"].append(signal)
                logger.debug(f"Cold signal: {signal} ({points})")
        
        # 4. ANÁLISE DE ORÇAMENTO (MELHORADA)
        budget_score, budget_reason = self._analyze_budget(conversation_lower, lead)
        score += budget_score
        if budget_reason:
            reasons.append(budget_reason)
        
        # 5. ANÁLISE DE ENGAJAMENTO (CORRIGIDA)
        engagement_score, engagement_reason = self._analyze_engagement(messages, lead)
        score += engagement_score
        if engagement_reason:
            reasons.append(engagement_reason)
        
        # 6. ANÁLISE DE URGÊNCIA (MELHORADA)
        urgency_score, urgency_reason = self._analyze_urgency(conversation_lower)
        score += urgency_score
        if urgency_reason:
            reasons.append(urgency_reason)
        
        # CLASSIFICAÇÃO FINAL (THRESHOLDS AJUSTADOS)
        if score >= 40:
            qualification = "hot"
            confidence = min(score / 100, 1.0)
        elif score >= 20:  # ✅ AJUSTADO (era 15)
            qualification = "warm"
            confidence = min(score / 60, 0.9)
        else:
            qualification = "cold"
            confidence = max(0.3, 1.0 - abs(score) / 40)
        
        # Monta razões principais
        if not reasons:
            if qualification == "hot":
                reasons = ["Múltiplos sinais de compra identificados"]
            elif qualification == "warm":
                reasons = ["Interesse genuíno com orçamento/prazo definido"]
            else:
                reasons = ["Baixo engajamento ou interesse inicial"]
        
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
        
        logger.info(f"Lead {lead.id} qualificado: {qualification} (score: {score}, confiança: {confidence:.2f})")
        
        return result
    
    def _analyze_budget(self, text: str, lead) -> tuple:
        """Analisa menções de orçamento - VERSÃO MELHORADA."""
        score = 0
        reason = None
        
        # ✅ PADRÕES MELHORADOS para detectar orçamento
        budget_patterns = [
            # "550 mil", "550k", "R$ 550.000"
            r"[0-9]{2,3}\s*(mil|k)\b",
            r"r\$?\s*[0-9]{2,3}[.,]?[0-9]{3}",
            
            # "orçamento de 550", "orçamento fica em torno de 550"
            r"(orçamento|orcamento).{0,30}(de|é|eh|fica|em torno|cerca|aproximadamente).{0,30}[0-9]{2,3}",
            
            # "até 550 mil", "em torno de 550k"
            r"(até|ate|em torno|cerca de|aproximadamente).{0,30}[0-9]{2,3}.{0,15}(mil|k|reais)",
            
            # "tenho 550k", "disponho de 550 mil"
            r"(tenho|possuo|disponho|dispor).{0,30}[0-9]{2,3}.{0,15}(mil|k|reais)",
        ]
        
        for pattern in budget_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 15
                reason = "Orçamento definido"
                logger.debug(f"Budget detectado: {pattern}")
                break
        
        # Se tem orçamento no lead
        if hasattr(lead, 'budget') and lead.budget:
            score += 10
            reason = f"Orçamento: R$ {lead.budget:,.0f}"
        
        return score, reason
    
    def _analyze_engagement(self, messages: List, lead) -> tuple:
        """Analisa engajamento na conversa - VERSÃO CORRIGIDA."""
        score = 0
        reason = None
        
        user_messages = [m for m in messages if m.role == "user"]
        
        # ✅ THRESHOLDS AJUSTADOS
        if len(user_messages) >= 6:
            score += 15
            reason = "Alto engajamento (6+ mensagens)"
        elif len(user_messages) >= 4:  # ✅ NOVO
            score += 10
            reason = "Engajamento bom (4-5 mensagens)"
        elif len(user_messages) == 3:  # ✅ NOVO
            score += 5
            reason = "Engajamento moderado"
        elif len(user_messages) <= 2:
            score -= 5  # ✅ REDUZIDO (era -10)
            reason = "Baixo engajamento"
        
        # Tamanho médio das mensagens
        if user_messages:
            avg_length = sum(len(m.content) for m in user_messages) / len(user_messages)
            
            # ✅ THRESHOLDS AJUSTADOS
            if avg_length > 80:  # ✅ REDUZIDO (era 100)
                score += 10
            elif avg_length < 20:
                score -= 5
        
        # Tempo de resposta (se disponível)
        if len(user_messages) >= 2:
            try:
                response_times = []
                for i in range(1, len(user_messages)):
                    prev_msg_index = messages.index(user_messages[i-1])
                    if prev_msg_index > 0:
                        time_diff = user_messages[i].created_at - messages[prev_msg_index - 1].created_at
                        response_times.append(time_diff.total_seconds())
                
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
                    
                    # Responde rápido = mais interessado
                    if avg_response_time < 300:  # < 5 min
                        score += 5
            except Exception as e:
                logger.debug(f"Erro calculando tempo de resposta: {e}")
        
        return score, reason
    
    def _analyze_urgency(self, text: str) -> tuple:
        """Analisa urgência mencionada - VERSÃO MELHORADA."""
        score = 0
        reason = None
        
        # Urgência extrema
        extreme_urgency = [
            "urgente", "hoje", "amanhã", "essa semana",
            "preciso logo", "o mais rápido possível", "rapido", "rápido"
        ]
        
        for word in extreme_urgency:
            if word in text:
                score += 15
                reason = "Urgência alta"
                break
        
        # ✅ PADRÕES MELHORADOS para detectar prazo
        prazo_patterns = [
            # "3 meses", "até 3 meses", "em 3 meses", "dentro de 3 meses"
            r"(em|até|ate|dentro de|prazo de).{0,20}[0-9]+.{0,15}(dia|semana|mes|meses)",
            
            # "me mudar em 3 meses", "mudar em até 3 meses"
            r"(me mudar|mudar|mudança|mudanca).{0,30}(em|até|ate).{0,20}[0-9]+.{0,15}(mes|meses)",
            
            # "ideia seria me mudar em X", "plano é mudar em X"
            r"(ideia|plano|pretendo).{0,30}(mudar|me mudar).{0,30}(em|até|ate).{0,20}[0-9]+",
        ]
        
        for pattern in prazo_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 10
                if not reason:
                    reason = "Prazo definido"
                logger.debug(f"Prazo detectado: {pattern}")
                break
        
        # Sem urgência
        no_urgency = ["sem pressa", "sem urgência", "sem urgencia", "com calma", "quando der"]
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