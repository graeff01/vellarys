import requests
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# ==========================================================
# MAPEAMENTO: CÓDIGO HUMANO → SLUG REAL DO PORTAL
# ==========================================================
PROPERTY_CODE_MAP = {
    "722585": "poa001",
    # futuros:
    # "722586": "poa002",
}


class PropertyLookupService:
    """
    Serviço responsável por buscar dados de imóveis no Portal de Investimento.
    Totalmente isolado, seguro e tolerante a falhas.
    """

    BASE_URL = "https://portalinvestimento.com"
    TIMEOUT = 4  # segundos (curto para não travar atendimento)
    USER_AGENT = "VellarysBot/1.0 (+https://vellarys.ai)"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        })

    # ==========================================================
    # BUSCA POR CÓDIGO (fallback / legado)
    # ==========================================================
    @lru_cache(maxsize=128)
    def buscar_por_codigo(self, codigo: str) -> Optional[dict]:
        """
        Busca um imóvel pelo código direto (fallback).
        Retorna dict normalizado ou None.
        """
        try:
            logger.info(f"🔎 PortalLookup | Buscando imóvel código={codigo}")

            url = f"{self.BASE_URL}/imovel/{codigo}"

            response = self.session.get(
                url,
                timeout=self.TIMEOUT,
                verify=True
            )

            if response.status_code != 200:
                logger.warning(
                    f"PortalLookup | HTTP {response.status_code} para código {codigo}"
                )
                return None

            html = response.text

            if "<title>" not in html:
                logger.warning(f"PortalLookup | HTML inválido para código {codigo}")
                return None

            return self._parse_html(codigo, html)

        except requests.Timeout:
            logger.warning(f"⏱️ PortalLookup timeout para código {codigo}")
            return None

        except requests.RequestException as e:
            logger.error(f"❌ PortalLookup erro HTTP: {e}")
            return None

        except Exception as e:
            logger.error(f"❌ PortalLookup erro inesperado: {e}")
            return None

    # ==========================================================
    # BUSCA POR SLUG REAL (RECOMENDADO / PRD)
    # ==========================================================
    @lru_cache(maxsize=128)
    def buscar_por_slug(self, slug: str) -> Optional[dict]:
        """
        Busca imóvel pelo slug real do Portal (ex: poa001)
        """
        try:
            logger.info(f"🔎 PortalLookup | Buscando imóvel slug={slug}")

            url = f"{self.BASE_URL}/imovel.html?id={slug}"

            response = self.session.get(
                url,
                timeout=self.TIMEOUT,
                verify=True
            )

            if response.status_code != 200:
                logger.warning(
                    f"PortalLookup | HTTP {response.status_code} para slug {slug}"
                )
                return None

            html = response.text

            if "<title>" not in html:
                logger.warning(f"PortalLookup | HTML inválido para slug {slug}")
                return None

            return self._parse_html(slug, html)

        except requests.Timeout:
            logger.warning(f"⏱️ PortalLookup timeout para slug {slug}")
            return None

        except requests.RequestException as e:
            logger.error(f"❌ PortalLookup erro HTTP slug {slug}: {e}")
            return None

        except Exception as e:
            logger.error(f"❌ PortalLookup erro inesperado slug {slug}: {e}")
            return None

    # ==========================================================
    # PARSER (ISOLADO E DEFENSIVO)
    # ==========================================================
    def _parse_html(self, identificador: str, html: str) -> Optional[dict]:
        """
        Parser simples e tolerante a mudanças de HTML.
        """

        try:
            def extract_between(text, start, end):
                if start not in text or end not in text:
                    return None
                return text.split(start)[1].split(end)[0].strip()

            titulo = extract_between(html, "<title>", "</title>")
            if titulo:
                titulo = titulo.replace(" | Portal de Investimento", "").strip()

            descricao = extract_between(
                html,
                '<meta name="description" content="',
                '"'
            )

            return {
                "codigo": identificador,
                "titulo": titulo or f"Imóvel código {identificador}",
                "tipo": "Imóvel residencial",
                "regiao": "Consulte detalhes",
                "quartos": "Consulte",
                "banheiros": "Consulte",
                "vagas": "Consulte",
                "metragem": "Consulte",
                "preco": "Consulte",
                "descricao": descricao or "Imóvel disponível para mais informações.",
                "link": f"{self.BASE_URL}/imovel.html?id={identificador}",
                "fonte": "portalinvestimento.com",
            }

        except Exception as e:
            logger.error(
                f"❌ Erro ao parsear HTML do imóvel {identificador}: {e}"
            )
            return None
