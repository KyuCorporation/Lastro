"""Dados sintéticos do catálogo, gravados como superusuário só para o teste e apagados no fim.

A API nunca usa o superusuário. Aqui ele só serve para montar e limpar as linhas de teste, já que lastro_app
não grava fatos públicos e lastro_ingest não apaga.
"""

import os
from datetime import date, timedelta

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo

HOJE = date(2026, 11, 6)
F1 = "11222333000181"  # CNPJ sintético com dígitos verificadores válidos
F2 = "11444777000161"
PREFIXO = "TCAT-"


def _superusuario() -> psycopg.Connection:
    base = conninfo_to_dict(os.environ["DATABASE_URL"])
    base.update(user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"])
    return psycopg.connect(make_conninfo(**base), autocommit=True)


def d(dias: int) -> date:
    return HOJE + timedelta(days=dias)


ORGAOS = [
    ("demo_sintetico:TCAT-PE1", "Secretaria Teste PE 1", "PE", "estadual"),
    ("demo_sintetico:TCAT-PE2", "Prefeitura Teste PE 2", "PE", "municipal"),
    ("demo_sintetico:TCAT-AL1", "Secretaria Teste AL 1", "AL", "estadual"),
]

# (id_origem, uf, orgao, valor, vigencia_fim)
CONTRATOS = [
    ("TCAT-C1", "PE", "demo_sintetico:TCAT-PE1", "100000.00", d(60)),  # vigente, vence em 60 dias
    ("TCAT-C2", "PE", "demo_sintetico:TCAT-PE2", "300000.00", d(400)),  # vigente, longe de vencer
    ("TCAT-C3", "PE", "demo_sintetico:TCAT-PE1", "50000.00", d(-10)),  # encerrado
    ("TCAT-C4", "AL", "demo_sintetico:TCAT-AL1", "70000.00", d(30)),  # vigente em AL
]

# (id_origem, uf, orgao, data, valor)
PAGAMENTOS = [
    ("TCAT-P1", "PE", "demo_sintetico:TCAT-PE1", date(2025, 3, 10), "40000.00"),
    ("TCAT-P2", "PE", "demo_sintetico:TCAT-PE2", date(2025, 8, 1), "10000.00"),
    ("TCAT-P3", "PE", "demo_sintetico:TCAT-PE1", date(2024, 12, 31), "5000.00"),
    ("TCAT-P4", "AL", "demo_sintetico:TCAT-AL1", date(2025, 5, 5), "20000.00"),
]

# (fonte, id_origem, data_inicio, data_fim)
SANCOES = [
    ("ceis", "TCAT-S1", d(-100), d(100)),  # vigente
    ("cnep", "TCAT-S2", d(-400), d(-5)),  # passada
]

LIMPAR = [
    "delete from pagamentos where id_origem like 'TCAT-%'",
    "delete from contratos where id_origem like 'TCAT-%'",
    "delete from sancoes where id_origem like 'TCAT-%'",
    "delete from orgaos where id like 'demo_sintetico:TCAT-%'",
    "delete from fornecedores where cnpj in ('11222333000181', '11444777000161')",
]


INSERIR_FORNECEDORES = """
insert into fornecedores (cnpj, razao_social, uf_sede) values (%s, %s, 'PE'), (%s, %s, 'PE')
"""
INSERIR_ORGAO = "insert into orgaos (id, nome, uf, esfera) values (%s, %s, %s, %s)"
INSERIR_CONTRATO = """
insert into contratos (fonte_id, id_origem, uf, orgao_id, fornecedor_cnpj, objeto, valor_global,
                       data_assinatura, vigencia_inicio, vigencia_fim, url_origem, coletado_em, hash_conteudo)
values ('demo_sintetico', %s, %s, %s, %s, 'Serviço de teste', %s, %s, %s, %s, %s, now(), %s)
"""
INSERIR_PAGAMENTO = """
insert into pagamentos (fonte_id, id_origem, uf, orgao_id, fornecedor_cnpj, data_pagamento, valor,
                        descricao, url_origem, coletado_em, hash_conteudo)
values ('demo_sintetico', %s, %s, %s, %s, %s, %s, 'liquidação de teste', %s, now(), %s)
"""
INSERIR_SANCAO = """
insert into sancoes (fonte_id, id_origem, cnpj, tipo, orgao_sancionador, data_inicio, data_fim,
                     url_origem, coletado_em, hash_conteudo)
values (%s, %s, %s, 'Impedimento', 'Órgão Teste', %s, %s, %s, now(), %s)
"""


def _url(id_origem: str) -> str:
    return f"about:blank#teste-{id_origem}"


def _hash(id_origem: str) -> str:
    return (id_origem.encode().hex() * 64)[:64]


@pytest.fixture(scope="session")
def dados_catalogo():
    with _superusuario() as conn:
        for comando in LIMPAR:
            conn.execute(comando)
        conn.execute(INSERIR_FORNECEDORES, (F1, "FORNECEDOR TESTE UM LTDA", F2, "FORNECEDOR TESTE DOIS LTDA"))
        conn.cursor().executemany(INSERIR_ORGAO, ORGAOS)
        for id_origem, uf, orgao, valor, fim in CONTRATOS:
            conn.execute(
                INSERIR_CONTRATO,
                (id_origem, uf, orgao, F1, valor, d(-500), d(-500), fim, _url(id_origem), _hash(id_origem)),
            )
        for id_origem, uf, orgao, data, valor in PAGAMENTOS:
            conn.execute(
                INSERIR_PAGAMENTO, (id_origem, uf, orgao, F1, data, valor, _url(id_origem), _hash(id_origem))
            )
        for fonte, id_origem, inicio, fim in SANCOES:
            conn.execute(
                INSERIR_SANCAO, (fonte, id_origem, F1, inicio, fim, _url(id_origem), _hash(id_origem))
            )
    yield
    with _superusuario() as conn:
        for comando in LIMPAR:
            conn.execute(comando)
