from datetime import date
from decimal import Decimal

import pytest

from lastro_pipeline.normalize.cnpj import classificar, cnpj_valido, com_dv
from lastro_pipeline.normalize.valores import campo, data, dinheiro, lista_de_registros, texto

CNPJ_COM_ZERO = com_dv("012345670001")


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("99.000.001/0001-01", ("cnpj", "99000001000101")),
        ("99000002000148", ("cnpj", "99000002000148")),
        (int(CNPJ_COM_ZERO), ("cnpj", CNPJ_COM_ZERO)),  # CNPJ lido como número perde o zero à esquerda
        ("123.456.789-09", ("cpf", "")),
        ("***.456.789-**", ("cpf", "")),
        ("99000001000102", ("invalido", "")),
        ("11111111111111", ("invalido", "")),
        ("", ("invalido", "")),
        (None, ("invalido", "")),
    ],
)
def test_classificar_documento(entrada, esperado):
    assert classificar(entrada) == esperado


def test_cpf_nunca_e_devolvido():
    tipo, digitos = classificar("12345678909")
    assert tipo == "cpf"
    assert digitos == ""


def test_com_dv_gera_cnpj_valido():
    assert cnpj_valido(com_dv("112223330001"))


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("1.250.000,00", Decimal("1250000.00")),
        ("1234,5", Decimal("1234.50")),
        (480000.5, Decimal("480000.50")),
        (1000, Decimal("1000.00")),
        ("R$ 10,005", Decimal("10.01")),
        ("abc", None),
        (None, None),
        (True, None),
    ],
)
def test_dinheiro_sem_float(entrada, esperado):
    assert dinheiro(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("2025-03-10", date(2025, 3, 10)),
        ("2026-10-01T07:05:02", date(2026, 10, 1)),
        ("15/01/2025", date(2025, 1, 15)),
        ("20250115", date(2025, 1, 15)),
        ("31/02/2025", None),
        ("", None),
    ],
)
def test_data(entrada, esperado):
    assert data(entrada) == esperado


def test_campo_aceita_chaves_alternativas_e_aninhadas():
    registro = {"a": "", "b": {"c": "valor"}, "d": "outro"}
    assert campo(registro, "a", "b.c", "d") == "valor"
    assert campo(registro, "x", "y") is None


def test_texto_colapsa_espacos_e_corta():
    assert texto("  muito   espaço \n aqui ", 10) == "muito espa"
    assert texto("   ") is None


def test_lista_de_registros_em_envelopes():
    assert lista_de_registros([{"a": 1}, "x"], ()) == [{"a": 1}]
    assert lista_de_registros({"resposta": {"conteudo": [{"a": 1}]}}, ("resposta.conteudo",)) == [{"a": 1}]
    assert lista_de_registros({"outra": 1}, ("conteudo",)) == []
