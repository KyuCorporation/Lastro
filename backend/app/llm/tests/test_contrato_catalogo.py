"""Contrato T08 → T10: o resultado real do executor do catálogo (Postgres, sob RLS) alimenta a redação.

Se o catálogo mudar o nome de um total, de um conjunto ou de uma coluna que os modelos usam, estes testes
quebram aqui, e não na demo. Os valores esperados vêm dos dados sintéticos de
`modules/catalogo/tests/conftest.py`.
"""

from datetime import date

import pytest

from app.llm.marcadores import montar_material
from app.llm.plano import PlanoConsulta
from app.llm.redator import redigir
from app.llm.verificador import MARCADOR, verificar
from app.modules.catalogo.executor import executar
from app.modules.catalogo.registry import CONSULTAS
from app.modules.catalogo.tests.conftest import F1, F2, HOJE

pytestmark = pytest.mark.usefixtures("dados_catalogo")

PARAMETROS = {
    "resumo_fornecedor": {"cnpj": F1},
    "contratos_vigentes": {"cnpj": F1},
    "contratos_vencendo": {"cnpj": F1, "dias": 180},
    "pagamentos_periodo": {"cnpj": F1, "data_inicio": date(2025, 1, 1), "data_fim": date(2025, 12, 31)},
    "sancoes_fornecedor": {"cnpj": F1},
}


def _plano(intent: str, **parametros) -> PlanoConsulta:
    return PlanoConsulta(intent=intent, parametros=parametros)


def test_todas_as_consultas_do_catalogo_estao_cobertas_aqui():
    assert set(PARAMETROS) == set(CONSULTAS)


class LLMQueCopiaOModelo:
    """Simula uma LLM obediente: devolve o modelo determinístico com os marcadores, sem números."""

    nome, modelo = "copia", "copia-1"

    def __init__(self, material):
        self.material = material

    def gerar(self, prompt, *, json=False, timeout_s, temperatura=0.0):
        return self.material.modelo


@pytest.mark.parametrize("intent", sorted(PARAMETROS))
def test_resultado_real_vira_texto_sem_marcador_e_passa_no_verificador(intent, ctx_ana):
    resultado = executar(_plano(intent, **PARAMETROS[intent]), ctx_ana, HOJE)
    material = montar_material(resultado)
    assert not material.vazio
    assert material.essenciais

    deterministico = redigir("p", resultado, ufs_autorizadas=ctx_ana.ufs, provedor=None)
    assert deterministico.status == "aprovado"
    assert deterministico.texto and not MARCADOR.search(deterministico.texto)
    assert "11.222.333/0001-81" in deterministico.texto

    anos = {v.year for k, v in resultado.parametros.items() if k.startswith("data_")}
    v = verificar(
        material.modelo,
        material.marcadores,
        ufs_autorizadas=ctx_ana.ufs,
        anos_permitidos=anos,
        essenciais=material.essenciais,
    )
    assert v.aprovado, v.motivos

    com_llm = redigir("p", resultado, ufs_autorizadas=ctx_ana.ufs, provedor=LLMQueCopiaOModelo(material))
    assert com_llm.status == "aprovado", com_llm.motivos
    assert com_llm.texto == deterministico.texto


def test_valores_do_texto_batem_com_o_banco(ctx_ana):
    # PE: C1 (100 mil, vence em 60 dias) e C2 (300 mil) vigentes; C3 (50 mil) encerrado. AL fica fora (RLS).
    vencendo = redigir(
        "p",
        executar(_plano("contratos_vencendo", cnpj=F1), ctx_ana, HOJE),
        ufs_autorizadas=("PE",),
        provedor=None,
    )
    assert "vence 1 contrato" in vencendo.texto
    assert "R$ 100.000,00" in vencendo.texto
    assert "25,00% do valor vigente" in vencendo.texto
    assert vencendo.valores["v4"] == {"valor": "100000.00", "tipo": "moeda", "origem": "sum(valor_global)"}

    resumo = redigir(
        "p",
        executar(_plano("resumo_fornecedor", cnpj=F1), ctx_ana, HOJE),
        ufs_autorizadas=("PE",),
        provedor=None,
    )
    assert "3 contratos, somando R$ 450.000,00" in resumo.texto
    assert "R$ 400.000,00 em contratos ainda vigentes" in resumo.texto
    assert "70.000" not in resumo.texto  # contrato de AL


def test_bia_so_ve_alagoas_no_texto(ctx_bia):
    r = redigir(
        "p",
        executar(_plano("resumo_fornecedor", cnpj=F1), ctx_bia, HOJE),
        ufs_autorizadas=("AL",),
        provedor=None,
    )
    assert "(AL)" in r.texto
    assert "R$ 70.000,00" in r.texto
    assert "450.000" not in r.texto and "PE" not in r.texto


def test_fornecedor_sem_registros_vira_abstencao_com_data_da_coleta(ctx_ana):
    resultado = executar(_plano("contratos_vigentes", cnpj=F2), ctx_ana, HOJE)
    r = redigir("p", resultado, ufs_autorizadas=("PE",), provedor=None, fontes_coletadas_em=HOJE)
    assert r.status == "abstencao"
    assert r.texto == (
        "Não encontrei contratos vigentes do fornecedor 11.444.777/0001-61 nas fontes autorizadas para você (PE). "
        "Fontes coletadas até 06/11/2026."
    )
