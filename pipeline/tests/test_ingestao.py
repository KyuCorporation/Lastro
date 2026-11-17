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


# ===================== sanção retirada do cadastro (P4.1, migration 008) =====================
# O banco de teste pode já ter sanções de outras fixtures (exemplo_manual): cada teste compara com o estado inicial.
def _ceis_sem_a_primeira_linha():
    """A amostra do CEIS sem a primeira sanção: o arquivo do dia seguinte, em que ela saiu do cadastro."""
    (resposta,) = fixtures.ler(FIXTURES / "ceis" / "amostra")
    cabecalho, _primeira, *resto = resposta.conteudo.decode("utf-8").splitlines(keepends=True)
    return resposta, replace(
        resposta, conteudo="".join([cabecalho, *resto]).encode("utf-8"), nome="sem_uma.csv"
    )


def _removidas(conn) -> set[str]:
    return {
        i
        for (i,) in conn.execute(
            "select id_origem from sancoes where fonte_id = 'ceis' and removida_em is not null"
        )
    }


def _ids(conector, resposta) -> set[str]:
    return {
        n.fato.id_origem
        for r in conector.interpretar(resposta)
        if hasattr(n := conector.normalizar(r, resposta), "fato")
    }


def test_coleta_completa_marca_a_sancao_que_saiu_do_cadastro(conn, settings):
    (conector,) = conectores("ceis", settings)
    completa, sem_uma = _ceis_sem_a_primeira_linha()
    runner.executar(conn, conector, [completa], "online", settings.raw_dir)
    antes = _removidas(conn)
    assert not (antes & _ids(conector, completa))  # tudo o que veio no arquivo está presente

    resumo = runner.executar(conn, conector, [sem_uma], "online", settings.raw_dir)
    assert resumo.status == "ok"
    (removida,) = _removidas(conn) - antes
    assert removida in _ids(conector, completa) - _ids(conector, sem_uma)
    detalhes = conn.execute(
        "select parametros from execucoes_ingestao where id = %s", (resumo.execucao_id,)
    ).fetchone()[0]
    assert detalhes["removidas"] == 1

    # Voltou ao cadastro: deixa de estar removida.
    runner.executar(conn, conector, [completa], "online", settings.raw_dir)
    assert _removidas(conn) == antes


def test_fixture_offline_nao_remove_nada(conn, settings):
    """A fixture é um recorte, não o cadastro inteiro: ausência nela não quer dizer nada."""
    (conector,) = conectores("ceis", settings)
    completa, sem_uma = _ceis_sem_a_primeira_linha()
    antes = _removidas(conn)
    runner.executar(conn, conector, [completa], "offline", raw_dir=None)
    runner.executar(conn, conector, [sem_uma], "offline", raw_dir=None)
    assert _removidas(conn) == antes


def test_coleta_parcial_nao_remove_nada(conn, settings):
    """Queda de volume (arquivo truncado, por exemplo) deixa a execução parcial: ninguém é marcado como removido."""
    (conector,) = conectores("ceis", settings)
    completa, _ = _ceis_sem_a_primeira_linha()
    runner.executar(conn, conector, [completa], "online", settings.raw_dir)
    antes = _removidas(conn)
    so_manual = list(fixtures.ler(FIXTURES / "ceis" / "exemplo_manual"))
    resumo = runner.executar(conn, conector, so_manual, "online", settings.raw_dir)
    assert resumo.status == "parcial"
    assert _removidas(conn) == antes
