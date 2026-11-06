"""Prioridade da fila (SPEC §9) e separação de CNPJs, sem banco."""

import math
from decimal import Decimal

import pytest

from app.modules.carteiras.prioridade import fator_exposicao, prioridade
from app.modules.carteiras.service import separar_cnpjs


def test_formula_do_spec_com_exposicao_real():
    valor = Decimal("400000.00")
    assert prioridade(["forte", "atencao"], valor) == round(13 * math.log10(400001), 4)


def test_sem_sinal_prioridade_zero_mesmo_com_exposicao():
    assert prioridade([], Decimal(1000000)) == 0


def test_sancionado_sem_exposicao_nao_vai_para_o_fim_da_fila():
    """Pela fórmula pura daria 0, atrás de qualquer atenção; com o piso, vale o peso da sanção (10)."""
    sancionado = prioridade(["forte"], Decimal(0))
    assert sancionado == 10
    assert sancionado > prioridade(["atencao"], Decimal(500))  # 3 × log10(501) ≈ 8,1
    assert sancionado < prioridade(["atencao"], Decimal(50000))  # a fórmula do SPEC segue valendo


@pytest.mark.parametrize(("valor", "fator"), [(Decimal(0), 1.0), (Decimal(9), 1.0), (Decimal(99), 2.0)])
def test_piso_do_fator_de_exposicao(valor, fator):
    assert fator_exposicao(valor) == pytest.approx(fator)


def test_mais_exposicao_mais_prioridade_com_os_mesmos_sinais():
    assert prioridade(["atencao"], Decimal(1000000)) > prioridade(["atencao"], Decimal(1000))


def test_separar_cnpjs_normaliza_deduplica_e_devolve_invalidos():
    validos, invalidos = separar_cnpjs(
        ["11.222.333/0001-81", "11222333000181", "11444777000161", "123", " 123 ", "", "11111111111111"]
    )
    assert validos == ["11222333000181", "11444777000161"]
    assert invalidos == ["123", "11111111111111"]
