"""T05: conector TCE-PE. Só fixture; a API real só é chamada no teste `rede`, por humano em rede brasileira."""

import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from lastro_pipeline import fixtures
from lastro_pipeline.connectors.pe_portal import ConectorPePortal
from lastro_pipeline.http import ClienteHttp
from lastro_pipeline.modelos import Contrato, Descarte, Pagamento, RegistroNormalizado
from tests.conftest import FIXTURES


def _normalizar_fixture(settings):
    conector = ConectorPePortal(settings)
    saidas = []
    for resposta in fixtures.ler_fonte(FIXTURES / "pe_portal"):
        for registro in conector.interpretar(resposta):
            saidas.append(conector.normalizar(registro, resposta))
    return saidas


def test_fixture_cobre_contratos_estaduais_municipais_empenho_e_liquidacao(settings):
    saidas = _normalizar_fixture(settings)
    validos = [s for s in saidas if isinstance(s, RegistroNormalizado)]
    contratos = [s for s in validos if isinstance(s.fato, Contrato)]
    pagamentos = [s for s in validos if isinstance(s.fato, Pagamento)]
    assert {c.orgao.esfera for c in contratos} == {"estadual", "municipal"}
    assert {p.fato.id_origem.split(":")[0] for p in pagamentos} == {"emp", "liq"}
    assert all(s.fato.uf == "PE" for s in validos)
    assert all(s.fato.fonte_id == "pe_portal" for s in validos)
    assert all(s.fato.url_origem and s.fato.url_origem.startswith("https://") for s in validos)


def test_credor_pessoa_fisica_e_descartado(settings):
    saidas = _normalizar_fixture(settings)
    descartes = [s for s in saidas if isinstance(s, Descarte)]
    assert [d.motivo for d in descartes] == ["pessoa_fisica", "pessoa_fisica"]
    cnpjs = {s.fornecedor.cnpj for s in saidas if isinstance(s, RegistroNormalizado)}
    assert all(len(c) == 14 for c in cnpjs)


def test_mapeamento_de_um_contrato(settings):
    contrato = next(
        s.fato
        for s in _normalizar_fixture(settings)
        if isinstance(s, RegistroNormalizado) and s.fato.id_origem == "ctr:510101:2025:001/2025"
    )
    assert contrato.fornecedor_cnpj == "99000001000101"
    assert str(contrato.valor_global) == "1250000.00"
    assert contrato.vigencia_fim.isoformat() == "2027-01-14"
    assert contrato.orgao_id == "pe_portal:510101"


def test_liquidacoes_do_mesmo_empenho_tem_ids_distintos(settings):
    ids = [
        s.fato.id_origem
        for s in _normalizar_fixture(settings)
        if isinstance(s, RegistroNormalizado) and s.fato.id_origem.startswith("liq:")
    ]
    assert len(ids) == len(set(ids)) == 2


def test_coleta_percorre_recortes_e_paginas(settings, cliente_falso):
    pedidos = []

    def rotas(req: httpx.Request) -> httpx.Response:
        params = parse_qs(urlparse(str(req.url)).query)
        pedidos.append((req.url.path.rsplit("/", 1)[-1], params.get("Esfera"), params.get("pagina")))
        pagina = int(params.get("pagina", ["1"])[0])
        corpo = {"resposta": {"conteudo": [{"pagina": pagina}], "totalPaginas": 2}}
        return httpx.Response(200, json=corpo)

    with cliente_falso(rotas) as cliente:
        respostas = list(ConectorPePortal(settings).coletar(cliente))
    # 3 conjuntos × 1 ano × 2 esferas × 2 páginas
    assert len(respostas) == 12
    assert ("Contratos!json", ["E"], ["2"]) in pedidos
    assert {r.metadados["tipo"] for r in respostas} == {"contrato", "empenho", "liquidacao"}


def test_amostra_nunca_leva_cpf(settings, cliente_falso):
    registros = [
        {"CpfCnpj": "99000001000101", "NumeroContrato": "1"},
        {"CpfCnpj": "123.456.789-09", "NumeroContrato": "2"},
    ]
    with cliente_falso(lambda _r: httpx.Response(200, json=registros)) as cliente:
        amostra = ConectorPePortal(settings).amostra(cliente, 10)
    gravados = [r for a in amostra for r in json.loads(a.conteudo)]
    assert gravados and all(r["CpfCnpj"] == "99000001000101" for r in gravados)


@pytest.mark.rede
def test_contrato_da_api_real(settings):
    """Só em rede brasileira, rodado por humano: `pytest -m rede tests/test_pe_portal.py`."""
    conector = ConectorPePortal(settings)
    with ClienteHttp("pe_portal", None) as cliente:
        primeira = next(conector.coletar(cliente))
    registros = list(conector.interpretar(primeira))
    assert registros, "envelope da resposta diferente do esperado: ajuste ENVELOPES"
    normalizados = [conector.normalizar(r, primeira) for r in registros[:50]]
    assert any(isinstance(n, RegistroNormalizado) for n in normalizados), (
        "ajuste CAMPOS_* em normalize/pe_portal.py"
    )
