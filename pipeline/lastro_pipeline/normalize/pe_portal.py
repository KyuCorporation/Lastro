"""Mapeamento TCE-PE Dados Abertos → esquema (SPEC §10, regra 6; docs/catalogo-fontes.md) e saneamento LGPD.

Nomes de campo conferidos na API real em 15/11/2026:
- `Contratos`: CamelCase (`CodigoContrato`, `CPF_CNPJ`, `Vigencia` = "dd/mm/aaaa a dd/mm/aaaa");
- `DespesasEstaduais` / `DespesasMunicipais` (um registro por empenho) e `EmpenhoLiquidacao`: MAIÚSCULAS.

A liquidação não traz o credor: ele vem do empenho, pela chave unidade gestora + exercício + empenho.

LGPD (AGENTS.md §3.6): `sanear` roda antes de a resposta ser gravada em cache ou no bronze. Registro de pessoa
física (ou sem CNPJ válido) vira só um marcador, para continuar contado em `registros_descartados`; CPF solto em
nome ou texto livre de registro de PJ é mascarado. A API manda o CPF inteiro em `NumeroDocumentoAjustado`.
"""

import json
import re
from datetime import date
from typing import Any, Literal

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
from lastro_pipeline.normalize.valores import campo, data, dinheiro, lista_de_registros, texto

FONTE_ID = "pe_portal"
UF = "PE"
ESFERAS = {"E": "estadual", "M": "municipal"}
Tipo = Literal["contrato", "empenho", "liquidacao"]

ENVELOPES = ("resposta.conteudo", "conteudo")
OMITIDO = "_lastro_omitido"  # marcador do registro que o saneamento reduziu; o valor é o motivo do descarte

CAMPOS_DOCUMENTO = ("CPF_CNPJ",)
CAMPOS_NOME = ("RazaoSocial", "NOME_FORNECEDOR", "FORNECEDOR")
CAMPOS_TEXTO_LIVRE = ("HISTORICO", "Objeto")
CAMPOS_ESFERA = ("Esfera", "ESFERA")
# Estado: código e-Fisco (o mesmo nos contratos e nas despesas). Municípios: código da UG no TCE.
CAMPOS_UG_CODIGO = ("CodigoEfiscoUG", "CodigoUG", "ID_UNIDADE_GESTORA")
CAMPOS_UG_NOME = ("UnidadeGestora", "NOMEUNIDADEGESTORA")
CAMPOS_EMPENHO_ID = ("ID_EMPENHO", "IDEMPENHO", "NUMEROEMPENHO")  # ID_EMPENHO só existe nos municípios

# Campos que vão para a fixture `amostra/` (só os usados; texto livre fica de fora).
CAMPOS_AMOSTRA: dict[str, tuple[str, ...]] = {
    "contrato": (
        "Esfera",
        "Municipio",
        "CodigoEfiscoUG",
        "CodigoUG",
        "UnidadeGestora",
        "CodigoContrato",
        "NumeroContrato",
        "AnoContrato",
        "CPF_CNPJ",
        "RazaoSocial",
        "Objeto",
        "Valor",
        "Vigencia",
        "LinkArquivo",
        "Situacao",
    ),
    "empenho": (
        "ESFERA",
        "CODIGO_MUNICIPIO",
        "ID_UNIDADE_GESTORA",
        "NOMEUNIDADEGESTORA",
        "ANOREFERENCIA",
        "ID_EMPENHO",
        "NUMEROEMPENHO",
        "CPF_CNPJ",
        "NOME_FORNECEDOR",
        "FORNECEDOR",
        "VALOREMPENHADO",
        "DATAEMPENHO",
    ),
    "liquidacao": (
        "ESFERA",
        "MUNICIPIO",
        "ID_UNIDADE_GESTORA",
        "ANOREFERENCIA",
        "IDEMPENHO",
        "NUMEROEMPENHO",
        "NUMERO",
        "TIPO",
        "VALOR",
        "DATA",
    ),
}

_CPF_FORMATADO = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_ONZE_DIGITOS = re.compile(r"(?<!\d)\d{11}(?!\d)")
_VIGENCIA = re.compile(r"(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})")
# `LinkArquivo`: página do documento do contrato no sistema do tribunal (só http). Vale como `url_origem` só se for
# desse host; qualquer outra coisa (vazio, outro host, outro esquema) fica com a URL do recorte da API.
_LINK_TCEPE = re.compile(r"https?://sistemas\.tcepe\.tc\.br/[^\s\"<>]*")


def _link_do_contrato(registro: dict[str, Any], url_recorte: str) -> str:
    link = (texto(registro.get("LinkArquivo")) or "").strip()
    return link if _LINK_TCEPE.fullmatch(link) else url_recorte


# ------------------------------------------------------------------ saneamento (LGPD)
def decodificar(conteudo: bytes) -> str:
    """A API responde em ISO-8859-1; fixture e resposta saneada estão em UTF-8."""
    try:
        return conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return conteudo.decode("latin-1")


def mascarar_cpf(valor: str) -> str:
    """Tira CPF formatado e sequência solta de 11 dígitos (razão social de MEI costuma trazer o CPF)."""
    return _ONZE_DIGITOS.sub("***", _CPF_FORMATADO.sub("***", valor))


def _motivo_omissao(registro: dict[str, Any]) -> Literal["pessoa_fisica", "documento_invalido"] | None:
    tipo_documento, _ = classificar(campo(registro, *CAMPOS_DOCUMENTO))
    if tipo_documento == "cpf" or str(registro.get("TipoDocumento", "")).strip().upper() == "CPF":
        return "pessoa_fisica"
    return "documento_invalido" if tipo_documento == "invalido" else None


def _limpar(registro: dict[str, Any]) -> dict[str, Any]:
    limpo = {}
    for chave, valor in registro.items():
        if isinstance(valor, str):
            valor = valor.strip()  # a API preenche colunas char com centenas de espaços
            if chave in CAMPOS_NOME or chave in CAMPOS_TEXTO_LIVRE:
                valor = mascarar_cpf(valor)
        limpo[chave] = valor
    return limpo


def sanear(conteudo: bytes, tipo: Tipo) -> bytes:
    """Resposta da API sem dado de pessoa física, em UTF-8. É isto que vai para o cache e para o bronze."""
    dados = json.loads(decodificar(conteudo))
    envelope = dados.get("resposta") if isinstance(dados, dict) else None
    meta = {k: v for k, v in envelope.items() if k != "conteudo"} if isinstance(envelope, dict) else {}
    omitidos: dict[str, int] = {}
    saneados = []
    for registro in lista_de_registros(dados, ENVELOPES):
        motivo = None if tipo == "liquidacao" else _motivo_omissao(registro)
        if motivo:
            omitidos[motivo] = omitidos.get(motivo, 0) + 1
            saneados.append({OMITIDO: motivo})
        else:
            saneados.append(_limpar(registro))
    meta["saneamento_lgpd"] = {"registros_omitidos": omitidos}
    saida = {"resposta": {**meta, "conteudo": saneados}}
    return json.dumps(saida, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def recortar_para_amostra(registro: dict[str, Any], tipo: str) -> dict[str, Any]:
    return {k: registro[k] for k in CAMPOS_AMOSTRA[tipo] if k in registro}


# ------------------------------------------------------------------ normalização
def _esfera(registro: dict[str, Any], esfera_param: str | None = None) -> str:
    return (texto(campo(registro, *CAMPOS_ESFERA)) or esfera_param or "").upper()[:1]


def _ug(registro: dict[str, Any], esfera_param: str | None = None) -> str | None:
    """Código da unidade gestora. No estado é o e-Fisco, de 6 dígitos: as despesas vêm sem o zero à esquerda
    (`10001`) e os contratos com ele (`010001`)."""
    codigo = texto(campo(registro, *CAMPOS_UG_CODIGO))
    if codigo and codigo.isdigit() and _esfera(registro, esfera_param) == "E":
        return codigo.zfill(6)
    return codigo


def _orgao(registro: dict[str, Any], esfera_param: str | None) -> Orgao | None:
    sigla = _esfera(registro, esfera_param)
    codigo = _ug(registro, esfera_param)
    if codigo is None:
        return None
    nome = texto(campo(registro, *CAMPOS_UG_NOME), 300)
    return Orgao(
        id=f"{FONTE_ID}:{codigo}", nome=nome or f"Unidade {codigo}", uf=UF, esfera=ESFERAS.get(sigla)
    )


def _fornecedor(registro: dict[str, Any]) -> Fornecedor | Descarte:
    motivo = registro.get(OMITIDO) or _motivo_omissao(registro)
    if motivo:
        return Descarte("pessoa_fisica" if motivo == "pessoa_fisica" else "documento_invalido")
    _, cnpj = classificar(campo(registro, *CAMPOS_DOCUMENTO))
    nome = texto(campo(registro, *CAMPOS_NOME), 300)
    return Fornecedor(cnpj=cnpj, razao_social=texto(mascarar_cpf(nome)) if nome else None)


def chave_empenho(registro: dict[str, Any]) -> str | None:
    """`<UG>:<exercício>:<empenho>`: igual no registro de despesa e no de liquidação; liga um ao outro."""
    ug = _ug(registro)
    ano = texto(registro.get("ANOREFERENCIA"))
    empenho = texto(campo(registro, *CAMPOS_EMPENHO_ID))
    return f"{ug}:{ano}:{empenho}" if ug and ano and empenho else None


def _vigencia(valor: Any) -> tuple[date | None, date | None]:
    achado = _VIGENCIA.search(str(valor or ""))
    return (data(achado.group(1)), data(achado.group(2))) if achado else (None, None)


def _contrato(registro: dict[str, Any], url_origem: str, esfera_param: str | None) -> Normalizacao:
    fornecedor = _fornecedor(registro)
    if isinstance(fornecedor, Descarte):
        return fornecedor
    codigo = texto(registro.get("CodigoContrato"))
    if codigo is None:
        return Descarte("incompleto")
    orgao = _orgao(registro, esfera_param)
    inicio, fim = _vigencia(registro.get("Vigencia"))
    fato = Contrato(
        fonte_id=FONTE_ID,
        id_origem=f"ctr:{codigo}",
        url_origem=_link_do_contrato(registro, url_origem),
        uf=UF,
        orgao_id=orgao.id if orgao else None,
        fornecedor_cnpj=fornecedor.cnpj,
        objeto=texto(mascarar_cpf(str(registro.get("Objeto") or "")), 4000),
        valor_global=dinheiro(registro.get("Valor")),
        data_assinatura=None,  # a API não informa; a vigência vem de `Vigencia`
        vigencia_inicio=inicio,
        vigencia_fim=fim,
        situacao=texto(registro.get("Situacao"), 120),
    )
    return RegistroNormalizado(fato=fato, orgao=orgao, fornecedor=fornecedor)


def _empenho(registro: dict[str, Any], url_origem: str, esfera_param: str | None) -> Normalizacao:
    fornecedor = _fornecedor(registro)
    if isinstance(fornecedor, Descarte):
        return fornecedor
    chave = chave_empenho(registro)
    if chave is None:
        return Descarte("incompleto")
    orgao = _orgao(registro, esfera_param)
    historico = texto(mascarar_cpf(str(registro.get("HISTORICO") or "")), 1000)
    fato = Pagamento(
        fonte_id=FONTE_ID,
        id_origem=f"emp:{chave}",
        url_origem=url_origem,
        uf=UF,
        orgao_id=orgao.id if orgao else None,
        fornecedor_cnpj=fornecedor.cnpj,
        data_pagamento=data(registro.get("DATAEMPENHO")),
        valor=dinheiro(registro.get("VALOREMPENHADO")),
        descricao="empenho" + (f": {historico}" if historico else ""),
    )
    return RegistroNormalizado(fato=fato, orgao=orgao, fornecedor=fornecedor)


def _liquidacao(
    registro: dict[str, Any], url_origem: str, credor: tuple[str, str | None] | None
) -> Normalizacao:
    chave = chave_empenho(registro)
    numero = texto(registro.get("NUMERO"))
    if chave is None or numero is None:
        return Descarte("incompleto")
    if credor is None:  # empenho de pessoa física, sem CNPJ válido ou fora do recorte coletado
        return Descarte("fora_do_escopo", id_origem=f"liq:{chave}:{numero}")
    cnpj, orgao_id = credor
    empenho = texto(registro.get("NUMEROEMPENHO")) or chave.rsplit(":", 1)[1]
    anulacao = "anula" in (texto(registro.get("TIPO")) or "").lower()
    fato = Pagamento(
        fonte_id=FONTE_ID,
        id_origem=f"liq:{chave}:{numero}",
        url_origem=url_origem,
        uf=UF,
        orgao_id=orgao_id,
        fornecedor_cnpj=cnpj,
        data_pagamento=data(registro.get("DATA")),
        valor=dinheiro(registro.get("VALOR")),  # anulação vem negativa: a soma dá o líquido
        descricao=("anulação de liquidação" if anulacao else "liquidação") + f" do empenho {empenho}",
    )
    return RegistroNormalizado(fato=fato)


def normalizar(
    registro: dict[str, Any],
    tipo: str,
    url_origem: str,
    esfera_param: str | None = None,
    credor: tuple[str, str | None] | None = None,
) -> Normalizacao:
    """`tipo` é o conjunto de onde veio o registro. `credor` (CNPJ, órgão) só vale para a liquidação."""
    if tipo == "contrato":
        return _contrato(registro, url_origem, esfera_param)
    if tipo == "empenho":
        return _empenho(registro, url_origem, esfera_param)
    if tipo == "liquidacao":
        return _liquidacao(registro, url_origem, credor)
    raise ValueError(f"tipo de registro desconhecido no TCE-PE: {tipo}")
