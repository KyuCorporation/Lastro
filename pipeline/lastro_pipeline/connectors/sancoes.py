"""Conectores CEIS e CNEP (`ceis`, `cnep`, SPEC §10): arquivo diário de dados abertos da CGU.

Online: `<SANCOES_DOWNLOAD_URL>/<cadastro>/<AAAAMMDD>` devolve um zip com um CSV (latin-1, `;`). Dia sem
arquivo responde 403 (S3 AccessDenied), por isso o conector volta até `SANCOES_DIAS_RETROATIVOS` dias.
Se nada vier (fonte fora ou firewall), **não contorna**: lê o download manual em `data/raw/sancoes/`
(arquivos `*CEIS*.zip|csv` ou `*CNEP*.zip|csv`, baixados no navegador).
"""

import csv
import io
import logging
import zipfile
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from lastro_pipeline.config import Settings
from lastro_pipeline.connectors.base import RegistroOrigem
from lastro_pipeline.http import ClienteHttp, FonteBloqueada, FonteIndisponivel, montar_url
from lastro_pipeline.modelos import Normalizacao, RespostaBruta
from lastro_pipeline.normalize import sancoes as mapa

log = logging.getLogger(__name__)

CADASTROS = ("ceis", "cnep")
ACEITAR = frozenset({200, 403, 404})


class ArquivoInvalido(ValueError):
    pass


def ler_csv(conteudo: bytes) -> tuple[list[str], Iterator[list[str]]]:
    """Aceita o zip da CGU ou o CSV solto. Devolve cabeçalho normalizado e linhas."""
    if conteudo[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not nomes:
                raise ArquivoInvalido("zip sem CSV")
            conteudo = z.read(nomes[0])
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = conteudo.decode("latin-1")
    leitor = csv.reader(io.StringIO(texto), delimiter=";")
    cabecalho = [mapa.chave_coluna(c) for c in next(leitor, [])]
    faltando = [c for c in mapa.COLUNAS_OBRIGATORIAS if c not in cabecalho]
    if faltando:
        raise ArquivoInvalido(f"colunas ausentes: {', '.join(faltando)}")
    return cabecalho, leitor


def escrever_csv(cabecalho: list[str], linhas: list[list[str]]) -> bytes:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\n")
    escritor.writerow(cabecalho)
    escritor.writerows(linhas)
    return saida.getvalue().encode("utf-8")


class ConectorSancoes:
    def __init__(self, settings: Settings, cadastro: str, hoje: date | None = None) -> None:
        if cadastro not in CADASTROS:
            raise ValueError(f"cadastro desconhecido: {cadastro}")
        self.fonte_id = cadastro
        self._base = settings.sancoes_download_url
        self._dias = settings.sancoes_dias_retroativos
        self._manual_dir = settings.raw_dir / "sancoes"
        self._hoje = hoje

    def filtros(self) -> dict[str, Any]:
        return {"cadastro": self.fonte_id}

    def coletar(self, cliente: ClienteHttp) -> Iterator[RespostaBruta]:
        hoje = self._hoje or date.today()
        for atraso in range(self._dias + 1):
            dia = hoje - timedelta(days=atraso)
            url = montar_url(self._base, f"{self.fonte_id}/{dia:%Y%m%d}")
            try:
                r = cliente.get(url, aceitar=ACEITAR)
            except (FonteIndisponivel, FonteBloqueada) as erro:
                log.warning("%s: %s", self.fonte_id, erro)
                break
            if r.status == 200 and r.conteudo[:2] == b"PK":
                yield RespostaBruta(
                    r.conteudo, url, f"{dia:%Y%m%d}_{self.fonte_id.upper()}.zip", r.coletado_em
                )
                return
        yield from self._manual()

    def _manual(self) -> Iterator[RespostaBruta]:
        arquivos = sorted(
            p
            for p in self._manual_dir.glob(f"*{self.fonte_id.upper()}*")
            if p.suffix.lower() in (".zip", ".csv")
        )
        if not arquivos:
            raise FonteIndisponivel(
                f"{self.fonte_id}: download indisponível e nenhum arquivo manual em {self._manual_dir}. "
                f"Baixe no navegador em {self._base}/{self.fonte_id} e salve nessa pasta."
            )
        caminho = arquivos[-1]
        log.warning("%s: usando download manual %s", self.fonte_id, caminho)
        coletado = datetime.fromtimestamp(caminho.stat().st_mtime, UTC)
        yield RespostaBruta(caminho.read_bytes(), f"{self._base}/{self.fonte_id}", caminho.name, coletado)

    def interpretar(self, resposta: RespostaBruta) -> Iterator[RegistroOrigem]:
        cabecalho, linhas = ler_csv(resposta.conteudo)
        for linha in linhas:
            if linha:
                yield dict(zip(cabecalho, linha, strict=False))

    def normalizar(self, registro: RegistroOrigem, resposta: RespostaBruta) -> Normalizacao:
        return mapa.normalizar(registro, self.fonte_id, resposta.url_origem)

    def amostra(self, cliente: ClienteHttp, linhas: int) -> list[RespostaBruta]:
        """Primeiras `linhas` sanções de PJ, só com as colunas usadas. Pessoa física nunca vai para a fixture."""
        for resposta in self.coletar(cliente):
            cabecalho, todas = ler_csv(resposta.conteudo)
            indice = cabecalho.index(mapa.COL_TIPO_PESSOA)
            pj = [linha for linha in todas if len(linha) > indice and linha[indice].strip() == "J"][:linhas]
            colunas = [cabecalho.index(c) for c in mapa.COLUNAS_AMOSTRA if c in cabecalho]
            recorte = [[linha[i] if i < len(linha) else "" for i in colunas] for linha in pj]
            nome = Path(resposta.nome).with_suffix(".csv").name
            conteudo = escrever_csv([cabecalho[i] for i in colunas], recorte)
            return [replace(resposta, conteudo=conteudo, nome=nome)]
        return []
