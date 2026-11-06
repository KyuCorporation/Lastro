"""Mapeamento PNCP `/v1/contratos` (RecuperarContratoDTO, OpenAPI v3) → esquema."""

from typing import Any

from lastro_pipeline.modelos import (
    Contrato,
    Descarte,
    Fornecedor,
    Normalizacao,
    Orgao,
    RegistroNormalizado,
)
from lastro_pipeline.normalize.cnpj import classificar
from lastro_pipeline.normalize.valores import campo, data, dinheiro, texto, uf

FONTE_ID = "pncp"
URL_PUBLICA = "https://pncp.gov.br/app/contratos/{cnpj}/{ano}/{sequencial}"
ESFERAS = {"F": "federal", "E": "estadual", "M": "municipal", "D": "distrital"}


def uf_do_registro(registro: dict[str, Any]) -> str | None:
    return uf(campo(registro, "unidadeOrgao.ufSigla"))


def normalizar(registro: dict[str, Any], ufs_permitidas: set[str]) -> Normalizacao:
    id_origem = texto(campo(registro, "numeroControlePNCP"))
    sigla = uf_do_registro(registro)
    if sigla not in ufs_permitidas:
        return Descarte("fora_do_escopo", id_origem)
    if id_origem is None:
        return Descarte("incompleto")

    tipo_pessoa = texto(campo(registro, "tipoPessoa"))
    documento, cnpj = classificar(campo(registro, "niFornecedor"))
    if tipo_pessoa == "PF" or documento == "cpf":
        return Descarte("pessoa_fisica", id_origem)
    if documento == "invalido":  # inclui estrangeira (tipoPessoa PE) sem CNPJ
        return Descarte("documento_invalido", id_origem)

    cnpj_orgao = texto(campo(registro, "orgaoEntidade.cnpj"))
    codigo_unidade = texto(campo(registro, "unidadeOrgao.codigoUnidade"))
    orgao = None
    if cnpj_orgao:
        orgao = Orgao(
            id=f"{FONTE_ID}:{cnpj_orgao}" + (f":{codigo_unidade}" if codigo_unidade else ""),
            nome=texto(campo(registro, "unidadeOrgao.nomeUnidade", "orgaoEntidade.razaoSocial"), 300)
            or cnpj_orgao,
            uf=sigla,
            esfera=ESFERAS.get(texto(campo(registro, "orgaoEntidade.esferaId")) or ""),
        )

    ano, sequencial = campo(registro, "anoContrato"), campo(registro, "sequencialContrato")
    url = URL_PUBLICA.format(cnpj=cnpj_orgao, ano=ano, sequencial=sequencial) if cnpj_orgao and ano else None

    contrato = Contrato(
        fonte_id=FONTE_ID,
        id_origem=id_origem,
        url_origem=url,
        uf=sigla,
        orgao_id=orgao.id if orgao else None,
        fornecedor_cnpj=cnpj,
        objeto=texto(campo(registro, "objetoContrato"), 4000),
        valor_global=dinheiro(campo(registro, "valorGlobal", "valorInicial")),
        data_assinatura=data(campo(registro, "dataAssinatura")),
        vigencia_inicio=data(campo(registro, "dataVigenciaInicio")),
        vigencia_fim=data(campo(registro, "dataVigenciaFim")),
    )
    fornecedor = Fornecedor(cnpj=cnpj, razao_social=texto(campo(registro, "nomeRazaoSocialFornecedor"), 300))
    return RegistroNormalizado(fato=contrato, orgao=orgao, fornecedor=fornecedor)
