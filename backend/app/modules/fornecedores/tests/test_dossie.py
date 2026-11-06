"""T18, passo 5 da demo: dossiê de uma página do fornecedor, cada item com fonte, sob RLS."""

import pytest

from app.core.db import sessao
from app.modules.carteiras.tests.conftest import F1, F2, F3


def _dossie(api, headers, cnpj):
    return api.get(f"/fornecedores/{cnpj}/dossie", headers=headers)


@pytest.fixture
def dossie_ana(cliente, autenticar) -> dict:
    r = _dossie(cliente, autenticar("ana@alfa.demo"), F1)
    assert r.status_code == 200, r.text
    return r.json()


def test_dossie_tem_todas_as_secoes_do_contrato(dossie_ana):
    assert set(dossie_ana) == {
        "fornecedor",
        "resumo_por_uf",
        "contratos_vigentes",
        "vencendo_180d",
        "sancoes",
        "sinais",
        "socios",
        "fontes",
    }
    assert dossie_ana["fornecedor"] == {
        "cnpj": F1,
        "razao_social": "FORNECEDOR TESTE UM LTDA",
        "uf_sede": "PE",
    }


def test_resumo_so_das_ufs_do_usuario_com_dinheiro_em_string(dossie_ana):
    (pe,) = dossie_ana["resumo_por_uf"]
    assert pe == {
        "uf": "PE",
        "n_contratos": 3,
        "valor_contratado": "450000.00",
        "valor_vigente": "400000.00",
        "n_pagamentos": 3,
        "valor_pago": "55000.00",
        "valor_empenhado": "0.00",
    }


def test_vigentes_e_vencendo_com_proveniencia(dossie_ana):
    vigentes = dossie_ana["contratos_vigentes"]
    assert [c["id_origem"] for c in vigentes] == ["TCAT-C1", "TCAT-C2"]  # C3 encerrado, C4 é de AL
    assert [c["id_origem"] for c in dossie_ana["vencendo_180d"]] == ["TCAT-C1"]
    for item in [*vigentes, *dossie_ana["sancoes"]]:
        assert item["fonte_id"] and item["url_origem"] and item["coletado_em"] and item["id"]
    assert vigentes[0]["valor_global"] == "100000.00" and vigentes[0]["orgao_nome"] == "Secretaria Teste PE 1"


def test_sancoes_vigentes_e_passadas(dossie_ana):
    assert {(s["id_origem"], s["vigente"]) for s in dossie_ana["sancoes"]} == {
        ("TCAT-S1", True),
        ("TCAT-S2", False),
    }


def test_sinais_sem_os_de_uf_fora_do_escopo(dossie_ana):
    assert {(s["tipo"], s["uf"]) for s in dossie_ana["sinais"]} == {
        ("sancao_direta", None),
        ("concentracao", "PE"),
    }
    assert dossie_ana["sinais"][0]["gravidade"] == "forte"  # forte primeiro


def test_socio_pf_so_mascarado(dossie_ana):
    (socio,) = dossie_ana["socios"]
    assert socio["socio_tipo"] == "PF" and socio["socio_exibicao"] == "J*** S*** (CPF ***.456.789-**)"
    assert "socio_chave" not in socio


def test_fontes_listadas_com_selo_sintetico(dossie_ana):
    fontes = {f["fonte_id"]: f for f in dossie_ana["fontes"]}
    assert {"demo_sintetico", "ceis", "cnep", "receita_qsa"} <= set(fontes)
    assert fontes["demo_sintetico"]["sintetico"] is True and fontes["ceis"]["sintetico"] is False


def test_gestor_ve_dossie_sem_socios(cliente, autenticar):
    r = _dossie(cliente, autenticar("gil@alfa.demo"), F1)
    assert r.status_code == 200
    assert r.json()["socios"] is None
    assert "receita_qsa" not in {f["fonte_id"] for f in r.json()["fontes"]}


def test_admin_ve_pe_e_al(cliente, autenticar):
    corpo = _dossie(cliente, autenticar("admin@alfa.demo"), F1).json()
    assert [r["uf"] for r in corpo["resumo_por_uf"]] == ["AL", "PE"]
    assert ("penhasco", "AL") in {(s["tipo"], s["uf"]) for s in corpo["sinais"]}


def test_bia_so_ve_al_do_mesmo_fornecedor(cliente, autenticar):
    corpo = _dossie(cliente, autenticar("bia@beta.demo"), F1).json()
    assert [r["uf"] for r in corpo["resumo_por_uf"]] == ["AL"]
    assert [c["id_origem"] for c in corpo["contratos_vigentes"]] == ["TCAT-C4"]
    assert all(s["uf"] in (None, "AL") for s in corpo["sinais"])


def test_cnpj_com_mascara_e_aceito(cliente, autenticar):
    assert _dossie(cliente, autenticar("ana@alfa.demo"), "11.222.333.0001-81").status_code == 200


@pytest.mark.parametrize("cnpj", ["11222333000180", "123", "abc", "1" * 14])
def test_cnpj_invalido_422(cliente, autenticar, cnpj):
    r = _dossie(cliente, autenticar("ana@alfa.demo"), cnpj)
    assert r.status_code == 422 and r.json()["erro"]["codigo"] == "ENTRADA_INVALIDA"


@pytest.mark.parametrize(
    "cnpj", [F2, F3], ids=["fornecedor_sem_nenhum_fato", "fornecedor_so_em_uf_fora_do_escopo"]
)
def test_sem_registro_visivel_e_404_sem_vazar_nada(cliente, autenticar, cnpj):
    """F3 só tem contrato e sinal em AL: para ana (PE) é igual a um CNPJ que não existe."""
    r = _dossie(cliente, autenticar("ana@alfa.demo"), cnpj)
    assert r.status_code == 404 and r.json()["erro"]["codigo"] == "NAO_ENCONTRADO"
    assert "SO EM AL" not in r.text and "5000" not in r.text


def test_abertura_do_dossie_fica_na_auditoria(cliente, autenticar, ctx_caio):
    _dossie(cliente, autenticar("ana@alfa.demo"), F3)
    with sessao(ctx_caio) as conn:
        evento = conn.execute(
            "select usuario_id::text, detalhes from auditoria where evento = 'dossie' order by seq desc limit 1"
        ).fetchone()
    assert evento == ("00000000-0000-0000-0000-0000000000a1", {"cnpj": F3, "encontrado": False})
