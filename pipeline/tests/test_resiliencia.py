"""SPEC §14.5: fonte fora do ar. A ingestão marca a execução como falha e não apaga o que já estava no banco."""

from collections.abc import Iterator

import pytest

from lastro_pipeline import fixtures, runner
from lastro_pipeline.connectors import conectores
from lastro_pipeline.http import FonteBloqueada, FonteIndisponivel
from lastro_pipeline.modelos import RespostaBruta
from tests.conftest import FIXTURES


def _contar_sancoes(conn) -> int:
    return conn.execute("select count(*) from sancoes where fonte_id = 'ceis'").fetchone()[0]


def _execucoes_que_falharam(conn) -> list[tuple[str, int]]:
    """O teste roda numa transação só (now() fixo): filtra por status em vez de ordenar por horário."""
    return conn.execute(
        "select erro, registros_lidos from execucoes_ingestao where fonte_id = 'ceis' and status = 'falhou'"
    ).fetchall()


def _cai_no_meio(erro: Exception) -> Iterator[RespostaBruta]:
    """Entrega a primeira página da amostra e depois a fonte para de responder."""
    yield next(fixtures.ler(FIXTURES / "ceis" / "amostra"))
    raise erro


@pytest.mark.parametrize(
    "erro", [FonteIndisponivel("503 depois de 3 tentativas"), FonteBloqueada("403")], ids=["fora", "bloqueada"]
)
def test_fonte_que_cai_no_meio_marca_falha_e_nao_apaga_dados(conn, settings, erro):
    (conector,) = conectores("ceis", settings)
    runner.executar(conn, conector, fixtures.ler_fonte(FIXTURES / "ceis"), "offline", raw_dir=None)
    antes = _contar_sancoes(conn)
    assert antes > 0

    with pytest.raises(type(erro)):
        runner.executar(conn, conector, _cai_no_meio(erro), "offline", raw_dir=None)

    ((mensagem, lidos),) = _execucoes_que_falharam(conn)
    assert type(erro).__name__ in mensagem
    assert lidos == 0  # a primeira página não entra pela metade
    assert _contar_sancoes(conn) == antes


def test_fonte_fora_desde_o_inicio_nao_mexe_em_nada(conn, settings):
    (conector,) = conectores("ceis", settings)
    runner.executar(conn, conector, fixtures.ler_fonte(FIXTURES / "ceis"), "offline", raw_dir=None)
    antes = _contar_sancoes(conn)

    def fora() -> Iterator[RespostaBruta]:
        raise FonteIndisponivel("timeout")
        yield  # pragma: no cover

    with pytest.raises(FonteIndisponivel):
        runner.executar(conn, conector, fora(), "offline", raw_dir=None)
    assert len(_execucoes_que_falharam(conn)) == 1
    assert _contar_sancoes(conn) == antes
