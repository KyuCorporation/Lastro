"""Resultados do catálogo montados à mão, para testar a redação sem banco."""

from datetime import date, datetime
from decimal import Decimal

from app.modules.catalogo.executor import ResultadoConsulta

CNPJ = "11222333000181"
HOJE = date(2026, 11, 6)
COLETA = datetime(2026, 11, 5, 10, 0)


def contrato(
    id_origem: str, valor: str, fim: date, orgao: str = "Secretaria de Saúde", objeto: str = "Limpeza"
):
    return {
        "id": f"id-{id_origem}",
        "fonte_id": "pe_portal",
        "id_origem": id_origem,
        "url_origem": f"https://sistemas.tcepe.tc.br/DadosAbertos/{id_origem}",
        "coletado_em": COLETA,
        "hash_conteudo": "a" * 64,
        "arquivo_bruto_id": None,
        "uf": "PE",
        "orgao_id": "pe_portal:1",
        "orgao_nome": orgao,
        "objeto": objeto,
        "valor_global": Decimal(valor),
        "data_assinatura": date(2025, 1, 1),
        "vigencia_inicio": date(2025, 1, 1),
        "vigencia_fim": fim,
    }


def vencendo(linhas=None, objeto: str = "Limpeza") -> ResultadoConsulta:
    linhas = [contrato("C1", "100000.00", date(2027, 1, 5), objeto=objeto)] if linhas is None else linhas
    total = sum((c["valor_global"] for c in linhas), Decimal(0))
    return ResultadoConsulta(
        intent="contratos_vencendo",
        versao="contratos_vencendo@v1",
        parametros={"cnpj": CNPJ, "hoje": HOJE, "ufs": ["PE"], "dias": 180},
        conjuntos={"linhas": linhas},
        totais={
            "n_contratos": len(linhas),
            "valor_vencendo": total,
            "valor_vigente_total": Decimal("400000.00"),
            "percentual_do_vigente": (total * 100 / Decimal("400000.00")).quantize(Decimal("0.01")),
        },
    )


def pagamentos(linhas=None) -> ResultadoConsulta:
    linhas = linhas if linhas is not None else [
        {
            "id": "p1", "fonte_id": "pe_portal", "id_origem": "liq:1", "url_origem": "https://x/liq/1",
            "coletado_em": COLETA, "hash_conteudo": "b" * 64, "arquivo_bruto_id": None, "uf": "PE",
            "orgao_id": "pe_portal:1", "orgao_nome": "Prefeitura de Garanhuns", "contrato_id": None,
            "data_pagamento": date(2025, 3, 10), "valor": Decimal("1234.56"), "descricao": "liquidação",
        }
    ]  # fmt: skip
    return ResultadoConsulta(
        intent="pagamentos_periodo",
        versao="pagamentos_periodo@v2",
        parametros={
            "cnpj": CNPJ,
            "hoje": HOJE,
            "ufs": ["PE"],
            "data_inicio": date(2025, 1, 1),
            "data_fim": date(2025, 12, 31),
        },
        conjuntos={"linhas": linhas},
        totais={
            "n_pagamentos": len(linhas),
            "valor_total": sum((p["valor"] for p in linhas), Decimal(0)),
            "n_empenhos": 0,
            "valor_empenhado": Decimal(0),
        },
    )


def resumo(vazio: bool = False, empenhado: str = "0") -> ResultadoConsulta:
    grupos = [] if vazio else [
        {"uf": "PE", "orgao_id": "pe_portal:1", "orgao_nome": "Secretaria de Saúde", "n_contratos": 2,
         "valor_contratado": Decimal("150000.00"), "valor_vigente": Decimal("100000.00"), "n_pagamentos": 1,
         "valor_pago": Decimal("40000.00"), "n_empenhos": int(Decimal(empenhado) > 0),
         "valor_empenhado": Decimal(empenhado)},
    ]  # fmt: skip
    soma = lambda k: sum((g[k] for g in grupos), Decimal(0))
    return ResultadoConsulta(
        intent="resumo_fornecedor",
        versao="resumo_fornecedor@v2",
        parametros={"cnpj": CNPJ, "hoje": HOJE, "ufs": ["PE"]},
        conjuntos={"por_uf_orgao": grupos, "contratos": [], "pagamentos": []},
        totais={
            "n_contratos": sum(g["n_contratos"] for g in grupos),
            "n_pagamentos": sum(g["n_pagamentos"] for g in grupos),
            "valor_contratado": soma("valor_contratado"),
            "valor_vigente": soma("valor_vigente"),
            "valor_pago": soma("valor_pago"),
            "n_empenhos": sum(g["n_empenhos"] for g in grupos),
            "valor_empenhado": soma("valor_empenhado"),
        },
    )


def sancoes(vigente: bool = True) -> ResultadoConsulta:
    linhas = [
        {"id": "s1", "fonte_id": "ceis", "id_origem": "S1", "url_origem": "https://x/s1",
         "coletado_em": COLETA, "hash_conteudo": "c" * 64, "arquivo_bruto_id": None, "tipo": "Impedimento",
         "orgao_sancionador": "Órgão X", "uf_orgao": "PE", "data_inicio": date(2026, 1, 1),
         "data_fim": date(2027, 1, 1), "fundamentacao": "Lei", "vigente": vigente},
    ]  # fmt: skip
    return ResultadoConsulta(
        intent="sancoes_fornecedor",
        versao="sancoes_fornecedor@v1",
        parametros={"cnpj": CNPJ, "hoje": HOJE},
        conjuntos={"linhas": linhas},
        totais={"n_sancoes": 1, "n_vigentes": int(vigente)},
    )


def vigentes() -> ResultadoConsulta:
    linhas = [contrato("C1", "100000.00", date(2027, 1, 5)), contrato("C2", "300000.00", date(2027, 12, 10))]
    return ResultadoConsulta(
        intent="contratos_vigentes",
        versao="contratos_vigentes@v1",
        parametros={"cnpj": CNPJ, "hoje": HOJE, "ufs": ["PE"]},
        conjuntos={"linhas": linhas},
        totais={"n_contratos": 2, "valor_total": Decimal("400000.00")},
    )
