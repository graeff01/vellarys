"""
Template Interpolation Service
===============================

Substitui variáveis em templates de respostas rápidas.

Variáveis suportadas:
- {{lead_name}} - Nome do lead
- {{lead_phone}} - Telefone do lead
- {{lead_city}} - Cidade do lead
- {{seller_name}} - Nome do vendedor
- {{company_name}} - Nome da empresa (tenant)
- {{current_date}} - Data atual (DD/MM/YYYY)
- {{current_time}} - Hora atual (HH:MM)
- {{current_datetime}} - Data e hora (DD/MM/YYYY HH:MM)

Exemplo:
    Template: "Olá {{lead_name}}, sou {{seller_name}} da {{company_name}}!"
    Resultado: "Olá João Silva, sou Maria Santos da Imobiliária XYZ!"
"""
import re
from datetime import datetime
from typing import Dict, Optional
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)


class TemplateInterpolationService:
    """Serviço para interpolação de templates."""

    # Regex para encontrar variáveis {{nome}}
    VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")

    def __init__(self):
        self.timezone = ZoneInfo("America/Sao_Paulo")

    def get_current_date(self) -> str:
        """Retorna data atual em formato brasileiro."""
        now = datetime.now(self.timezone)
        return now.strftime("%d/%m/%Y")

    def get_current_time(self) -> str:
        """Retorna hora atual."""
        now = datetime.now(self.timezone)
        return now.strftime("%H:%M")

    def get_current_datetime(self) -> str:
        """Retorna data e hora atual."""
        now = datetime.now(self.timezone)
        return now.strftime("%d/%m/%Y %H:%M")

    def build_context(
        self,
        lead_data: Optional[dict] = None,
        seller_data: Optional[dict] = None,
        tenant_data: Optional[dict] = None
    ) -> Dict[str, str]:
        """
        Constrói dicionário de variáveis disponíveis.

        Args:
            lead_data: Dados do lead (name, phone, city, etc)
            seller_data: Dados do vendedor (name, email, etc)
            tenant_data: Dados do tenant (name, etc)

        Returns:
            Dicionário com todas as variáveis disponíveis
        """
        context = {}

        # Variáveis do lead
        if lead_data:
            context["lead_name"] = lead_data.get("name", "Cliente")
            context["lead_phone"] = lead_data.get("phone", "")
            context["lead_email"] = lead_data.get("email", "")
            context["lead_city"] = lead_data.get("city", "")

        # Variáveis do vendedor
        if seller_data:
            context["seller_name"] = seller_data.get("name", "Vendedor")
            context["seller_email"] = seller_data.get("email", "")
            context["seller_phone"] = seller_data.get("phone", "")

        # Variáveis da empresa
        if tenant_data:
            context["company_name"] = tenant_data.get("name", "Nossa Empresa")

        # Variáveis de data/hora
        context["current_date"] = self.get_current_date()
        context["current_time"] = self.get_current_time()
        context["current_datetime"] = self.get_current_datetime()

        return context

    def interpolate(self, template: str, context: Dict[str, str]) -> str:
        """
        Substitui todas as variáveis {{nome}} pelo valor correspondente.

        Args:
            template: Texto com variáveis
            context: Dicionário com valores

        Returns:
            Texto interpolado
        """

        def replace_variable(match):
            """Função auxiliar para re.sub."""
            var_name = match.group(1)

            # Se variável existe no contexto, substitui
            if var_name in context:
                return str(context[var_name])

            # Se não existe, mantém original
            logger.warning(f"[Template] Variável não encontrada: {var_name}")
            return match.group(0)

        # Substitui todas as ocorrências
        result = self.VARIABLE_PATTERN.sub(replace_variable, template)

        return result

    def validate_template(self, template: str) -> tuple[bool, Optional[str]]:
        """
        Valida sintaxe do template.

        Returns:
            (is_valid, error_message)
        """
        # Verifica se há chaves não balanceadas
        open_count = template.count("{{")
        close_count = template.count("}}")

        if open_count != close_count:
            return False, "Chaves não balanceadas ({{ e }})"

        # Verifica se variáveis têm nomes válidos
        variables = self.VARIABLE_PATTERN.findall(template)
        for var in variables:
            if not var.replace("_", "").isalnum():
                return False, f"Nome de variável inválido: {var}"

        return True, None

    def get_available_variables(self) -> list[dict]:
        """
        Retorna lista de variáveis disponíveis para documentação.

        Returns:
            [{"name": "lead_name", "description": "Nome do lead", "example": "João Silva"}, ...]
        """
        return [
            {"name": "lead_name", "description": "Nome do lead", "example": "João Silva"},
            {"name": "lead_phone", "description": "Telefone do lead", "example": "(11) 99999-9999"},
            {"name": "lead_email", "description": "E-mail do lead", "example": "joao@email.com"},
            {"name": "lead_city", "description": "Cidade do lead", "example": "São Paulo"},
            {"name": "seller_name", "description": "Nome do vendedor", "example": "Maria Santos"},
            {"name": "seller_email", "description": "E-mail do vendedor", "example": "maria@empresa.com"},
            {"name": "seller_phone", "description": "Telefone do vendedor", "example": "(11) 98888-8888"},
            {"name": "company_name", "description": "Nome da empresa", "example": "Imobiliária XYZ"},
            {"name": "current_date", "description": "Data atual", "example": self.get_current_date()},
            {"name": "current_time", "description": "Hora atual", "example": self.get_current_time()},
            {"name": "current_datetime", "description": "Data e hora atual", "example": self.get_current_datetime()},
        ]


# Singleton global
template_service = TemplateInterpolationService()
