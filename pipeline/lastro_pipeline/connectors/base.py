"""Contrato comum dos conectores.

Um conector só sabe três coisas sobre a sua fonte:
  1. `coletar`: buscar as respostas brutas (online), paginando e respeitando o cliente HTTP comum;
  2. `interpretar`: transformar uma resposta bruta em registros de origem (dict);
  3. `normalizar`: mapear um registro de origem para o esquema (ou descartá-lo).

Bronze, upsert, qualidade e registro da execução ficam no `runner` e valem para todas as fontes.
Fonte nova = um módulo novo em `connectors/` + o mapeamento em `normalize/` + uma linha no registro.
"""

from collections.abc import Iterator
from typing import Any, Protocol

from lastro_pipeline.http import ClienteHttp
from lastro_pipeline.modelos import Normalizacao, RespostaBruta

RegistroOrigem = dict[str, Any]


class Conector(Protocol):
    fonte_id: str

    def filtros(self) -> dict[str, Any]:
        """Parâmetros que definem o recorte (UFs, anos, período). Vão para `execucoes_ingestao.parametros`."""
        ...

    def coletar(self, cliente: ClienteHttp) -> Iterator[RespostaBruta]: ...

    def interpretar(self, resposta: RespostaBruta) -> Iterator[RegistroOrigem]: ...

    def normalizar(self, registro: RegistroOrigem, resposta: RespostaBruta) -> Normalizacao: ...

    def amostra(self, cliente: ClienteHttp, linhas: int) -> list[RespostaBruta]:
        """Coleta online e recorta até `linhas` registros de pessoa jurídica para `data/fixtures/`."""
        ...
