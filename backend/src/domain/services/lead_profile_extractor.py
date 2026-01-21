"""
EXTRATOR DE PERFIL DE LEAD - MEMORY DE LONGO PRAZO
====================================================
Extrai preferências e informações do lead a partir das conversas.
Permite que a IA "lembre" das preferências entre sessões.

Características:
- Extração incremental (cada mensagem adiciona ao perfil)
- Nunca sobrescreve dados existentes (só adiciona)
- Acumula bairros/preferências em listas
- Armazena em lead.custom_data["lead_profile"]
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class LeadProfileExtractor:
    """
    Extrai e atualiza perfil do lead baseado nas conversas.
    O perfil persiste entre sessões para evitar perguntas repetidas.
    """

    # Bairros conhecidos (pode ser expandido por tenant)
    DEFAULT_BAIRROS = [
        # Rio Grande do Sul
        "centro", "niteroi", "niterói", "igara", "guajuviras", "mathias velho",
        "rio branco", "fatima", "fátima", "harmonia", "mato grande", "estância velha",
        "marechal rondon", "são josé", "são jose", "industrial", "humaitá", "humaita",
        "olaria", "vila rosa", "cristo rei", "são luís", "sao luis",
        # POA
        "moinhos", "moinhos de vento", "bela vista", "petrópolis", "petropolis",
        "mont serrat", "auxiliadora", "boa vista", "jardim botânico", "jardim botanico",
        "higienópolis", "higienopolis", "floresta", "independência", "independencia",
        "cidade baixa", "menino deus", "praia de belas", "cristal", "ipanema",
        "cavalhada", "tristeza", "vila assunção", "vila assuncao",
        # Outras cidades RS
        "canoas", "novo hamburgo", "são leopoldo", "sao leopoldo", "gravataí", "gravatai",
        "cachoeirinha", "alvorada", "viamão", "viamao", "eldorado do sul",
    ]

    # Tipos de imóvel reconhecidos
    TIPOS_IMOVEL = {
        "apartamento": ["apartamento", "apto", "ap"],
        "casa": ["casa", "sobrado", "residência", "residencia"],
        "terreno": ["terreno", "lote"],
        "comercial": ["comercial", "sala", "loja", "galpão", "galpao"],
        "cobertura": ["cobertura", "duplex", "penthouse"],
        "kitnet": ["kitnet", "studio", "jk"],
    }

    def extract_from_message(
        self,
        message: str,
        current_profile: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Extrai informações de UMA mensagem e atualiza o perfil.
        Chamado após cada mensagem do usuário.

        Args:
            message: Texto da mensagem do usuário
            current_profile: Perfil atual (ou None para criar novo)

        Returns:
            Perfil atualizado
        """
        profile = current_profile.copy() if current_profile else self._empty_profile()
        msg_lower = message.lower()

        # Extrai cada tipo de informação
        self._extract_property_preferences(msg_lower, profile)
        self._extract_budget_info(msg_lower, profile)
        self._extract_timeline_info(msg_lower, profile)
        self._extract_family_info(msg_lower, profile)
        self._extract_financial_info(msg_lower, profile)
        self._extract_objections(msg_lower, profile)
        self._extract_contact_preferences(msg_lower, profile)

        profile["last_updated"] = datetime.now(timezone.utc).isoformat()

        return profile

    def _empty_profile(self) -> Dict[str, Any]:
        """Retorna estrutura vazia do perfil."""
        return {
            "preferences": {},
            "budget_info": {},
            "timeline_info": {},
            "family_info": {},
            "financial_info": {},
            "contact_preferences": {},
            "objections": [],
            "interaction_count": 0,
            "last_updated": None,
        }

    def _extract_property_preferences(self, msg: str, profile: Dict) -> None:
        """Extrai preferências de imóvel."""
        prefs = profile.get("preferences", {})

        # Tipo de imóvel
        for tipo_nome, keywords in self.TIPOS_IMOVEL.items():
            for keyword in keywords:
                if keyword in msg:
                    prefs["tipo_imovel"] = tipo_nome
                    break

        # Quartos
        quartos_patterns = [
            r'(\d+)\s*(?:quartos?|dormit[oó]rios?|dorms?)',
            r'(?:quero|preciso|busco).{0,20}(\d+)\s*(?:quartos?|dorms?)',
        ]
        for pattern in quartos_patterns:
            match = re.search(pattern, msg)
            if match:
                prefs["quartos_minimo"] = int(match.group(1))
                break

        # Banheiros
        banheiros_match = re.search(r'(\d+)\s*(?:banheiros?|wc|lavabos?)', msg)
        if banheiros_match:
            prefs["banheiros_minimo"] = int(banheiros_match.group(1))

        # Vagas
        vagas_match = re.search(r'(\d+)\s*(?:vagas?|garagens?)', msg)
        if vagas_match:
            prefs["vagas_minimo"] = int(vagas_match.group(1))

        # Metragem
        metragem_patterns = [
            r'(\d+)\s*(?:m2|m²|metros?)',
            r'(?:pelo menos|no mínimo|minimo|acima de)\s*(\d+)\s*(?:m|metros?)',
        ]
        for pattern in metragem_patterns:
            match = re.search(pattern, msg)
            if match:
                prefs["metragem_minima"] = int(match.group(1))
                break

        # Bairros (acumula em lista)
        bairros_interesse = prefs.get("bairros_interesse", [])
        for bairro in self.DEFAULT_BAIRROS:
            if bairro in msg and bairro not in bairros_interesse:
                bairros_interesse.append(bairro)

        if bairros_interesse:
            prefs["bairros_interesse"] = bairros_interesse

        # Características desejadas
        caracteristicas = prefs.get("caracteristicas", [])

        caracteristicas_map = {
            "churrasqueira": ["churrasqueira", "churras", "area gourmet", "área gourmet"],
            "piscina": ["piscina"],
            "quintal": ["quintal", "jardim", "pátio", "patio"],
            "sacada": ["sacada", "varanda", "terraço", "terraco"],
            "suite": ["suite", "suíte"],
            "closet": ["closet"],
            "lareira": ["lareira"],
            "ar_condicionado": ["ar condicionado", "ar-condicionado", "split"],
            "mobiliado": ["mobiliado", "com móveis", "com moveis"],
            "novo": ["novo", "na planta", "nunca habitado"],
            "reformado": ["reformado", "recém reformado", "recem reformado"],
            "seguranca": ["segurança", "seguranca", "portaria", "condomínio fechado"],
            "elevador": ["elevador"],
            "playground": ["playground", "área kids", "area kids"],
            "academia": ["academia", "fitness"],
            "pet_friendly": ["aceita pet", "pet friendly", "aceita animais"],
        }

        for caract, keywords in caracteristicas_map.items():
            for keyword in keywords:
                if keyword in msg and caract not in caracteristicas:
                    caracteristicas.append(caract)
                    break

        if caracteristicas:
            prefs["caracteristicas"] = caracteristicas

        profile["preferences"] = prefs

    def _extract_budget_info(self, msg: str, profile: Dict) -> None:
        """Extrai informações de orçamento."""
        budget = profile.get("budget_info", {})

        # Valores em reais - padrões mais específicos
        valor_patterns = [
            # "até 500 mil" ou "até 500k"
            (r'(?:at[eé]|m[aá]ximo|menos de|no m[aá]ximo)\s*(?:r\$)?\s*(\d+(?:\.\d+)?)\s*(?:mil|k)', 'faixa_max'),
            # "a partir de 300 mil"
            (r'(?:a partir de|m[ií]nimo|pelo menos|no m[ií]nimo)\s*(?:r\$)?\s*(\d+(?:\.\d+)?)\s*(?:mil|k)', 'faixa_min'),
            # "entre 300 e 500 mil"
            (r'entre\s*(?:r\$)?\s*(\d+(?:\.\d+)?)\s*(?:e|a)\s*(\d+(?:\.\d+)?)\s*(?:mil|k)', 'faixa_range'),
            # "tenho 800 mil"
            (r'(?:tenho|possuo|disponho)\s*(?:r\$)?\s*(\d+(?:\.\d+)?)\s*(?:mil|k|reais)', 'disponivel'),
            # "orçamento de 500 mil"
            (r'(?:or[çc]amento|budget)\s*(?:de|é|e|:)?\s*(?:r\$)?\s*(\d+(?:\.\d+)?)\s*(?:mil|k)', 'faixa_max'),
        ]

        for pattern, field in valor_patterns:
            match = re.search(pattern, msg)
            if match:
                if field == 'faixa_range':
                    # Extrai min e max
                    val_min = float(match.group(1).replace(".", ""))
                    val_max = float(match.group(2).replace(".", ""))
                    if val_min < 1000:
                        val_min *= 1000
                    if val_max < 1000:
                        val_max *= 1000
                    budget["faixa_min"] = int(val_min)
                    budget["faixa_max"] = int(val_max)
                else:
                    valor = float(match.group(1).replace(".", ""))
                    if valor < 1000:
                        valor *= 1000
                    budget[field] = int(valor)

        # Entrada
        entrada_patterns = [
            r'(?:tenho|possuo).{0,20}entrada.{0,10}(?:de)?\s*(?:r\$)?\s*(\d+(?:\.\d+)?)\s*(?:mil|k)?',
            r'entrada.{0,10}(?:de)?\s*(?:r\$)?\s*(\d+(?:\.\d+)?)\s*(?:mil|k)',
        ]
        for pattern in entrada_patterns:
            match = re.search(pattern, msg)
            if match:
                budget["tem_entrada"] = True
                valor = float(match.group(1).replace(".", ""))
                if valor < 1000:
                    valor *= 1000
                budget["valor_entrada"] = int(valor)
                break

        # Apenas menção de entrada sem valor
        if re.search(r'tenho.{0,20}entrada|entrada.{0,20}dispon[ií]vel', msg):
            budget["tem_entrada"] = True

        profile["budget_info"] = budget

    def _extract_timeline_info(self, msg: str, profile: Dict) -> None:
        """Extrai informações de prazo/urgência."""
        timeline = profile.get("timeline_info", {})

        # Urgência alta
        if re.search(r'urgente|hoje|amanh[aã]|essa semana|o mais r[aá]pido', msg):
            timeline["urgencia"] = "alta"
            timeline["prazo_descricao"] = "Imediato"

        # Urgência média - próximos meses
        prazo_match = re.search(r'(?:pr[oó]ximos?|em|dentro de)\s*(\d+)\s*(?:meses?|mes)', msg)
        if prazo_match:
            meses = int(prazo_match.group(1))
            timeline["prazo_meses"] = meses
            if meses <= 3:
                timeline["urgencia"] = "alta"
            elif meses <= 6:
                timeline["urgencia"] = "media"
            else:
                timeline["urgencia"] = "baixa"
            timeline["prazo_descricao"] = f"Em {meses} meses"

        # Urgência baixa
        if re.search(r'sem pressa|com calma|s[oó] pesquisando|n[aã]o tenho pressa', msg):
            timeline["urgencia"] = "baixa"
            timeline["prazo_descricao"] = "Sem pressa"

        # Motivo da mudança
        motivos_map = {
            "casamento": ["casar", "casamento", "vou casar", "noivo", "noiva"],
            "familia_crescendo": ["filho", "filha", "beb[eê]", "grav[ií]da", "grávida", "esperando"],
            "trabalho": ["trabalho", "emprego", "transferido", "mudar de cidade"],
            "investimento": ["investir", "investimento", "renda", "alugar"],
            "upgrade": ["maior", "melhor", "trocar", "upgrade"],
            "downsizing": ["menor", "reduzir", "aposentado", "aposentadoria"],
            "primeiro_imovel": ["primeiro", "nunca tive", "sair do aluguel"],
        }

        for motivo, keywords in motivos_map.items():
            for keyword in keywords:
                if re.search(keyword, msg):
                    timeline["motivo_mudanca"] = motivo
                    break

        profile["timeline_info"] = timeline

    def _extract_family_info(self, msg: str, profile: Dict) -> None:
        """Extrai informações familiares."""
        family = profile.get("family_info", {})

        # Número de filhos
        filhos_match = re.search(r'(\d+)\s*(?:filhos?|crian[çc]as?|kids?)', msg)
        if filhos_match:
            family["filhos"] = int(filhos_match.group(1))

        # Menção de filhos sem número
        if re.search(r'\b(?:filho|filha|criança|crianca)\b', msg) and "filhos" not in family:
            family["tem_filhos"] = True

        # Estado civil
        if re.search(r'casad[oa]|esposa|marido|companheira?|c[oô]njuge|conjuge', msg):
            family["estado_civil"] = "casado"
        elif re.search(r'solteir[oa]|sozinho|morar sozinho', msg):
            family["estado_civil"] = "solteiro"
        elif re.search(r'divorcia|separad[oa]', msg):
            family["estado_civil"] = "divorciado"

        # Pets
        if re.search(r'cachorro|c[aã]o|gato|pet|animal', msg):
            family["tem_pet"] = True

            # Tipo de pet
            if re.search(r'cachorro|c[aã]o', msg):
                family["tipo_pet"] = "cachorro"
            elif re.search(r'gato', msg):
                family["tipo_pet"] = "gato"

        # Idosos
        if re.search(r'idos[oa]|pai|m[aã]e|av[oó]|terceira idade|acessibilidade', msg):
            family["mora_com_idoso"] = True

        profile["family_info"] = family

    def _extract_financial_info(self, msg: str, profile: Dict) -> None:
        """Extrai informações financeiras."""
        financial = profile.get("financial_info", {})

        # FGTS
        if re.search(r'\bfgts\b', msg):
            financial["usa_fgts"] = True

            # Valor do FGTS
            fgts_match = re.search(r'fgts.{0,20}(?:de)?\s*(?:r\$)?\s*(\d+(?:\.\d+)?)\s*(?:mil|k)?', msg)
            if fgts_match:
                valor = float(fgts_match.group(1).replace(".", ""))
                if valor < 1000:
                    valor *= 1000
                financial["valor_fgts"] = int(valor)

        # Financiamento aprovado
        if re.search(r'financiamento.{0,20}aprovado|aprovado.{0,20}financiamento', msg):
            financial["financiamento_aprovado"] = True

        # Crédito aprovado
        if re.search(r'cr[eé]dito.{0,20}aprovado|aprovado.{0,20}cr[eé]dito', msg):
            financial["credito_aprovado"] = True

        # Pagamento à vista
        if re.search(r'\bvista\b|dinheiro.{0,10}vista|pagar.{0,10}vista', msg):
            financial["pagamento_vista"] = True

        # Consórcio
        if re.search(r'cons[oó]rcio', msg):
            financial["usa_consorcio"] = True

        # Programa habitacional
        if re.search(r'minha casa|mcmv|casa verde|programa habitacional', msg):
            financial["programa_habitacional"] = True

        # Banco de preferência
        bancos = ["caixa", "itau", "itaú", "bradesco", "santander", "bb", "banco do brasil"]
        for banco in bancos:
            if banco in msg:
                financial["banco_preferencia"] = banco
                break

        # Renda
        renda_match = re.search(r'(?:renda|ganho|salário|salario)\s*(?:de)?\s*(?:r\$)?\s*(\d+(?:\.\d+)?)\s*(?:mil|k)?', msg)
        if renda_match:
            valor = float(renda_match.group(1).replace(".", ""))
            if valor < 100:  # Provavelmente em mil
                valor *= 1000
            financial["renda_aproximada"] = int(valor)

        profile["financial_info"] = financial

    def _extract_objections(self, msg: str, profile: Dict) -> None:
        """Detecta objeções e preocupações."""
        objections = profile.get("objections", [])

        objections_map = {
            "preco": [r'caro|muito caro|acima.{0,20}or[çc]amento|fora.{0,20}or[çc]amento'],
            "localizacao": [r'longe|muito longe|distante'],
            "decisao": [r'preciso pensar|vou pensar|deixa eu ver'],
            "consultar_familia": [r'conversar.{0,20}(?:esposa|marido|fam[ií]lia)|falar.{0,20}(?:esposa|marido)'],
            "documentacao": [r'burocracia|muita papelada|complicado'],
            "reforma": [r'precisa.{0,20}reforma|muito.{0,20}velho'],
            "tamanho": [r'muito pequeno|espa[çc]o.{0,20}pequeno'],
            "seguranca": [r'(?:área|bairro).{0,20}(?:perigoso|inseguro)'],
        }

        for objecao, patterns in objections_map.items():
            for pattern in patterns:
                if re.search(pattern, msg) and objecao not in objections:
                    objections.append(objecao)
                    break

        profile["objections"] = objections

    def _extract_contact_preferences(self, msg: str, profile: Dict) -> None:
        """Extrai preferências de contato."""
        contact = profile.get("contact_preferences", {})

        # Horário preferido
        if re.search(r'manh[aã]|pela manh[aã]', msg):
            contact["horario_preferido"] = "manha"
        elif re.search(r'tarde|[àa] tarde', msg):
            contact["horario_preferido"] = "tarde"
        elif re.search(r'noite|[àa] noite', msg):
            contact["horario_preferido"] = "noite"

        # Canal preferido
        if re.search(r'prefer[oe].{0,10}(?:ligar|liga[çc][aã]o|telefonar)', msg):
            contact["canal_preferido"] = "telefone"
        elif re.search(r'prefer[oe].{0,10}(?:whatsapp|zap|mensagem)', msg):
            contact["canal_preferido"] = "whatsapp"

        profile["contact_preferences"] = contact


# Instância global
lead_profile_extractor = LeadProfileExtractor()


def extract_lead_profile(message: str, current_profile: Dict = None) -> Dict:
    """
    Helper function para extrair perfil de lead.

    Args:
        message: Mensagem do usuário
        current_profile: Perfil atual (opcional)

    Returns:
        Perfil atualizado
    """
    return lead_profile_extractor.extract_from_message(message, current_profile)


def merge_profiles(base_profile: Dict, new_data: Dict) -> Dict:
    """
    Mescla dois perfis, preservando dados existentes e adicionando novos.
    """
    if not base_profile:
        return new_data
    if not new_data:
        return base_profile

    merged = base_profile.copy()

    for key, value in new_data.items():
        if key not in merged or not merged[key]:
            merged[key] = value
        elif isinstance(value, dict) and isinstance(merged[key], dict):
            # Mescla dicionários recursivamente
            for k, v in value.items():
                if k not in merged[key] or not merged[key][k]:
                    merged[key][k] = v
                elif isinstance(v, list):
                    # Acumula listas sem duplicar
                    existing = merged[key].get(k, [])
                    merged[key][k] = list(set(existing + v))
        elif isinstance(value, list):
            # Acumula listas sem duplicar
            existing = merged.get(key, [])
            merged[key] = list(set(existing + value))

    merged["last_updated"] = datetime.now(timezone.utc).isoformat()

    return merged
