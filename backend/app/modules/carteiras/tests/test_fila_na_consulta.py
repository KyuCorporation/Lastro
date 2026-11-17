"""I5: a pergunta sobre a fila, feita com a carteira como contexto, responde pelo catálogo (`fila_carteira`).

Mesmos dados da T18 (conftest): para ana (PE), F1 tem sanção vigente (forte) e concentração em PE (atenção);
F2 não tem fato; o penhasco de F3 é de AL e não aparece.
"""

from uuid import uuid4

import pytest

from app.llm.regras import PERGUNTA_CARTEIRA
from app.modules.carteiras.tests.conftest import F1, F2, F3
from app.modules.consulta.tests.conftest import ProvedorFalso
from app.modules.recibos.tests.esquema import erros

PERGUNTA = "Quem eu devo olhar primeiro na fila desta carteira?"
TEXTO_ANA = (
    "A carteira tem 3 fornecedores: 1 com sinal para investigar (1 com sinal forte). "
    "Nas fontes autorizadas para você (PE), os contratos vigentes deles somam R$ 400.000,00. "
    "O primeiro da fila é o fornecedor 11.222.333/0001-81, com concentração em um órgão, sanção vigente: "
    "sinal para investigar."
)


@pytest.fixture
def carteira_id(cliente, autenticar) -> str:
    corpo = {"nome": f"T18 {uuid4().hex[:8]}", "finalidade": "monitoramento", "cnpjs": [F1, F2, F3]}
    r = cliente.post("/carteiras", json=corpo, headers=autenticar("ana@alfa.demo"))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _perguntar(api, headers, pergunta=PERGUNTA, carteira_id=None):
    corpo = {"pergunta": pergunta, **({"carteira_id": carteira_id} if carteira_id else {})}
    return api.post("/consultas", json=corpo, headers=headers)


def test_fila_pela_consulta_com_texto_citacoes_e_recibo(cliente, autenticar, carteira_id):
    ana = autenticar("ana@alfa.demo")
    r = _perguntar(cliente, ana, carteira_id=carteira_id)
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["status"] == "respondida"
    assert corpo["resposta"] == TEXTO_ANA

    citadas = {(c["tabela"], c["id_origem"]) for c in corpo["citacoes"]}
    assert citadas == {("contratos", "TCAT-C1"), ("contratos", "TCAT-C2"), ("sancoes", "TCAT-S1")}

    recibo = cliente.get(f"/recibos/{corpo['recibo_id']}", headers=ana).json()["conteudo"]
    assert erros(recibo) == []
    assert recibo["execucao"]["consulta_catalogo"] == "fila_carteira@v1"
    assert recibo["execucao"]["parametros_efetivos"]["carteira_id"] == carteira_id
    assert recibo["carteira"] == {"id": carteira_id, "finalidade": "monitoramento"}


def test_primeiro_da_fila_e_o_mesmo_da_tela(cliente, autenticar, carteira_id):
    ana = autenticar("ana@alfa.demo")
    tela = cliente.get(f"/carteiras/{carteira_id}/fila", headers=ana).json()["itens"]
    assert tela[0]["cnpj"] == F1
    assert "11.222.333/0001-81" in _perguntar(cliente, ana, carteira_id=carteira_id).json()["resposta"]


def test_admin_ve_o_penhasco_de_al(cliente, autenticar, carteira_id):
    corpo = _perguntar(cliente, autenticar("admin@alfa.demo"), carteira_id=carteira_id).json()
    assert corpo["resposta"].startswith("A carteira tem 3 fornecedores: 2 com sinal para investigar")
    assert "R$ 475.000,00" in corpo["resposta"]  # F1 em PE e AL (470 mil) + F3 em AL (5 mil)


def test_sem_carteira_no_contexto_pede_a_carteira(cliente, autenticar):
    corpo = _perguntar(cliente, autenticar("ana@alfa.demo")).json()
    assert corpo["status"] == "esclarecimento" and corpo["resposta"] == PERGUNTA_CARTEIRA


def test_carteira_de_outro_tenant_para_antes_da_fila(cliente, autenticar, carteira_id):
    r = _perguntar(cliente, autenticar("bia@beta.demo"), carteira_id=carteira_id)
    assert r.status_code == 404 and F1 not in r.text


def test_plano_da_llm_sem_carteira_usa_a_do_contexto(cliente, autenticar, com_ambiente, carteira_id):
    alheia = str(uuid4())  # a LLM não escolhe a carteira: a do contexto vale
    plano = {"versao": "v1", "intent": "fila_carteira", "parametros": {"carteira_id": alheia}}
    com_ambiente(provedor=ProvedorFalso(plano=plano))
    corpo = _perguntar(cliente, autenticar("ana@alfa.demo"), carteira_id=carteira_id).json()
    assert corpo["status"] == "respondida"
    assert corpo["resposta"] == TEXTO_ANA  # redator falso devolve vazio: cai no texto pronto
