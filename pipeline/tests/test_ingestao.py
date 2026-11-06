"""Critério de aceite comum de T05, T06 e T07, contra o Postgres real como `lastro_ingest`.

Cada teste roda numa transação desfeita no fim (fixture `conn`), então não deixa linhas no banco.
"""

import json
from dataclasses import replace

import pytest

from lastro_pipeline import fixtures, runner
from lastro_pipeline.connectors import conectores
from tests.conftest import FIXTURES

TABELA_POR_FONTE = {"pe_portal": ("contratos", "pagamentos"), "pncp": ("contratos",), "ceis": ("sancoes",)}
TABELA_POR_FONTE["cnep"] = ("sancoes",)


def _contar(conn, tabela: str, fonte_id: str) -> int:
    sql = {
        "contratos": "select count(*) from contratos where fonte_id = %s",
        "pagamentos": "select count(*) from pagamentos where fonte_id = %s",
        "sancoes": "select count(*) from sancoes where fonte_id = %s",
    }[tabela]
    return conn.execute(sql, (fonte_id,)).fetchone()[0]


def _rodar(conn, conector):
    respostas = fixtures.ler_fonte(FIXTURES / conector.fonte_id)
    return runner.executar(conn, conector, respostas, "offline", raw_dir=None)


@pytest.mark.parametrize("fonte", ["pe_portal", "pncp", "ceis", "cnep"])
def test_duas_execucoes_dao_contagens_estaveis(conn, settings, fonte):
    (conector,) = conectores(fonte, settings)
    primeira = _rodar(conn, conector)
    contagens = {t: _contar(conn, t, fonte) for t in TABELA_POR_FONTE[fonte]}
    segunda = _rodar(conn, conector)

    assert primeira.status == segunda.status == "ok"
    assert all(n > 0 for n in contagens.values())
    assert {t: _contar(conn, t, fonte) for t in TABELA_POR_FONTE[fonte]} == contagens
    assert (segunda.contagem.novos, segunda.contagem.atualizados) == (0, 0)
    assert segunda.contagem.lidos == primeira.contagem.lidos
    assert segunda.contagem.descartados == primeira.contagem.descartados


def test_execucao_registrada_com_contagens_e_qualidade(conn, settings):
    (conector,) = conectores("pe_portal", settings)
    resumo = _rodar(conn, conector)
    linha = conn.execute(
        "select status, registros_lidos, registros_descartados, parametros, finalizada_em "
        "from execucoes_ingestao where id = %s",
        (resumo.execucao_id,),
    ).fetchone()
    status, lidos, descartados, parametros, finalizada = linha
    assert status == "ok" and finalizada is not None
    assert lidos == resumo.contagem.lidos
    assert descartados == 2
    assert parametros["qualidade"]["descartes"] == {"pessoa_fisica": 2}
    assert parametros["filtros"]["modo"] == "offline"


def test_pessoa_fisica_nunca_chega_ao_banco(conn, settings):
    for fonte in ("pe_portal", "pncp", "ceis"):
        (conector,) = conectores(fonte, settings)
        _rodar(conn, conector)
    assert conn.execute(
        "select count(*) from fornecedores where razao_social ilike '%pessoa f%sint%'"
    ).fetchone() == (0,)
    assert conn.execute(
        "select count(*) from contratos where objeto ilike '%deve ser descartad%'"
    ).fetchone() == (0,)
    assert conn.execute("select count(*) from sancoes where id_origem = '9000001'").fetchone() == (0,)


def test_pncp_nao_grava_pe_sem_fallback(conn, settings):
    (conector,) = conectores("pncp", settings)
    _rodar(conn, conector)
    assert conn.execute(
        "select count(*) from contratos where fonte_id = 'pncp' and uf = 'PE'"
    ).fetchone() == (0,)


def test_proveniencia_completa_em_toda_linha(conn, settings):
    for fonte in ("pe_portal", "pncp", "ceis"):
        (conector,) = conectores(fonte, settings)
        _rodar(conn, conector)
    for tabela in ("contratos", "pagamentos", "sancoes"):
        sem_proveniencia = conn.execute(
            f"select count(*) from {tabela} where fonte_id in ('pe_portal', 'pncp', 'ceis') and ("
            "id_origem is null or url_origem is null or coletado_em is null "
            "or hash_conteudo is null or arquivo_bruto_id is null)"
        ).fetchone()
        assert sem_proveniencia == (0,), tabela


def test_bronze_grava_arquivo_e_nao_duplica_sha(conn, settings):
    (conector,) = conectores("ceis", settings)
    respostas = list(fixtures.ler_fonte(FIXTURES / "ceis"))
    runner.executar(conn, conector, respostas, "online", settings.raw_dir)
    runner.executar(conn, conector, respostas, "online", settings.raw_dir)
    shas = [r.sha256 for r in respostas]
    linhas = conn.execute(
        "select count(*), count(distinct sha256) from arquivos_brutos where fonte_id = 'ceis' and sha256 = any(%s)",
        (shas,),
    ).fetchone()
    assert linhas == (len(shas), len(shas))
    assert len(list(settings.raw_dir.glob("ceis/*/*"))) == len(shas)


def test_conteudo_alterado_atualiza_sem_duplicar(conn, settings):
    (conector,) = conectores("pncp", settings)
    _rodar(conn, conector)
    original = next(fixtures.ler(FIXTURES / "pncp" / "amostra"))
    corpo = json.loads(original.conteudo)
    corpo["data"] = [r for r in corpo["data"] if r["unidadeOrgao"]["ufSigla"] == "AL"][:1]
    corpo["data"][0]["valorGlobal"] = 1.23
    alterada = replace(original, conteudo=json.dumps(corpo).encode())
    resumo = runner.executar(conn, conector, [alterada], "offline", raw_dir=None)
    assert (resumo.contagem.novos, resumo.contagem.atualizados) == (0, 1)
    valor = conn.execute(
        "select valor_global from contratos where fonte_id = 'pncp' and id_origem = %s",
        (corpo["data"][0]["numeroControlePNCP"],),
    ).fetchone()
    assert str(valor[0]) == "1.23"


def test_queda_de_volume_marca_execucao_parcial(conn, settings):
    (conector,) = conectores("ceis", settings)
    _rodar(conn, conector)
    so_manual = list(fixtures.ler(FIXTURES / "ceis" / "exemplo_manual"))
    resumo = runner.executar(conn, conector, so_manual, "offline", raw_dir=None)
    assert resumo.status == "parcial"
    assert resumo.qualidade["queda_de_volume"] is True
    assert _contar(conn, "sancoes", "ceis") > len(so_manual)  # nada foi apagado


def test_falha_fica_registrada_e_nao_grava_fatos(conn, settings):
    (conector,) = conectores("ceis", settings)
    quebrada = replace(next(fixtures.ler(FIXTURES / "ceis" / "amostra")), conteudo=b"A;B\n1;2\n")
    with pytest.raises(ValueError):
        runner.executar(conn, conector, [quebrada], "offline", raw_dir=None)
    status, erro = conn.execute(
        "select status, erro from execucoes_ingestao where fonte_id = 'ceis' order by iniciada_em desc limit 1"
    ).fetchone()
    assert status == "falhou"
    assert "colunas ausentes" in erro
