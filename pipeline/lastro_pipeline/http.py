"""Cliente HTTP comum a todos os conectores (AGENTS.md §9).

- no máximo N requisições por segundo (`REQUESTS_PER_SECOND`, padrão 1), por cliente;
- retry com backoff exponencial em erro de rede, 404 intermitente, 429 e 5xx;
- cache em disco por URL, válido no dia (reexecução no mesmo dia não volta à fonte);
- cabeçalho `User-Agent: lastro-hackathon`, sem e-mail.

Bloqueio (403, firewall) não é contornado: vira `FonteBloqueada` e o conector usa o download manual.
"""

import hashlib
import json
import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Self
from urllib.parse import urlencode

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from lastro_pipeline.config import USER_AGENT

log = logging.getLogger(__name__)

STATUS_REPETIR = {404, 408, 425, 429, 500, 502, 503, 504}


class FonteIndisponivel(Exception):
    """A fonte não respondeu depois das tentativas."""


class FonteBloqueada(Exception):
    """A fonte recusou o acesso (403, captcha, firewall). Não contornar: usar download manual."""


class _Repetir(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(f"status {status}")
        self.status = status


@dataclass(frozen=True)
class Resposta:
    status: int
    conteudo: bytes
    url: str
    coletado_em: datetime
    do_cache: bool = False


class LimitadorTaxa:
    """Garante intervalo mínimo entre requisições. Relógio e espera injetáveis para teste."""

    def __init__(
        self,
        por_segundo: float,
        relogio: Callable[[], float] = time.monotonic,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self._intervalo = 1.0 / por_segundo if por_segundo > 0 else 0.0
        self._relogio = relogio
        self._dormir = dormir
        self._ultima: float | None = None

    def aguardar(self) -> None:
        agora = self._relogio()
        if self._ultima is not None:
            falta = self._intervalo - (agora - self._ultima)
            if falta > 0:
                self._dormir(falta)
                agora += falta
        self._ultima = agora


def montar_url(base: str, caminho: str = "", params: Mapping[str, object] | None = None) -> str:
    url = base.rstrip("/") + ("/" + caminho.lstrip("/") if caminho else "")
    if params:
        url += "?" + urlencode({k: v for k, v in params.items() if v not in (None, "")})
    return url


class ClienteHttp:
    def __init__(
        self,
        fonte_id: str,
        cache_dir: Path | None,
        por_segundo: float = 1.0,
        tentativas: int = 5,
        timeout: float = 60.0,
        transporte: httpx.BaseTransport | None = None,
        limitador: LimitadorTaxa | None = None,
        espera_minima: float = 1.0,
        espera_maxima: float = 60.0,
    ) -> None:
        self.fonte_id = fonte_id
        self._cache_dir = cache_dir / fonte_id if cache_dir else None
        self._limitador = limitador or LimitadorTaxa(por_segundo)
        self._http = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            timeout=timeout,
            follow_redirects=True,
            transport=transporte,
        )
        self._buscar_com_retry = retry(
            retry=retry_if_exception_type((_Repetir, httpx.TransportError)),
            wait=wait_exponential(multiplier=espera_minima, min=espera_minima, max=espera_maxima),
            stop=stop_after_attempt(tentativas),
            reraise=True,
        )(self._buscar)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self._http.close()

    def get(self, url: str, aceitar: frozenset[int] = frozenset({200})) -> Resposta:
        """GET com cache, limite de taxa e retry. `aceitar` lista os status tratados como resposta válida."""
        em_cache = self._ler_cache(url)
        if em_cache is not None:
            return em_cache
        try:
            resposta = self._buscar_com_retry(url, aceitar)
        except _Repetir as erro:
            raise FonteIndisponivel(f"{self.fonte_id}: {url} respondeu {erro.status}") from erro
        except httpx.TransportError as erro:
            raise FonteIndisponivel(f"{self.fonte_id}: {url} falhou ({type(erro).__name__})") from erro
        self._gravar_cache(resposta)
        return resposta

    def _buscar(self, url: str, aceitar: frozenset[int]) -> Resposta:
        self._limitador.aguardar()
        log.info("GET %s", url)
        r = self._http.get(url)
        if r.status_code in aceitar:
            return Resposta(r.status_code, r.content, url, datetime.now(UTC))
        if r.status_code in (401, 403):
            raise FonteBloqueada(f"{self.fonte_id}: {url} respondeu {r.status_code}")
        if r.status_code in STATUS_REPETIR:
            raise _Repetir(r.status_code)
        raise FonteIndisponivel(f"{self.fonte_id}: {url} respondeu {r.status_code}")

    def _caminho_cache(self, url: str) -> Path | None:
        if self._cache_dir is None:
            return None
        chave = hashlib.sha256(url.encode()).hexdigest()
        return self._cache_dir / date.today().isoformat() / chave

    def _ler_cache(self, url: str) -> Resposta | None:
        caminho = self._caminho_cache(url)
        if caminho is None or not caminho.exists():
            return None
        meta = json.loads(caminho.with_suffix(".json").read_text())
        return Resposta(
            meta["status"], caminho.read_bytes(), url, datetime.fromisoformat(meta["coletado_em"]), True
        )

    def _gravar_cache(self, resposta: Resposta) -> None:
        caminho = self._caminho_cache(resposta.url)
        if caminho is None or resposta.status != 200:  # erro ou "sem dado hoje" não vira cache
            return
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(resposta.conteudo)
        meta = {
            "url": resposta.url,
            "status": resposta.status,
            "coletado_em": resposta.coletado_em.isoformat(),
        }
        caminho.with_suffix(".json").write_text(json.dumps(meta))
