"""Mapeamento CEIS/CNEP (CSV de dados abertos da CGU) → `sancoes`.

Colunas conferidas no arquivo real de 05/11/2026 (`20261105_CEIS.csv` e `_CNEP.csv`). Os cabeçalhos são
comparados sem acento e em maiúsculas, para tolerar variação de codificação.
"""

import unicodedata
from typing import Any

from lastro_pipeline.modelos import Descarte, Normalizacao, RegistroNormalizado, Sancao
from lastro_pipeline.normalize.cnpj import classificar
from lastro_pipeline.normalize.valores import data, texto, uf

COL_CODIGO = "CODIGO DA SANCAO"
COL_TIPO_PESSOA = "TIPO DE PESSOA"
COL_DOCUMENTO = "CPF OU CNPJ DO SANCIONADO"
COL_CATEGORIA = "CATEGORIA DA SANCAO"
COL_INICIO = "DATA INICIO SANCAO"
COL_FIM = "DATA FINAL SANCAO"
COL_ORGAO = "ORGAO SANCIONADOR"
COL_UF_ORGAO = "UF ORGAO SANCIONADOR"
COL_FUNDAMENTACAO = "FUNDAMENTACAO LEGAL"
COL_CADASTRO = "CADASTRO"
COL_NOME = "NOME DO SANCIONADO"
COLUNAS_OBRIGATORIAS = (COL_CODIGO, COL_TIPO_PESSOA, COL_DOCUMENTO, COL_INICIO)
# Colunas guardadas na fixture: as usadas no mapeamento e a identificação da empresa. Texto livre fica de fora.
COLUNAS_AMOSTRA = (
    COL_CADASTRO,
    COL_CODIGO,
    COL_TIPO_PESSOA,
    COL_DOCUMENTO,
    COL_NOME,
    COL_CATEGORIA,
    COL_INICIO,
    COL_FIM,
    COL_ORGAO,
    COL_UF_ORGAO,
    COL_FUNDAMENTACAO,
)


def chave_coluna(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.upper().split())


def normalizar(registro: dict[str, Any], fonte_id: str, url_origem: str) -> Normalizacao:
    """`registro` já vem com as chaves passadas por `chave_coluna`."""
    codigo = texto(registro.get(COL_CODIGO))
    if registro.get(COL_TIPO_PESSOA, "").strip().upper() == "F":
        return Descarte("pessoa_fisica", codigo)
    tipo, cnpj = classificar(registro.get(COL_DOCUMENTO))
    if tipo == "cpf":
        return Descarte("pessoa_fisica", codigo)
    if tipo == "invalido" or codigo is None:
        return Descarte("documento_invalido", codigo)

    sancao = Sancao(
        fonte_id=fonte_id,
        id_origem=codigo,
        url_origem=url_origem,
        cnpj=cnpj,
        tipo=texto(registro.get(COL_CATEGORIA), 300),
        orgao_sancionador=texto(registro.get(COL_ORGAO), 500),
        uf_orgao=uf(registro.get(COL_UF_ORGAO)),
        data_inicio=data(registro.get(COL_INICIO)),
        data_fim=data(registro.get(COL_FIM)),
        fundamentacao=texto(registro.get(COL_FUNDAMENTACAO), 2000),
    )
    return RegistroNormalizado(fato=sancao)
