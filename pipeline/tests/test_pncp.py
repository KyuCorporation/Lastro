"""T06: conector PNCP. Fixture real recortada (`amostra/`) + caso sintético de pessoa física (`exemplo_manual/`)."""

import json
from datetime import date
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from lastro_pipeline import fixtures
from lastro_pipeline.connectors.pncp import ConectorPncp, janelas_mensais
from lastro_pipeline.http import ClienteHttp
from lastro_pipeline.modelos import Contrato, Descarte, RegistroNormalizado
from tests.conftest import FIXTURES

CAMPOS_USADOS = {
    "numeroControlePNCP",
    "niFornecedor",
    "tipoPessoa",
    "nomeRazaoSocialFornecedor",
    "objetoContrato",
    "valorGlobal",
    "dataAssinatura",
    "dataVigenciaInicio",
    "dataVigenciaFim",
    "anoContrato",
    "sequencialContrato",
    "orgaoEntidade",
    "unidadeOrgao",
}


def _processar(settings):
    conector = ConectorPncp(settings)
    saidas = []
    for resposta in fixtures.ler_fonte(FIXTURES / "pncp"):
        for registro in conector.interpretar(resposta):
            saidas.append(conector.normalizar(registro, resposta))
    return saidas


def test_contrato_da_rota_na_fixture_real():
    corpo = json.loads((FIXTURES / "pncp" / "amostra" / "contratos_amostra.json").read_bytes())
    assert {"data", "totalPaginas", "paginasRestantes"} <= corpo.keys()
    for registro in corpo["data"]:
        assert CAMPOS_USADOS <= registro.keys()
        assert {"cnpj", "esferaId"} <= registro["orgaoEntidade"].keys()
        assert {"ufSigla", "codigoUnidade", "nomeUnidade"} <= registro["unidadeOrgao"].keys()


def test_nenhuma_linha_de_pe_sem_fallback(settings):
    corpo = json.loads((FIXTURES / "pncp" / "amostra" / "contratos_amostra.json").read_bytes())
    assert any(r["unidadeOrgao"]["ufSigla"] == "PE" for r in corpo["data"]), "fixture precisa ter PE"
    contratos = [s.fato for s in _processar(settings) if isinstance(s, RegistroNormalizado)]
    assert contratos
    assert {c.uf for c in contratos} == {"AL"}


def test_pe_entra_com_fallback_ligado(settings):
    settings.pncp_pe_fallback = True
    ufs = {s.fato.uf for s in _processar(settings) if isinstance(s, RegistroNormalizado)}
    assert ufs == {"AL", "PE"}


def test_pe_listado_em_pncp_ufs_continua_fora_sem_fallback(settings):
    settings.pncp_ufs = "AL,PE"
    assert settings.ufs_pncp == ["AL"]


def test_pessoa_fisica_descartada(settings):
    descartes = [s for s in _processar(settings) if isinstance(s, Descarte)]
    assert [d.motivo for d in descartes] == ["pessoa_fisica"]


def test_mapeamento_com_proveniencia(settings):
    contrato: Contrato = next(s.fato for s in _processar(settings) if isinstance(s, RegistroNormalizado))
    assert contrato.fonte_id == "pncp"
    assert contrato.url_origem.startswith("https://pncp.gov.br/app/contratos/")
    assert contrato.orgao_id.startswith("pncp:")
    assert len(contrato.fornecedor_cnpj) == 14


def test_janelas_mensais():
    janelas = list(janelas_mensais(date(2025, 1, 15), date(2025, 3, 10)))
    assert janelas == [
        (date(2025, 1, 15), date(2025, 1, 31)),
        (date(2025, 2, 1), date(2025, 2, 28)),
        (date(2025, 3, 1), date(2025, 3, 10)),
    ]


def test_coleta_pagina_ate_acabar_e_trata_204(settings, cliente_falso):
    settings.pncp_data_inicial, settings.pncp_data_final = "20260901", "20261031"
    pedidos = []

    def rotas(req: httpx.Request) -> httpx.Response:
        q = parse_qs(urlparse(str(req.url)).query)
        pedidos.append((q["dataInicial"][0], q["pagina"][0]))
        if q["dataInicial"][0] == "20261001":
            return httpx.Response(204)
        pagina = int(q["pagina"][0])
        return httpx.Response(200, json={"data": [], "paginasRestantes": 2 - pagina})

    with cliente_falso(rotas) as cliente:
        respostas = list(ConectorPncp(settings).coletar(cliente))
    assert pedidos == [("20260901", "1"), ("20260901", "2"), ("20261001", "1")]
    assert len(respostas) == 2


def test_amostra_remove_campos_que_podem_identificar_pessoa(settings, cliente_falso):
    registro = json.loads((FIXTURES / "pncp" / "amostra" / "contratos_amostra.json").read_bytes())["data"][0]
    registro = {
        **registro,
        "nomeFornecedorSubContratado": "FULANO",
        "niFornecedorSubContratado": "12345678909",
    }
    with cliente_falso(lambda _r: httpx.Response(200, json={"data": [registro], "paginasRestantes": 0})) as c:
        amostra = ConectorPncp(settings).amostra(c, 5)
    gravado = json.loads(amostra[0].conteudo)["data"][0]
    assert "nomeFornecedorSubContratado" not in gravado
    assert "niFornecedorSubContratado" not in gravado


@pytest.mark.rede
def test_contrato_da_api_real(settings):
    settings.pncp_data_inicial = settings.pncp_data_final = "20261001"
    settings.pncp_tamanho_pagina = 10
    with ClienteHttp("pncp", None) as cliente:
        primeira = next(ConectorPncp(settings).coletar(cliente))
    corpo = json.loads(primeira.conteudo)
    assert CAMPOS_USADOS <= corpo["data"][0].keys()
