"""Conector PNCP (`pncp`, SPEC §10): contratos das UFs de `PNCP_UFS` num período.

`/v1/contratos` não filtra por UF: o período é dividido em janelas mensais, cada janela é paginada
(`tamanhoPagina` até 500) e o filtro de UF é aplicado aqui. **PE nunca vem do PNCP**, salvo
`PNCP_PE_FALLBACK=true` (PE é do TCE-PE; sem sobreposição). 204 = janela sem contratos.
404 intermitente é tratado pelo retry do cliente HTTP.
"""

import json
from collections.abc import Iterator
from dataclasses import replace
from datetime import date, timedelta
from typing import Any

from lastro_pipeline.config import Settings
from lastro_pipeline.connectors.base import RegistroOrigem
from lastro_pipeline.http import ClienteHttp, montar_url
from lastro_pipeline.modelos import Normalizacao, RespostaBruta
from lastro_pipeline.normalize import pncp as mapa
from lastro_pipeline.normalize.cnpj import classificar

ROTA = "v1/contratos"
STATUS_OK = frozenset({200, 204})
MAX_PAGINAS_AMOSTRA = 40
# A amostra guarda algumas linhas de PE de propósito: o teste prova que elas não entram sem o fallback.
FRACAO_PE_NA_AMOSTRA = 0.1
# Campos que podem identificar pessoa física (subcontratado, usuário, texto livre) não vão para a fixture.
CAMPOS_FORA_DA_AMOSTRA = frozenset(
    {
        "tipoPessoaSubContratada",
        "niFornecedorSubContratado",
        "nomeFornecedorSubContratado",
        "usuarioNome",
        "informacaoComplementar",
    }
)


def janelas_mensais(inicio: date, fim: date) -> Iterator[tuple[date, date]]:
    atual = inicio
    while atual <= fim:
        proximo_mes = (atual.replace(day=1) + timedelta(days=32)).replace(day=1)
        yield atual, min(fim, proximo_mes - timedelta(days=1))
        atual = proximo_mes


class ConectorPncp:
    fonte_id = mapa.FONTE_ID

    def __init__(self, settings: Settings) -> None:
        self._base = settings.pncp_base_url
        self._ufs = set(settings.ufs_pncp)
        self._inicio, self._fim = settings.periodo_pncp
        self._tamanho = min(500, max(10, settings.pncp_tamanho_pagina))

    def filtros(self) -> dict[str, Any]:
        return {
            "ufs": sorted(self._ufs),
            "data_inicial": self._inicio.isoformat(),
            "data_final": self._fim.isoformat(),
        }

    def _paginas(self, cliente: ClienteHttp, inicio: date, fim: date) -> Iterator[RespostaBruta]:
        pagina, restantes = 1, 1
        while restantes > 0:
            params = {
                "dataInicial": inicio.strftime("%Y%m%d"),
                "dataFinal": fim.strftime("%Y%m%d"),
                "pagina": pagina,
                "tamanhoPagina": self._tamanho,
            }
            url = montar_url(self._base, ROTA, params)
            r = cliente.get(url, aceitar=STATUS_OK)
            if r.status == 204 or not r.conteudo.strip():
                return
            corpo = json.loads(r.conteudo)
            yield RespostaBruta(
                conteudo=r.conteudo,
                url_origem=url,
                nome=f"contratos_{params['dataInicial']}_{params['dataFinal']}_p{pagina:04d}.json",
                coletado_em=r.coletado_em,
            )
            restantes = int(corpo.get("paginasRestantes") or 0)
            pagina += 1

    def coletar(self, cliente: ClienteHttp) -> Iterator[RespostaBruta]:
        for inicio, fim in janelas_mensais(self._inicio, self._fim):
            yield from self._paginas(cliente, inicio, fim)

    def interpretar(self, resposta: RespostaBruta) -> Iterator[RegistroOrigem]:
        """Só os contratos das UFs permitidas contam como lidos nesta execução."""
        for registro in json.loads(resposta.conteudo).get("data") or []:
            if mapa.uf_do_registro(registro) in self._ufs:
                yield registro

    def normalizar(self, registro: RegistroOrigem, resposta: RespostaBruta) -> Normalizacao:
        return mapa.normalizar(registro, self._ufs)

    def amostra(self, cliente: ClienteHttp, linhas: int) -> list[RespostaBruta]:
        """Contratos de PJ das UFs alvo (e alguns de PE), das janelas mais recentes do período."""
        cota_pe = max(1, int(linhas * FRACAO_PE_NA_AMOSTRA))
        alvo: list[RegistroOrigem] = []
        pe: list[RegistroOrigem] = []
        primeira: RespostaBruta | None = None
        paginas = 0
        for inicio, fim in reversed(list(janelas_mensais(self._inicio, self._fim))):
            for resposta in self._paginas(cliente, inicio, fim):
                primeira = primeira or resposta
                paginas += 1
                for registro in json.loads(resposta.conteudo).get("data") or []:
                    if classificar(registro.get("niFornecedor"))[0] != "cnpj":
                        continue
                    sigla = mapa.uf_do_registro(registro)
                    if sigla in self._ufs and len(alvo) < linhas - cota_pe:
                        alvo.append(_sem_campos_sensiveis(registro))
                    elif sigla == "PE" and "PE" not in self._ufs and len(pe) < cota_pe:
                        pe.append(_sem_campos_sensiveis(registro))
                if len(alvo) + len(pe) >= linhas or paginas >= MAX_PAGINAS_AMOSTRA:
                    break
            if len(alvo) + len(pe) >= linhas or paginas >= MAX_PAGINAS_AMOSTRA:
                break
        if primeira is None:
            return []
        registros = alvo + pe
        corpo = {
            "data": registros,
            "totalRegistros": len(registros),
            "totalPaginas": 1,
            "numeroPagina": 1,
            "paginasRestantes": 0,
            "empty": not registros,
        }
        conteudo = json.dumps(corpo, ensure_ascii=False, indent=1).encode("utf-8")
        return [replace(primeira, conteudo=conteudo, nome="contratos_amostra.json")]


def _sem_campos_sensiveis(registro: RegistroOrigem) -> RegistroOrigem:
    return {k: v for k, v in registro.items() if k not in CAMPOS_FORA_DA_AMOSTRA}
