"""T05: conector TCE-PE. Só fixture e HTTP simulado; a API real só é chamada no teste `rede` (rede brasileira)."""

import json
from datetime import date
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from lastro_pipeline import fixtures
from lastro_pipeline.connectors.pe_portal import ConectorPePortal, RecorteTruncado
from lastro_pipeline.http import ClienteHttp
from lastro_pipeline.modelos import Contrato, Descarte, Pagamento, RegistroNormalizado, RespostaBruta
from lastro_pipeline.normalize import pe_portal as mapa
from tests.conftest import FIXTURES

HOJE = date(2025, 3, 20)
CPF = "12345678909"  # fictício
PJ = "99000001000101"
MANUAL = FIXTURES / "pe_portal" / "exemplo_manual"


def _normalizar(settings, respostas):
    conector = ConectorPePortal(settings)
    return [conector.normalizar(reg, r) for r in respostas for reg in conector.interpretar(r)]


def _resposta(tipo: str, registros: list[dict], esfera: str = "E") -> RespostaBruta:
    conteudo = json.dumps({"resposta": {"status": "OK", "conteudo": registros}}).encode()
    return RespostaBruta(conteudo, "https://tce.test/x", "x.json", HOJE, {"tipo": tipo, "esfera": esfera})  # type: ignore[arg-type]


def _corpo(registros: list[dict], **meta: str) -> bytes:
    """Como a API responde: ISO-8859-1, envelope `resposta`, contagem e limite."""
    envelope = {"status": "OK", "tamanhoResultado": str(len(registros)), "limiteResultado": "100000", **meta}
    return json.dumps({"resposta": {**envelope, "conteudo": registros}}, ensure_ascii=False).encode("latin-1")


# ------------------------------------------------------------------ normalização (fixture)
def test_fixture_cobre_contratos_estaduais_municipais_empenho_e_liquidacao(settings):
    saidas = _normalizar(settings, fixtures.ler_fonte(FIXTURES / "pe_portal"))
    validos = [s for s in saidas if isinstance(s, RegistroNormalizado)]
    contratos = [s for s in validos if isinstance(s.fato, Contrato)]
    pagamentos = [s for s in validos if isinstance(s.fato, Pagamento)]
    assert {c.orgao.esfera for c in contratos} == {"estadual", "municipal"}
    assert {p.fato.id_origem.split(":")[0] for p in pagamentos} == {"emp", "liq"}
    assert all(s.fato.uf == "PE" for s in validos)
    assert all(s.fato.fonte_id == "pe_portal" for s in validos)
    # Contrato com `LinkArquivo` aponta para a página do documento no tribunal (só http); o resto, para a API.
    assert all(
        s.fato.url_origem and s.fato.url_origem.startswith(("https://", "http://sistemas.tcepe.tc.br/"))
        for s in validos
    )


def test_pessoa_fisica_e_descartada_crua_ou_ja_saneada(settings):
    saidas = _normalizar(settings, fixtures.ler(MANUAL))
    descartes = [s for s in saidas if isinstance(s, Descarte)]
    assert [d.motivo for d in descartes] == ["pessoa_fisica", "pessoa_fisica"]
    cnpjs = {s.fornecedor.cnpj for s in saidas if isinstance(s, RegistroNormalizado) and s.fornecedor}
    assert cnpjs == {PJ, "99000002000148"}


def test_mapeamento_de_um_contrato(settings):
    contrato = next(
        s.fato
        for s in _normalizar(settings, fixtures.ler(MANUAL))
        if isinstance(s, RegistroNormalizado) and s.fato.id_origem == "ctr:90000001"
    )
    assert contrato.fornecedor_cnpj == PJ
    assert str(contrato.valor_global) == "1250000.00"
    assert contrato.vigencia_inicio.isoformat() == "2025-01-15"
    assert contrato.vigencia_fim.isoformat() == "2027-01-14"
    assert contrato.orgao_id == "pe_portal:510101"  # estado: código e-Fisco, o mesmo das despesas
    assert contrato.data_assinatura is None  # a API não informa
    assert contrato.situacao == "Regular"  # `Situacao` da fonte, sem tradução (migration 009)
    assert (
        contrato.url_origem
        == "http://sistemas.tcepe.tc.br/audinArquivos/licon/remessaTCEPE/remessaTCEPE.html?tipoFonteDocumento=IJ&idDocumento=90000001"
    )  # LinkArquivo: a página do contrato no TCE-PE


def _contrato_manual(**troca: str) -> dict:
    registro = json.loads((MANUAL / "contrato_2025_E.json").read_text(encoding="utf-8"))["resposta"][
        "conteudo"
    ][0]
    return {**registro, **troca}


@pytest.mark.parametrize(
    "link",
    [
        "",
        "https://malicioso.exemplo/contrato",
        "javascript:alert(1)",
        "http://sistemas.tcepe.tc.br.malicioso.exemplo/x",
    ],
    ids=["vazio", "outro_host", "javascript", "host_parecido"],
)
def test_contrato_sem_link_valido_do_tce_aponta_para_o_recorte_da_api(settings, link):
    (saida,) = _normalizar(settings, [_resposta("contrato", [_contrato_manual(LinkArquivo=link)])])
    assert saida.fato.url_origem == "https://tce.test/x"


def test_amostra_guarda_o_link_do_contrato():
    assert "LinkArquivo" in mapa.CAMPOS_AMOSTRA["contrato"]


def test_amostra_guarda_a_situacao_do_contrato():
    assert "Situacao" in mapa.CAMPOS_AMOSTRA["contrato"]


def test_contrato_sem_situacao_fica_nulo(settings):
    registro = {k: v for k, v in _contrato_manual().items() if k != "Situacao"}
    (saida,) = _normalizar(settings, [_resposta("contrato", [registro])])
    assert saida.fato.situacao is None


def test_liquidacao_herda_o_credor_do_empenho(settings):
    saidas = _normalizar(settings, fixtures.ler(MANUAL))
    pagamentos = {s.fato.id_origem: s.fato for s in saidas if isinstance(s, RegistroNormalizado)}
    empenho = pagamentos["emp:1146:2025:9000310"]
    liquidacoes = [f for i, f in pagamentos.items() if i.startswith("liq:1146:2025:9000310:")]
    assert str(empenho.valor) == "40000.00" and empenho.data_pagamento.isoformat() == "2025-04-05"
    assert empenho.descricao == "empenho: Transporte escolar, abril"
    assert [str(f.valor) for f in liquidacoes] == ["20000.00", "20000.00"]
    assert {f.fornecedor_cnpj for f in liquidacoes} == {empenho.fornecedor_cnpj}
    assert {f.orgao_id for f in liquidacoes} == {"pe_portal:1146"}
    assert liquidacoes[0].descricao == "liquidação do empenho 0000310"


def test_liquidacao_sem_empenho_de_pj_fica_fora_e_anulacao_entra_negativa(settings):
    base = {"ID_UNIDADE_GESTORA": "220201", "ANOREFERENCIA": "2025", "ESFERA": "E"}
    empenho = {**base, "NUMEROEMPENHO": "2025NE000001", "CPF_CNPJ": PJ, "VALOREMPENHADO": "100.00"}
    liquidacao = {**base, "IDEMPENHO": "2025NE000001", "NUMEROEMPENHO": "2025NE000001", "DATA": "2025-02-20"}
    saidas = _normalizar(
        settings,
        [
            _resposta("empenho", [empenho, {mapa.OMITIDO: "pessoa_fisica"}]),
            _resposta(
                "liquidacao",
                [
                    {**liquidacao, "NUMERO": "2025LE000001", "TIPO": "Liquidação", "VALOR": "100.00"},
                    {
                        **liquidacao,
                        "NUMERO": "2025AL000005",
                        "TIPO": "Liquidação - anulação",
                        "VALOR": "-55.00",
                    },
                    {**liquidacao, "IDEMPENHO": "2025NE000999", "NUMERO": "2025LE000002", "VALOR": "9.00"},
                ],
            ),
        ],
    )
    assert [type(s).__name__ for s in saidas] == ["RegistroNormalizado", "Descarte"] + [
        "RegistroNormalizado",
        "RegistroNormalizado",
        "Descarte",
    ]
    anulacao = saidas[3].fato
    assert str(anulacao.valor) == "-55.00" and anulacao.descricao.startswith("anulação de liquidação")
    assert anulacao.id_origem == "liq:220201:2025:2025NE000001:2025AL000005"
    assert saidas[4].motivo == "fora_do_escopo"


def test_ug_estadual_tem_o_mesmo_id_no_contrato_e_na_despesa(settings):
    """A API manda o e-Fisco com zero à esquerda nos contratos e sem ele nas despesas e liquidações."""
    despesa = {"ID_UNIDADE_GESTORA": "10001", "ANOREFERENCIA": "2026", "ESFERA": "E"}
    contrato, empenho, liquidacao = _normalizar(
        settings,
        [
            _resposta("contrato", [{"CodigoContrato": "7", "CodigoEfiscoUG": "010001", "CPF_CNPJ": PJ}]),
            _resposta("empenho", [{**despesa, "NUMEROEMPENHO": "2026NE000008", "CPF_CNPJ": PJ}]),
            _resposta("liquidacao", [{**despesa, "IDEMPENHO": "2026NE000008", "NUMERO": "2026LE000001"}]),
        ],
    )
    assert contrato.fato.orgao_id == empenho.fato.orgao_id == liquidacao.fato.orgao_id == "pe_portal:010001"
    assert empenho.fato.id_origem == "emp:010001:2026:2026NE000008"


# ------------------------------------------------------------------ saneamento (LGPD)
REGISTRO_PF = {
    "CodigoContrato": "1",
    "TipoDocumento": "CPF",
    "CPF_CNPJ": "***.***.789-09",
    "NumeroDocumento": CPF,
    "NumeroDocumentoAjustado": f"{CPF}                   ",
    "RazaoSocial": "Fulana de Tal Sintética",
    "Objeto": "LOCAÇÃO DE IMÓVEIS",
}
REGISTRO_PJ = {
    "CodigoContrato": "2",
    "TipoDocumento": "CNPJ",
    "CPF_CNPJ": f"{PJ}    ",
    "RazaoSocial": f"FULANO SINTETICO {CPF}",  # MEI: a razão social traz o CPF do titular
    "Objeto": "Serviço prestado por 123.456.789-09 conforme edital   ",
    "Valor": "10.00",
}


def test_saneamento_tira_pessoa_fisica_e_mascara_cpf_em_registro_de_pj():
    saneado = mapa.sanear(_corpo([REGISTRO_PF, REGISTRO_PJ, {"CPF_CNPJ": "123456"}]), "contrato")
    texto = saneado.decode("utf-8")
    assert CPF not in texto and "789-09" not in texto and "Fulana" not in texto
    resposta = json.loads(texto)["resposta"]
    assert resposta["conteudo"][0] == {mapa.OMITIDO: "pessoa_fisica"}
    assert resposta["conteudo"][2] == {mapa.OMITIDO: "documento_invalido"}
    assert resposta["conteudo"][1]["CPF_CNPJ"] == PJ  # espaços de preenchimento saem
    assert resposta["conteudo"][1]["RazaoSocial"] == "FULANO SINTETICO ***"
    assert resposta["saneamento_lgpd"] == {
        "registros_omitidos": {"pessoa_fisica": 1, "documento_invalido": 1}
    }
    assert resposta["tamanhoResultado"] == "3"  # a contagem da fonte fica


def test_cpf_nunca_e_gravado_em_cache_nem_no_que_vai_para_o_bronze(settings, cliente_falso, tmp_path):
    """A resposta chega em ISO-8859-1 com CPF inteiro; em disco e no bronze só existe a versão saneada."""

    def rotas(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("Contratos!json"):
            return httpx.Response(200, content=_corpo([REGISTRO_PF, REGISTRO_PJ]))
        return httpx.Response(200, content=_corpo([]))

    conector = ConectorPePortal(settings.model_copy(update={"tcepe_ugs_estaduais": "220201"}), hoje=HOJE)
    with cliente_falso(rotas, tmp_path) as cliente:
        respostas = list(conector.coletar(cliente))

    em_disco = [p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()]
    assert em_disco and respostas
    for conteudo in em_disco + [r.conteudo for r in respostas]:
        assert CPF.encode() not in conteudo and b"789-09" not in conteudo and b"Fulana" not in conteudo
    saidas = [conector.normalizar(reg, r) for r in respostas for reg in conector.interpretar(r)]
    assert [getattr(s, "motivo", "ok") for s in saidas] == ["pessoa_fisica", "ok"] * len(respostas)
    assert "LOCAÇÃO" not in respostas[0].conteudo.decode("utf-8")  # do registro de PF não sobra nada


# ------------------------------------------------------------------ coleta
def _api_falsa(pedidos: list[tuple[str, dict[str, str]]]):
    def rotas(req: httpx.Request) -> httpx.Response:
        metodo = req.url.path.rsplit("/", 1)[-1]
        params = {k: v[0] for k, v in parse_qs(urlparse(str(req.url)).query).items()}
        pedidos.append((metodo, params))
        if metodo == "UnidadesJurisdicionadasEstaduais!json":
            return httpx.Response(
                200, content=_corpo([{"ID_UNIDADEGESTORA": u} for u in ("110001", "220201")])
            )
        if metodo == "Municipios!json":
            municipios = [
                {"MUNICIPIO": "Garanhuns", "CODIGO": "P062", "UNIDADEFEDERATIVA": "PE"},
                {"MUNICIPIO": "Garanhuns", "CODIGO": "X999", "UNIDADEFEDERATIVA": "ZZ"},
            ]
            return httpx.Response(200, content=_corpo(municipios))
        if metodo == "Contratos!json":
            return httpx.Response(200, content=_corpo([{"CodigoContrato": "1", "CPF_CNPJ": PJ}]))
        if metodo == "DespesasEstaduais!json":
            com_pj = params["ID_UNIDADE_GESTORA"] == "220201"
            credor = {"CPF_CNPJ": PJ} if com_pj else {"CPF_CNPJ": "***.***.789-09"}
            return httpx.Response(200, content=_corpo([{**params, "NUMEROEMPENHO": "NE1", **credor}]))
        if metodo == "DespesasMunicipais!json":
            ug = "247" if params["MESREFERENCIA"] == "1" else "250"
            registro = {"ID_UNIDADE_GESTORA": ug, "ANOREFERENCIA": "2025", "ID_EMPENHO": "9", "CPF_CNPJ": PJ}
            return httpx.Response(200, content=_corpo([registro]))
        return httpx.Response(200, content=_corpo([{**params, "IDEMPENHO": "NE1", "NUMERO": "L1"}]))

    return rotas


def test_coleta_fatia_por_ano_unidade_gestora_e_mes(settings, cliente_falso):
    pedidos: list[tuple[str, dict[str, str]]] = []
    ajustes = {"tcepe_contratos_ano_inicial": 2023, "tcepe_municipios": "garanhuns"}
    conector = ConectorPePortal(settings.model_copy(update=ajustes), hoje=HOJE)
    with cliente_falso(_api_falsa(pedidos)) as cliente:
        respostas = list(conector.coletar(cliente))

    def de(metodo: str) -> list[dict[str, str]]:
        return [p for m, p in pedidos if m == metodo]

    # Contratos antigos entram: um recorte por ano do contrato e esfera, com o filtro que a API respeita.
    assert sorted((p["AnoContrato"], p["Esfera"]) for p in de("Contratos!json")) == [
        (ano, esfera) for ano in ("2023", "2024", "2025") for esfera in ("E", "M")
    ]
    assert all("AnoReferencia" not in p for p in de("Contratos!json"))
    # Estado: despesas por UG; liquidação só da UG que teve empenho de PJ.
    assert [p["ID_UNIDADE_GESTORA"] for p in de("DespesasEstaduais!json")] == ["110001", "220201"]
    liquidacoes = de("EmpenhoLiquidacao!json")
    assert [p["ID_UNIDADE_GESTORA"] for p in liquidacoes if p["ESFERA"] == "E"] == ["220201"]
    # Município: do nome ao código do TCE; um recorte por mês até o mês corrente; liquidação por UG vista.
    municipais = de("DespesasMunicipais!json")
    assert {p["CODIGO_MUNICIPIO"] for p in municipais} == {"P062"}
    assert [p["MESREFERENCIA"] for p in municipais] == ["1", "2", "3"]
    assert [p["ID_UNIDADE_GESTORA"] for p in liquidacoes if p["ESFERA"] == "M"] == ["247", "250"]
    # Despesa vem antes da liquidação dela, e o bronze distingue os recortes pelo nome.
    nomes = [r.nome for r in respostas]
    assert nomes.index("empenho_2025_E_ug220201.json") < nomes.index("liquidacao_2025_E_ug220201.json")
    assert len(nomes) == len(set(nomes))
    assert {r.metadados["tipo"] for r in respostas} == {"contrato", "empenho", "liquidacao"}


def test_exercicio_encerrado_fica_em_cache_e_o_corrente_e_refeito(settings, cliente_falso, tmp_path):
    pedidos: list[tuple[str, dict[str, str]]] = []
    ajustes = {"tcepe_contratos_ano_inicial": 2024, "tcepe_esferas": "E", "tcepe_ugs_estaduais": "220201"}
    conector = ConectorPePortal(settings.model_copy(update=ajustes), hoje=HOJE)
    with cliente_falso(_api_falsa(pedidos), tmp_path) as cliente:
        list(conector.coletar(cliente))
        for dia in (tmp_path / "teste").iterdir():  # como se a primeira coleta fosse de 5 dias atrás
            dia.rename(dia.with_name((date.today().fromordinal(date.today().toordinal() - 5)).isoformat()))
        pedidos.clear()
        list(conector.coletar(cliente))
    refeitos = [(m, p.get("AnoContrato") or p.get("ANOREFERENCIA")) for m, p in pedidos]
    assert ("Contratos!json", "2024") not in refeitos  # exercício encerrado: cache de TCEPE_CACHE_DIAS
    assert ("Contratos!json", "2025") in refeitos and ("DespesasEstaduais!json", "2025") in refeitos


def test_resposta_no_limite_da_api_falha_em_vez_de_gravar_dado_cortado(settings, cliente_falso):
    cheio = _corpo([{"CodigoContrato": "1", "CPF_CNPJ": PJ}], tamanhoResultado="100000")
    rotas = lambda _r: httpx.Response(200, content=cheio)
    with cliente_falso(rotas) as cliente, pytest.raises(RecorteTruncado, match="100000 registros"):
        list(ConectorPePortal(settings, hoje=HOJE).coletar(cliente))


def test_municipio_desconhecido_e_erro_claro(settings, cliente_falso):
    conector = ConectorPePortal(settings.model_copy(update={"tcepe_municipios": "Atlantida"}), hoje=HOJE)
    with cliente_falso(_api_falsa([])) as cliente, pytest.raises(ValueError, match="Atlantida"):
        list(conector.coletar(cliente))


def test_amostra_so_leva_pj_campos_usados_e_liquidacao_com_empenho(settings, cliente_falso):
    def rotas(req: httpx.Request) -> httpx.Response:
        metodo = req.url.path.rsplit("/", 1)[-1]
        if metodo == "Contratos!json":
            return httpx.Response(200, content=_corpo([REGISTRO_PF, REGISTRO_PJ]))
        base = {"ID_UNIDADE_GESTORA": "220201", "ANOREFERENCIA": "2025", "ESFERA": "E"}
        if metodo == "DespesasEstaduais!json":
            empenhos = [
                {**base, "NUMEROEMPENHO": "NE1", "CPF_CNPJ": PJ, "HISTORICO": "texto livre"},
                {**base, "NUMEROEMPENHO": "NE2", "CPF_CNPJ": "***.***.789-09", "NOME_FORNECEDOR": "Fulana"},
            ]
            return httpx.Response(200, content=_corpo(empenhos))
        liquidacoes = [
            {**base, "IDEMPENHO": "NE1", "NUMERO": "L1", "VALOR": "1.00"},
            {**base, "IDEMPENHO": "NE2", "NUMERO": "L2", "VALOR": "2.00"},  # empenho de PF: fica fora
        ]
        return httpx.Response(200, content=_corpo(liquidacoes))

    ajustes = {"tcepe_esferas": "E", "tcepe_ugs_estaduais": "220201"}
    conector = ConectorPePortal(settings.model_copy(update=ajustes), hoje=HOJE)
    with cliente_falso(rotas) as cliente:
        amostra = conector.amostra(cliente, 12)

    gravado = b"".join(a.conteudo for a in amostra).decode("utf-8")
    assert "789-09" not in gravado and "Fulana" not in gravado and "texto livre" not in gravado
    por_tipo = {a.metadados["tipo"]: json.loads(a.conteudo) for a in amostra}
    assert [r["CodigoContrato"] for r in por_tipo["contrato"]] == ["2"]
    assert [r["NUMEROEMPENHO"] for r in por_tipo["empenho"]] == ["NE1"]
    assert [r["NUMERO"] for r in por_tipo["liquidacao"]] == ["L1"]
    # A amostra, lida como fixture, normaliza sem descarte.
    saidas = _normalizar(settings, amostra)
    assert len(saidas) == 3 and all(isinstance(s, RegistroNormalizado) for s in saidas)


@pytest.mark.rede
def test_contrato_da_api_real(settings):
    """Só em rede brasileira: `pytest -m rede tests/test_pe_portal.py`. Uma requisição (contratos do ano, estado)."""
    conector = ConectorPePortal(settings.model_copy(update={"tcepe_esferas": "E"}))
    with ClienteHttp("pe_portal", None, timeout=180) as cliente:
        primeira = next(conector.coletar(cliente))
    assert b'NumeroDocumentoAjustado":"' in primeira.conteudo  # formato esperado dos contratos
    registros = list(conector.interpretar(primeira))
    assert registros, "envelope da resposta diferente do esperado: ajuste ENVELOPES"
    normalizados = [conector.normalizar(r, primeira) for r in registros]
    validos = [n for n in normalizados if isinstance(n, RegistroNormalizado)]
    assert validos, "ajuste CAMPOS_* em normalize/pe_portal.py"
    assert any(n.fato.vigencia_fim for n in validos), "formato de `Vigencia` mudou"
    assert all(mapa.OMITIDO in r or "*" not in str(r.get("CPF_CNPJ")) for r in registros)  # PF saneada
