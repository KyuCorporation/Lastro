"""Mapeamento TCE-PE Dados Abertos → esquema (SPEC §10, regra 6; docs/catalogo-fontes.md).

HIPÓTESE até existir a amostra real (`ingest pe_portal --amostra 200` em rede brasileira): os nomes dos
campos abaixo vêm da documentação do cliente R `tceper`. Cada campo aceita nomes alternativos, na ordem.
Ao receber a amostra, ajuste só as tuplas `CAMPOS_*` (e a fixture `exemplo_manual`).
"""

from typing import Any

from lastro_pipeline.modelos import (
    Contrato,
    Descarte,
    Fornecedor,
    Normalizacao,
    Orgao,
    Pagamento,
    RegistroNormalizado,
)
from lastro_pipeline.normalize.cnpj import classificar
from lastro_pipeline.normalize.valores import campo, data, dinheiro, texto

FONTE_ID = "pe_portal"
UF = "PE"
ESFERAS = {"E": "estadual", "M": "municipal"}

CAMPOS_UG_CODIGO = ("CodigoEfiscoUG", "CodigoUG", "CodigoUnidadeGestora", "CodigoUnidadeJurisdicionada")
CAMPOS_UG_NOME = ("NomeUG", "UnidadeGestora", "NomeUnidadeGestora", "NomeUnidadeJurisdicionada")
CAMPOS_MUNICIPIO_CODIGO = ("CodigoMunicipio", "CodigoIBGE")
CAMPOS_MUNICIPIO_NOME = ("Municipio", "NomeMunicipio")
CAMPOS_ESFERA = ("Esfera",)
CAMPOS_ANO = ("AnoReferencia", "Ano", "AnoContrato", "AnoEmpenho")
CAMPOS_DOCUMENTO = ("CpfCnpj", "CPF_CNPJ", "CpfCnpjContratado", "CpfCnpjCredor", "CnpjContratado")
CAMPOS_NOME = ("NomeContratado", "NomeCredor", "RazaoSocial", "Nome", "Contratado", "Credor")

CAMPOS_CONTRATO_ID = ("IdContrato", "CodigoContrato")
CAMPOS_CONTRATO_NUMERO = ("NumeroContrato", "Numero")
CAMPOS_CONTRATO_OBJETO = ("Objeto", "ObjetoContrato", "DescricaoObjeto")
CAMPOS_CONTRATO_VALOR = ("ValorContrato", "ValorGlobal", "Valor")
CAMPOS_CONTRATO_ASSINATURA = ("DataAssinatura", "DataContrato")
CAMPOS_CONTRATO_INICIO = ("DataInicioVigencia", "DataVigenciaInicio", "InicioVigencia")
CAMPOS_CONTRATO_FIM = ("DataFimVigencia", "DataVigenciaFim", "FimVigencia", "DataTerminoVigencia")

CAMPOS_EMPENHO_NUMERO = ("NumeroEmpenho", "Empenho")
CAMPOS_EMPENHO_VALOR = ("ValorEmpenho", "ValorEmpenhado", "Valor")
CAMPOS_EMPENHO_DATA = ("DataEmpenho", "Data")
CAMPOS_EMPENHO_HISTORICO = ("Historico", "HistoricoEmpenho", "Descricao")

CAMPOS_LIQUIDACAO_NUMERO = ("NumeroLiquidacao", "Liquidacao", "SequencialLiquidacao")
CAMPOS_LIQUIDACAO_VALOR = ("ValorLiquidacao", "ValorLiquidado", "Valor")
CAMPOS_LIQUIDACAO_DATA = ("DataLiquidacao", "Data")


def _orgao(registro: dict[str, Any], esfera_param: str | None) -> Orgao | None:
    sigla = (texto(campo(registro, *CAMPOS_ESFERA)) or esfera_param or "").upper()[:1]
    esfera = ESFERAS.get(sigla)
    codigo = texto(campo(registro, *CAMPOS_UG_CODIGO))
    nome = texto(campo(registro, *CAMPOS_UG_NOME))
    if codigo is None and esfera == "municipal":
        codigo = texto(campo(registro, *CAMPOS_MUNICIPIO_CODIGO))
        nome = nome or texto(campo(registro, *CAMPOS_MUNICIPIO_NOME))
    if codigo is None:
        return None
    return Orgao(id=f"{FONTE_ID}:{codigo}", nome=nome or f"Unidade {codigo}", uf=UF, esfera=esfera)


def _fornecedor(registro: dict[str, Any]) -> Fornecedor | Descarte:
    tipo, cnpj = classificar(campo(registro, *CAMPOS_DOCUMENTO))
    if tipo == "cpf":
        return Descarte("pessoa_fisica")
    if tipo == "invalido":
        return Descarte("documento_invalido")
    return Fornecedor(cnpj=cnpj, razao_social=texto(campo(registro, *CAMPOS_NOME), 300))


def _chave(orgao: Orgao | None, registro: dict[str, Any], numero: str | None) -> str | None:
    if numero is None:
        return None
    ano = texto(campo(registro, *CAMPOS_ANO)) or "s-ano"
    ug = orgao.id.split(":", 1)[1] if orgao else "s-ug"
    return f"{ug}:{ano}:{numero}"


def normalizar(
    registro: dict[str, Any], tipo: str, url_origem: str, esfera_param: str | None = None
) -> Normalizacao:
    """`tipo` é o conjunto da API de onde veio o registro: 'contrato', 'empenho' ou 'liquidacao'."""
    fornecedor = _fornecedor(registro)
    if isinstance(fornecedor, Descarte):
        return fornecedor
    orgao = _orgao(registro, esfera_param)

    if tipo == "contrato":
        chave = texto(campo(registro, *CAMPOS_CONTRATO_ID)) or _chave(
            orgao, registro, texto(campo(registro, *CAMPOS_CONTRATO_NUMERO))
        )
        if chave is None:
            return Descarte("incompleto")
        fato: Contrato | Pagamento = Contrato(
            fonte_id=FONTE_ID,
            id_origem=f"ctr:{chave}",
            url_origem=url_origem,
            uf=UF,
            orgao_id=orgao.id if orgao else None,
            fornecedor_cnpj=fornecedor.cnpj,
            objeto=texto(campo(registro, *CAMPOS_CONTRATO_OBJETO), 4000),
            valor_global=dinheiro(campo(registro, *CAMPOS_CONTRATO_VALOR)),
            data_assinatura=data(campo(registro, *CAMPOS_CONTRATO_ASSINATURA)),
            vigencia_inicio=data(campo(registro, *CAMPOS_CONTRATO_INICIO)),
            vigencia_fim=data(campo(registro, *CAMPOS_CONTRATO_FIM)),
        )
    elif tipo == "empenho":
        chave = _chave(orgao, registro, texto(campo(registro, *CAMPOS_EMPENHO_NUMERO)))
        if chave is None:
            return Descarte("incompleto")
        historico = texto(campo(registro, *CAMPOS_EMPENHO_HISTORICO), 1000)
        fato = Pagamento(
            fonte_id=FONTE_ID,
            id_origem=f"emp:{chave}",
            url_origem=url_origem,
            uf=UF,
            orgao_id=orgao.id if orgao else None,
            fornecedor_cnpj=fornecedor.cnpj,
            data_pagamento=data(campo(registro, *CAMPOS_EMPENHO_DATA)),
            valor=dinheiro(campo(registro, *CAMPOS_EMPENHO_VALOR)),
            descricao="empenho" + (f": {historico}" if historico else ""),
        )
    elif tipo == "liquidacao":
        empenho = texto(campo(registro, *CAMPOS_EMPENHO_NUMERO))
        liquidacao = texto(campo(registro, *CAMPOS_LIQUIDACAO_NUMERO))
        chave = _chave(orgao, registro, f"{empenho}:{liquidacao}" if empenho and liquidacao else None)
        if chave is None:
            return Descarte("incompleto")
        fato = Pagamento(
            fonte_id=FONTE_ID,
            id_origem=f"liq:{chave}",
            url_origem=url_origem,
            uf=UF,
            orgao_id=orgao.id if orgao else None,
            fornecedor_cnpj=fornecedor.cnpj,
            data_pagamento=data(campo(registro, *CAMPOS_LIQUIDACAO_DATA)),
            valor=dinheiro(campo(registro, *CAMPOS_LIQUIDACAO_VALOR)),
            descricao=f"liquidação do empenho {empenho}",
        )
    else:
        raise ValueError(f"tipo de registro desconhecido no TCE-PE: {tipo}")

    return RegistroNormalizado(fato=fato, orgao=orgao, fornecedor=fornecedor)
