"""Conector TCE-PE Dados Abertos (`pe_portal`, SPEC §10). Obrigatório (R1).

A API só responde a IP brasileiro: agente de nuvem usa `--offline` (fixtures) e nunca tenta contornar.
Recorte: conjunto × ano × esfera (× município, se `TCEPE_MUNICIPIOS`). Se a resposta trouxer paginação
(`totalPaginas`), as páginas seguintes são pedidas com o parâmetro `pagina`.

HIPÓTESE até a amostra real: caminhos dos conjuntos (`CONJUNTOS`), formato `!json` e envelope da resposta.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass, replace
from itertools import product
from typing import Any

from lastro_pipeline.config import Settings
from lastro_pipeline.connectors.base import RegistroOrigem
from lastro_pipeline.http import ClienteHttp, montar_url
from lastro_pipeline.modelos import Normalizacao, RespostaBruta
from lastro_pipeline.normalize import pe_portal as mapa
from lastro_pipeline.normalize.cnpj import classificar
from lastro_pipeline.normalize.valores import campo, lista_de_registros

ENVELOPES = ("resposta.conteudo", "conteudo", "dados", "data", "registros")
CAMPOS_TOTAL_PAGINAS = ("resposta.totalPaginas", "totalPaginas", "paginas")


@dataclass(frozen=True)
class Conjunto:
    tipo: str  # 'contrato' | 'empenho' | 'liquidacao' (ver normalize/pe_portal.py)
    caminho: str
    so_municipio: bool = False


CONJUNTOS: tuple[Conjunto, ...] = (
    Conjunto("contrato", "Contratos!json"),
    Conjunto("empenho", "Empenhos!json"),
    Conjunto("liquidacao", "Liquidacoes!json"),
)


class ConectorPePortal:
    fonte_id = mapa.FONTE_ID

    def __init__(self, settings: Settings) -> None:
        self._base = settings.tcepe_base_url
        self._anos = settings.anos_tcepe
        self._esferas = settings.esferas_tcepe
        self._municipios = settings.municipios_tcepe

    def filtros(self) -> dict[str, Any]:
        return {"anos": self._anos, "esferas": self._esferas, "municipios": self._municipios}

    def _recortes(self) -> Iterator[tuple[Conjunto, dict[str, Any]]]:
        municipios: list[str | None] = list(self._municipios) or [None]
        for conjunto, ano, esfera in product(CONJUNTOS, self._anos, self._esferas):
            if conjunto.so_municipio and esfera != "M":
                continue
            for municipio in municipios if esfera == "M" else [None]:
                yield conjunto, {"AnoReferencia": ano, "Esfera": esfera, "CodigoMunicipio": municipio}

    def coletar(self, cliente: ClienteHttp) -> Iterator[RespostaBruta]:
        for conjunto, params in self._recortes():
            pagina, total = 1, 1
            while pagina <= total:
                extra = {"pagina": pagina} if pagina > 1 else {}
                url = montar_url(self._base, conjunto.caminho, {**params, **extra})
                r = cliente.get(url)
                yield RespostaBruta(
                    conteudo=r.conteudo,
                    url_origem=url,
                    nome=_nome_arquivo(conjunto, params, pagina),
                    coletado_em=r.coletado_em,
                    metadados={"tipo": conjunto.tipo, "esfera": params["Esfera"]},
                )
                total = _total_paginas(r.conteudo)
                pagina += 1

    def interpretar(self, resposta: RespostaBruta) -> Iterator[RegistroOrigem]:
        yield from lista_de_registros(json.loads(resposta.conteudo), ENVELOPES)

    def normalizar(self, registro: RegistroOrigem, resposta: RespostaBruta) -> Normalizacao:
        return mapa.normalizar(
            registro, resposta.metadados["tipo"], resposta.url_origem, resposta.metadados.get("esfera")
        )

    def amostra(self, cliente: ClienteHttp, linhas: int) -> list[RespostaBruta]:
        """Até `linhas` registros de PJ, divididos entre os conjuntos e as esferas. CPF nunca vai para a fixture."""
        recortes = list(self._recortes())
        por_recorte = max(1, linhas // max(1, len(recortes)))
        amostras = []
        for resposta in self.coletar(cliente):
            pj = [
                r
                for r in self.interpretar(resposta)
                if classificar(campo(r, *mapa.CAMPOS_DOCUMENTO))[0] == "cnpj"
            ][:por_recorte]
            if pj:
                amostras.append(
                    replace(resposta, conteudo=json.dumps(pj, ensure_ascii=False, indent=1).encode())
                )
            if sum(len(json.loads(a.conteudo)) for a in amostras) >= linhas:
                break
        return amostras


def _nome_arquivo(conjunto: Conjunto, params: dict[str, Any], pagina: int) -> str:
    municipio = f"_m{params['CodigoMunicipio']}" if params.get("CodigoMunicipio") else ""
    return f"{conjunto.tipo}_{params['AnoReferencia']}_{params['Esfera']}{municipio}_p{pagina:04d}.json"


def _total_paginas(conteudo: bytes) -> int:
    try:
        valor = campo(json.loads(conteudo), *CAMPOS_TOTAL_PAGINAS)
    except ValueError:
        return 1
    return int(valor) if isinstance(valor, int | str) and str(valor).isdigit() else 1
