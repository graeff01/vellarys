"""
PropertyMatcherService - Match Automático de Imóveis com IA
=============================================================

Extrai critérios de mensagens usando IA e busca imóveis compatíveis.

Exemplo de uso:
Lead: "Procuro casa 3 quartos zona norte até 500k"

IA extrai:
- tipo: casa
- quartos: 3
- região: zona norte
- valor_max: 500000

Sistema busca e retorna imóveis que correspondem.
"""
import re
import json
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.property import Property
from src.infrastructure.openai_client import get_openai_client


class PropertyMatcherService:
    """Service para match automático de imóveis."""

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    @staticmethod
    async def extract_criteria_from_message(message: str) -> Dict[str, Any]:
        """
        Extrai critérios de busca da mensagem usando IA.

        Args:
            message: Mensagem do lead

        Returns:
            Dict com critérios extraídos
        """
        client = get_openai_client()

        prompt = f"""
Você é um assistente de imobiliária. Extraia os critérios de busca desta mensagem:

"{message}"

Retorne APENAS um JSON válido com estes campos (use null se não mencionado):
{{
    "property_type": "casa|apartamento|sobrado|terreno|sala_comercial|null",
    "min_rooms": número ou null,
    "max_rooms": número ou null,
    "min_price": número ou null,
    "max_price": número ou null,
    "neighborhoods": ["bairro1", "bairro2"] ou [],
    "cities": ["cidade1"] ou [],
    "required_features": ["piscina", "churrasqueira"] ou []
}}

Conversões comuns:
- "3Q", "3 quartos", "três quartos" → min_rooms: 3, max_rooms: 3
- "até 500k", "até R$ 500 mil" → max_price: 500000
- "acima de 300k" → min_price: 300000
- "zona norte", "ZN" → adicione em neighborhoods ou cities conforme contexto
- "perto do metrô", "próximo ao shopping" → adicione em required_features

IMPORTANTE: Retorne APENAS o JSON, sem markdown ou explicações.
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300
            )

            content = response.choices[0].message.content.strip()

            # Remove markdown se presente
            content = content.replace("```json", "").replace("```", "").strip()

            criteria = json.loads(content)

            # Validar e converter
            return {
                "property_type": criteria.get("property_type"),
                "min_rooms": criteria.get("min_rooms"),
                "max_rooms": criteria.get("max_rooms"),
                "min_price": criteria.get("min_price"),
                "max_price": criteria.get("max_price"),
                "neighborhoods": criteria.get("neighborhoods", []),
                "cities": criteria.get("cities", []),
                "required_features": criteria.get("required_features", [])
            }

        except Exception as e:
            print(f"Erro ao extrair critérios: {e}")
            # Fallback: regex simples
            return PropertyMatcherService._fallback_extraction(message)

    @staticmethod
    def _fallback_extraction(message: str) -> Dict[str, Any]:
        """Extração simples por regex se IA falhar."""
        message_lower = message.lower()
        criteria = {
            "property_type": None,
            "min_rooms": None,
            "max_rooms": None,
            "min_price": None,
            "max_price": None,
            "neighborhoods": [],
            "cities": [],
            "required_features": []
        }

        # Tipo de imóvel
        if "casa" in message_lower:
            criteria["property_type"] = "casa"
        elif "apto" in message_lower or "apartamento" in message_lower:
            criteria["property_type"] = "apartamento"
        elif "sobrado" in message_lower:
            criteria["property_type"] = "sobrado"
        elif "terreno" in message_lower:
            criteria["property_type"] = "terreno"

        # Quartos
        rooms_match = re.search(r'(\d+)\s*q(?:uarto)?s?', message_lower)
        if rooms_match:
            rooms = int(rooms_match.group(1))
            criteria["min_rooms"] = rooms
            criteria["max_rooms"] = rooms

        # Preço máximo
        price_patterns = [
            r'até\s+r?\$?\s*(\d+)k',
            r'até\s+r?\$?\s*(\d+)\s*mil',
            r'max\s+r?\$?\s*(\d+)k'
        ]
        for pattern in price_patterns:
            match = re.search(pattern, message_lower)
            if match:
                criteria["max_price"] = int(match.group(1)) * 1000
                break

        # Preço mínimo
        min_patterns = [
            r'acima\s+de\s+r?\$?\s*(\d+)k',
            r'mínimo\s+r?\$?\s*(\d+)k',
            r'a\s+partir\s+de\s+r?\$?\s*(\d+)k'
        ]
        for pattern in min_patterns:
            match = re.search(pattern, message_lower)
            if match:
                criteria["min_price"] = int(match.group(1)) * 1000
                break

        return criteria

    async def find_matches(self, message: str, limit: int = 5) -> Dict[str, Any]:
        """
        Busca imóveis que correspondem à mensagem.

        Args:
            message: Mensagem do lead
            limit: Máximo de resultados

        Returns:
            Dict com critérios e imóveis encontrados
        """
        # 1. Extrair critérios
        criteria = await self.extract_criteria_from_message(message)

        # 2. Construir query
        query = select(Property).where(
            Property.tenant_id == self.tenant_id,
            Property.is_active == True,
            Property.is_available == True
        )

        # Aplicar filtros
        if criteria["property_type"]:
            query = query.where(Property.property_type == criteria["property_type"])

        if criteria["min_rooms"]:
            query = query.where(Property.rooms >= criteria["min_rooms"])

        if criteria["max_rooms"]:
            query = query.where(Property.rooms <= criteria["max_rooms"])

        if criteria["min_price"]:
            query = query.where(
                or_(
                    Property.sale_price >= criteria["min_price"],
                    Property.rent_price >= criteria["min_price"]
                )
            )

        if criteria["max_price"]:
            query = query.where(
                or_(
                    Property.sale_price <= criteria["max_price"],
                    Property.rent_price <= criteria["max_price"]
                )
            )

        if criteria["cities"]:
            city_filters = [Property.city.ilike(f"%{city}%") for city in criteria["cities"]]
            query = query.where(or_(*city_filters))

        if criteria["neighborhoods"]:
            neighborhood_filters = [
                Property.neighborhood.ilike(f"%{n}%") for n in criteria["neighborhoods"]
            ]
            query = query.where(or_(*neighborhood_filters))

        # Features (JSONB contains)
        if criteria["required_features"]:
            for feature in criteria["required_features"]:
                query = query.where(
                    Property.features.contains([feature])
                )

        # Ordenar por preço (menor primeiro)
        query = query.order_by(Property.sale_price.asc().nullslast()).limit(limit)

        # 3. Executar busca
        result = await self.db.execute(query)
        properties = result.scalars().all()

        # 4. Formatar resposta
        return {
            "criteria": criteria,
            "properties": [
                {
                    "id": p.id,
                    "title": p.title,
                    "property_type": p.property_type,
                    "address": p.address,
                    "neighborhood": p.neighborhood,
                    "city": p.city,
                    "rooms": p.rooms,
                    "bathrooms": p.bathrooms,
                    "parking_spots": p.parking_spots,
                    "size_sqm": float(p.size_sqm) if p.size_sqm else None,
                    "sale_price": float(p.sale_price) if p.sale_price else None,
                    "rent_price": float(p.rent_price) if p.rent_price else None,
                    "features": p.features or [],
                    "images": (p.images or [])[:3],  # Primeiras 3 fotos
                    "match_score": self._calculate_match_score(p, criteria)
                }
                for p in properties
            ]
        }

    @staticmethod
    def _calculate_match_score(prop: Property, criteria: Dict[str, Any]) -> float:
        """
        Calcula score de compatibilidade (0-100).

        Critérios:
        - Tipo exato: +30
        - Quartos exatos: +25
        - Preço dentro da faixa: +25
        - Localização correta: +15
        - Features: +5
        """
        score = 0.0

        # Tipo
        if criteria["property_type"] and prop.property_type == criteria["property_type"]:
            score += 30

        # Quartos
        if criteria["min_rooms"] and criteria["max_rooms"]:
            if prop.rooms and criteria["min_rooms"] <= prop.rooms <= criteria["max_rooms"]:
                score += 25

        # Preço
        price = prop.sale_price or prop.rent_price
        if price:
            if criteria["max_price"] and price <= criteria["max_price"]:
                score += 15
            if criteria["min_price"] and price >= criteria["min_price"]:
                score += 10

        # Localização
        if criteria["cities"]:
            for city in criteria["cities"]:
                if prop.city and city.lower() in prop.city.lower():
                    score += 10
                    break

        if criteria["neighborhoods"]:
            for neighborhood in criteria["neighborhoods"]:
                if prop.neighborhood and neighborhood.lower() in prop.neighborhood.lower():
                    score += 5
                    break

        # Features
        if criteria["required_features"] and prop.features:
            matched_features = len(set(criteria["required_features"]) & set(prop.features))
            score += min(matched_features * 2, 10)

        return min(round(score, 1), 100.0)

    async def generate_whatsapp_message(
        self,
        properties: List[Dict[str, Any]],
        lead_name: str
    ) -> str:
        """
        Gera mensagem formatada para WhatsApp com os imóveis encontrados.

        Args:
            properties: Lista de imóveis
            lead_name: Nome do lead

        Returns:
            Mensagem formatada
        """
        if not properties:
            return f"Olá {lead_name}! Infelizmente não encontrei imóveis que correspondam exatamente ao que você procura. Mas posso te ajudar com outras opções! 😊"

        msg = f"Oi {lead_name}! Encontrei {len(properties)} opções que combinam com você! 🏠\n\n"

        for i, prop in enumerate(properties, 1):
            msg += f"{i}. *{prop['title']}*\n"
            msg += f"   📍 {prop['neighborhood'] or prop['city']}\n"

            if prop['rooms']:
                msg += f"   🛏️ {prop['rooms']} quartos"
                if prop['bathrooms']:
                    msg += f" | 🚿 {prop['bathrooms']} banheiros"
                if prop['parking_spots']:
                    msg += f" | 🚗 {prop['parking_spots']} vagas"
                msg += "\n"

            if prop['size_sqm']:
                msg += f"   📐 {prop['size_sqm']}m²\n"

            if prop['sale_price']:
                msg += f"   💰 R$ {prop['sale_price']:,.2f}\n"
            elif prop['rent_price']:
                msg += f"   💰 R$ {prop['rent_price']:,.2f}/mês\n"

            if prop['match_score'] and prop['match_score'] >= 80:
                msg += f"   ⭐ Match de {prop['match_score']}%\n"

            msg += "\n"

        msg += "Qual te interessou mais? Posso te enviar mais detalhes! 😊"

        return msg
