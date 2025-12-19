"""
GERADOR DE RESUMOS ESTRUTURADOS
================================
Cria resumos úteis e acionáveis para corretores/gestores.
"""

import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from src.domain.services.smart_notifications import notify_hot_lead

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """
    Gera resumos estruturados e úteis de conversas com leads.
    
    Em vez de resumos genéricos, cria resumos que ajudam o corretor
    a atender o cliente com contexto completo.
    """
    
    def generate(
        self,
        lead,
        messages: List,
        qualification_data: Dict = None
    ) -> str:
        """
        Gera resumo completo do lead.
        
        Args:
            lead: Objeto Lead
            messages: Lista de mensagens
            qualification_data: Dados da qualificação (opcional)
        
        Returns:
            String com resumo formatado
        """
        
        conversation_text = " ".join([
            m.content for m in messages 
            if hasattr(m, 'content') and m.content
        ])
        
        # Extrai informações
        profile = self._extract_profile(lead, conversation_text)
        key_points = self._extract_key_points(messages, conversation_text)
        objections = self._extract_objections(conversation_text)
        next_action = self._recommend_next_action(lead, qualification_data, objections)
        best_time = self._predict_best_contact_time(messages)
        
        # Monta resumo
        summary = self._build_summary(
            lead=lead,
            profile=profile,
            key_points=key_points,
            objections=objections,
            next_action=next_action,
            best_time=best_time,
            qualification_data=qualification_data
        )
        
        return summary
    
    def _extract_profile(self, lead, text: str) -> Dict:
        """Extrai perfil do cliente da conversa."""
        
        profile = {
            "orcamento": None,
            "urgencia": None,
            "finalidade": None,
            "preferencias": [],
            "situacao_atual": None,
            "familia": None,
        }
        
        # Orçamento
        budget_patterns = [
            r"orçamento.{0,20}(de|é|até|tem).{0,20}([0-9]+).{0,10}(mil|k|reais)",
            r"(tenho|possuo).{0,20}([0-9]+).{0,10}(mil|k|reais)",
            r"até.{0,20}([0-9]+).{0,10}(mil|reais)",
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = re.search(r"[0-9]+", match.group(0))
                    if value:
                        profile["orcamento"] = f"R$ {value.group(0)}k"
                        break
                except:
                    pass
        
        # Se tem no lead
        if hasattr(lead, 'budget') and lead.budget:
            profile["orcamento"] = f"R$ {lead.budget:,.0f}"
        
        # Urgência
        urgency_patterns = {
            "urgente|hoje|amanhã|essa semana": "ALTA - Imediata",
            "preciso.{0,20}em.{0,20}[0-9]+.{0,10}mes": "ALTA - Prazo curto",
            "próximos.{0,20}[0-9]+.{0,10}meses": "MÉDIA - Alguns meses",
            "sem pressa|com calma": "BAIXA - Sem urgência",
        }
        for pattern, urgency in urgency_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                profile["urgencia"] = urgency
                break
        
        # Finalidade
        if re.search(r"\b(morar|moradia|residir)\b", text, re.IGNORECASE):
            profile["finalidade"] = "Morar"
        elif re.search(r"\b(investir|investimento|renda)\b", text, re.IGNORECASE):
            profile["finalidade"] = "Investir"
        elif re.search(r"\b(alugar|locação)\b", text, re.IGNORECASE):
            profile["finalidade"] = "Alugar"
        
        # Preferências (tipo de imóvel, bairro, etc)
        preferences = []
        
        # Tipo de imóvel
        if re.search(r"\b(casa|sobrado)\b", text, re.IGNORECASE):
            preferences.append("Casa")
        if re.search(r"\b(apartamento|apto)\b", text, re.IGNORECASE):
            preferences.append("Apartamento")
        if re.search(r"\bterreno\b", text, re.IGNORECASE):
            preferences.append("Terreno")
        
        # Quartos
        quartos_match = re.search(r"([0-9]+).{0,10}(quarto|dormitório)", text, re.IGNORECASE)
        if quartos_match:
            preferences.append(f"{quartos_match.group(1)} quartos")
        
        # Bairro/região
        bairro_match = re.search(r"(em|no|na).{0,10}([A-Z][a-zà-ú]+(?:\s+[A-Z][a-zà-ú]+)*)", text)
        if bairro_match:
            bairro = bairro_match.group(2)
            if len(bairro) > 3:  # Evita falsos positivos
                preferences.append(f"Região: {bairro}")
        
        profile["preferencias"] = preferences
        
        # Situação atual
        if re.search(r"(moro|moramos).{0,20}(aluguel|alugado)", text, re.IGNORECASE):
            profile["situacao_atual"] = "Mora de aluguel"
        elif re.search(r"(moro|moramos).{0,20}(pais|família)", text, re.IGNORECASE):
            profile["situacao_atual"] = "Mora com família"
        
        # Família
        filhos_match = re.search(r"([0-9]+).{0,10}(filho|filha|criança)", text, re.IGNORECASE)
        if filhos_match:
            profile["familia"] = f"{filhos_match.group(1)} filhos"
        elif re.search(r"\b(casad|esposa|marido|companheiro)\b", text, re.IGNORECASE):
            profile["familia"] = "Casado(a)"
        
        return profile
    
    def _extract_key_points(self, messages: List, text: str) -> List[str]:
        """Extrai pontos-chave da conversa."""
        
        key_points = []
        
        # Interesses mencionados
        interests = []
        
        if re.search(r"(gostei|interessei|achei legal).{0,30}(imóvel|casa|apto)", text, re.IGNORECASE):
            interests.append("Demonstrou interesse em imóvel específico")
        
        if re.search(r"(financiamento|financiar|banco)", text, re.IGNORECASE):
            interests.append("Interessado em financiamento")
        
        if re.search(r"(visita|visitar|conhecer|ver).{0,20}(imóvel|casa|apto)", text, re.IGNORECASE):
            interests.append("Quer agendar visita")
        
        if re.search(r"(documentos?|documentação|papelada)", text, re.IGNORECASE):
            interests.append("Perguntou sobre documentação necessária")
        
        # Aprovações
        approvals = []
        
        if re.search(r"(aprovado|aprovada).{0,20}(banco|financiamento|crédito)", text, re.IGNORECASE):
            approvals.append("✅ Financiamento PRÉ-APROVADO")
        
        if re.search(r"nome saiu.{0,30}(compra assistida|programa)", text, re.IGNORECASE):
            approvals.append("✅ Aprovado em programa habitacional")
        
        if re.search(r"(tenho|possuo).{0,20}(entrada|dinheiro guardado)", text, re.IGNORECASE):
            approvals.append("✅ Tem entrada disponível")
        
        # Monta lista final
        key_points.extend(approvals)
        key_points.extend(interests)
        
        # Engajamento
        user_messages = [m for m in messages if m.role == "user"]
        if len(user_messages) >= 8:
            key_points.append(f"🔥 Alto engajamento ({len(user_messages)} mensagens)")
        
        return key_points[:5]  # Top 5
    
    def _extract_objections(self, text: str) -> List[str]:
        """Extrai objeções e preocupações mencionadas."""
        
        objections = []
        
        # Preço
        if re.search(r"(caro|muito caro|acima.{0,20}orçamento)", text, re.IGNORECASE):
            objections.append("💰 Preocupação com preço/valor")
        
        # Localização
        if re.search(r"(longe|muito longe|distante)", text, re.IGNORECASE):
            objections.append("📍 Preocupação com localização/distância")
        
        # Documentação
        if re.search(r"(burocracia|muita papelada|complicado)", text, re.IGNORECASE):
            objections.append("📄 Preocupação com burocracia")
        
        # Condição
        if re.search(r"(reforma|reformar|precisa arrumar)", text, re.IGNORECASE):
            objections.append("🔧 Preocupação com estado do imóvel")
        
        # Decisão
        if re.search(r"(preciso pensar|vou pensar|tenho que decidir)", text, re.IGNORECASE):
            objections.append("🤔 Ainda não decidiu")
        
        if re.search(r"(conversar|falar).{0,20}(esposa|marido|família)", text, re.IGNORECASE):
            objections.append("👥 Precisa consultar família")
        
        return objections
    
    def _recommend_next_action(
        self,
        lead,
        qualification_data: Dict,
        objections: List[str]
    ) -> str:
        """Recomenda próxima ação para o corretor."""
        
        qualification = qualification_data.get("qualification") if qualification_data else lead.qualification
        
        if qualification == "hot":
            if any("visita" in obj.lower() for obj in objections):
                return "🎯 AGENDAR VISITA URGENTE - Cliente pronto!"
            elif any("documentação" in obj.lower() for obj in objections):
                return "📋 Explicar processo e documentação necessária"
            else:
                return "🔥 LIGAR IMEDIATAMENTE - Lead quente!"
        
        elif qualification == "warm":
            if any("preço" in obj.lower() for obj in objections):
                return "💰 Apresentar opções na faixa de orçamento"
            elif any("família" in obj.lower() for obj in objections):
                return "👥 Agendar visita com família/cônjuge"
            else:
                return "📞 Ligar em 24h para apresentar opções"
        
        else:  # cold
            return "📧 Follow-up em 3-5 dias"
    
    def _predict_best_contact_time(self, messages: List) -> str:
        """Prediz melhor horário para contato baseado na atividade."""
        
        if not messages:
            return "Não identificado"
        
        # Analisa horários das mensagens do usuário
        user_messages = [m for m in messages if m.role == "user"]
        
        if not user_messages:
            return "Não identificado"
        
        hours = [m.created_at.hour for m in user_messages if hasattr(m, 'created_at')]
        
        if not hours:
            return "Não identificado"
        
        avg_hour = sum(hours) / len(hours)
        
        if avg_hour < 12:
            return "Manhã (8h-12h)"
        elif avg_hour < 18:
            return "Tarde (12h-18h)"
        else:
            return "Noite (18h-21h)"
    
    def _build_summary(
        self,
        lead,
        profile: Dict,
        key_points: List[str],
        objections: List[str],
        next_action: str,
        best_time: str,
        qualification_data: Dict
    ) -> str:
        """Monta o resumo final formatado."""
        
        qualification = qualification_data.get("qualification") if qualification_data else lead.qualification
        
        # Emoji de qualificação
        qual_emoji = {
            "hot": "🔥",
            "warm": "🌡️",
            "cold": "❄️"
        }.get(qualification, "❓")
        
        summary_parts = []
        
        # HEADER
        summary_parts.append(f"{qual_emoji} QUALIFICAÇÃO: {qualification.upper()}")
        
        if qualification_data:
            confidence = qualification_data.get("confidence", 0)
            score = qualification_data.get("score", 0)
            summary_parts.append(f"Confiança: {int(confidence * 100)}% | Score: {score}")
        
        summary_parts.append("")
        
        # PERFIL
        summary_parts.append("📊 PERFIL DO CLIENTE:")
        
        if profile.get("orcamento"):
            summary_parts.append(f"💰 Orçamento: {profile['orcamento']}")
        else:
            summary_parts.append("💰 Orçamento: Não informado")
        
        if profile.get("urgencia"):
            summary_parts.append(f"⏰ Urgência: {profile['urgencia']}")
        else:
            summary_parts.append("⏰ Urgência: Não definida")
        
        if profile.get("finalidade"):
            summary_parts.append(f"🎯 Finalidade: {profile['finalidade']}")
        
        if profile.get("familia"):
            summary_parts.append(f"👨‍👩‍👧‍👦 Família: {profile['familia']}")
        
        if profile.get("situacao_atual"):
            summary_parts.append(f"🏠 Situação: {profile['situacao_atual']}")
        
        # PREFERÊNCIAS
        if profile.get("preferencias"):
            summary_parts.append("")
            summary_parts.append("✅ PREFERÊNCIAS:")
            for pref in profile["preferencias"]:
                summary_parts.append(f"  • {pref}")
        
        # PONTOS-CHAVE
        if key_points:
            summary_parts.append("")
            summary_parts.append("💬 PRINCIPAIS PONTOS:")
            for point in key_points:
                summary_parts.append(f"  • {point}")
        
        # OBJEÇÕES
        if objections:
            summary_parts.append("")
            summary_parts.append("⚠️ OBJEÇÕES/PREOCUPAÇÕES:")
            for obj in objections:
                summary_parts.append(f"  • {obj}")
        
        # PRÓXIMA AÇÃO
        summary_parts.append("")
        summary_parts.append("🎯 PRÓXIMA AÇÃO RECOMENDADA:")
        summary_parts.append(f"  {next_action}")
        
        # MELHOR HORÁRIO
        summary_parts.append("")
        summary_parts.append(f"📞 Melhor horário contato: {best_time}")
        
        # RAZÕES DA QUALIFICAÇÃO
        if qualification_data and qualification_data.get("reasons"):
            summary_parts.append("")
            summary_parts.append("🔍 POR QUE ESTA QUALIFICAÇÃO:")
            for reason in qualification_data["reasons"]:
                summary_parts.append(f"  • {reason}")
        
        return "\n".join(summary_parts)


# Instância global
summary_generator = SummaryGenerator()


def generate_lead_summary(lead, messages, qualification_data=None):
    """Helper function para gerar resumo."""
    return summary_generator.generate(lead, messages, qualification_data)