"""T19: texto pronto e marcadores de `orgaos_fornecedor` e `busca_objeto` (sem banco)."""

from datetime import date
from decimal import Decimal

from app.llm.marcadores import montar_material
from app.llm.redator import redigir
from app.llm.verificador import MARCADOR
from app.modules.catalogo.executor import ResultadoConsulta

HOJE = date(2026, 11, 6)
CNPJ = "11222333000181"


def contrato(id_origem: str, valor: str, objeto: str = "Limpeza predial") -> dict:
    return {
        "id": f"id-{id_origem}", "fonte_id": "pncp", "id_origem": id_origem, "url_origem": "https://pncp.gov.br/x",
        "coletado_em": date(2026, 11, 5), "hash_conteudo": "a" * 64, "arquivo_bruto_id": None, "uf": "PE",
        "orgao_id": "pncp:1", "orgao_nome": "Secretaria de Educação", "objeto": objeto,
        "valor_global": Decimal(valor), "fornecedor_cnpj": CNPJ, "razao_social": "EMPRESA TESTE",
    }  # fmt: skip


def orgaos(participacao: str = "80.00") -> ResultadoConsulta:
    ranking = [
        {"uf": "PE", "orgao_id": "pncp:1", "orgao_nome": "Secretaria de Educação", "esfera": "estadual",
         "n_contratos": 2, "valor_contratado": Decimal("800000.00"), "participacao": Decimal(participacao)},
        {"uf": "PE", "orgao_id": "pncp:2", "orgao_nome": "Prefeitura do Recife", "esfera": "municipal",
         "n_contratos": 1, "valor_contratado": Decimal("200000.00"), "participacao": Decimal("20.00")},
    ]  # fmt: skip
    return ResultadoConsulta(
        intent="orgaos_fornecedor",
        versao="orgaos_fornecedor@v1",
        parametros={"cnpj": CNPJ, "hoje": HOJE, "ufs": ["PE"]},
        conjuntos={
            "ranking": ranking,
            "contratos": [contrato("C1", "500000.00"), contrato("C2", "300000.00")],
        },
        totais={
            "n_orgaos": 2,
            "n_contratos": 3,
            "valor_total": Decimal("1000000.00"),
            "maior_orgao": "Secretaria de Educação",
            "maior_participacao": Decimal(participacao),
        },
    )


def busca(linhas: list[dict], total: int | None = None) -> ResultadoConsulta:
    return ResultadoConsulta(
        intent="busca_objeto",
        versao="busca_objeto@v1",
        parametros={"termo": "merenda escolar", "hoje": HOJE, "ufs": ["PE"]},
        conjuntos={"linhas": linhas},
        totais={
            "n_contratos": len(linhas) if total is None else total,
            "valor_total": sum((c["valor_global"] for c in linhas), Decimal(0)),
        },
    )


def test_orgaos_texto_pronto_com_sinal_de_concentracao():
    r = redigir("Quais órgãos contratam?", orgaos(), ufs_autorizadas=("PE",), provedor=None)
    assert r.status == "aprovado"
    assert r.texto == (
        "Nas fontes autorizadas para você (PE), o fornecedor 11.222.333/0001-81 tem contratos com 2 órgãos, "
        "somando R$ 1.000.000,00. O maior é Secretaria de Educação, com 80,00% do valor. "
        "Concentração em um só órgão é um sinal para investigar."
    )


def test_orgaos_sem_concentracao_nao_fala_em_sinal():
    r = redigir("Quais órgãos contratam?", orgaos("55.00"), ufs_autorizadas=("PE",), provedor=None)
    assert "sinal para investigar" not in r.texto
    assert "55,00%" in r.texto


def test_busca_texto_pronto():
    linhas = [contrato("C1", "300000.00", "Fornecimento de merenda escolar")]
    r = redigir("contratos de merenda escolar", busca(linhas), ufs_autorizadas=("PE",), provedor=None)
    assert r.texto == (
        "Encontrei 1 contrato com objeto relacionado a merenda escolar nas fontes autorizadas para você (PE), "
        "somando R$ 300.000,00."
    )


def test_busca_com_mais_resultados_que_o_limite_avisa_que_cita_os_mais_relevantes():
    linhas = [contrato(f"C{i}", "1000.00") for i in range(20)]
    r = redigir("contratos de limpeza", busca(linhas, total=35), ufs_autorizadas=("PE",), provedor=None)
    assert r.texto.startswith("Encontrei 35 contratos")
    assert r.texto.endswith("Os mais relevantes estão citados abaixo.")


def test_busca_vazia_e_abstencao():
    r = redigir("contratos de helicóptero", busca([]), ufs_autorizadas=("PE",), provedor=None)
    assert r.status == "abstencao"
    assert r.texto.startswith("Não encontrei contratos com objeto relacionado a merenda escolar")


def test_todo_marcador_dos_modelos_existe():
    for resultado in (orgaos(), busca([contrato("C1", "10.00")])):
        material = montar_material(resultado)
        assert set(MARCADOR.findall(material.modelo)) <= set(material.marcadores)
