"""Integração de ponta a ponta: fixtures → pipeline → banco → API → resposta, recibo e auditoria.

Os valores esperados vêm de data/fixtures (ingeridos por `make demo`):
- pe_portal/exemplo_manual: contrato estadual 99.000.001/0001-01 (R$ 1.250.000,00, até 14/01/2027) e
  municipal de Garanhuns 99.000.002/0001-48 (R$ 480.000,50, encerrado em 09/03/2026);
- pncp/amostra: contratos reais de AL (18.008.915/0001-09 soma R$ 517.541,15);
- ceis/amostra: sanção real e vigente de 01.609.785/0001-67.
"""

from concurrent.futures import ThreadPoolExecutor

import pytest

from app.modules.recibos.canonico import hash_recibo
from app.modules.recibos.tests.esquema import erros

pytestmark = pytest.mark.integracao

ESTADUAL = "99.000.001/0001-01"
GARANHUNS = "99.000.002/0001-48"
PNCP_AL = "18.008.915/0001-09"
SANCIONADA = "01.609.785/0001-67"


def test_saude_com_banco_de_pe(http):
    assert http.get("/health").json() == {"status": "ok", "db": "ok", "llm": "mock"}


# ------------------------------------------------------------------ TCE-PE (pe_portal)
def test_contrato_do_tce_pe_chega_a_resposta_com_proveniencia(perguntar, http, cabecalho, banco_superusuario):
    r = perguntar("ana@alfa.demo", f"Quais contratos do CNPJ {ESTADUAL} vencem nos próximos 6 meses?")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["status"] == "respondida"
    assert "R$ 1.250.000,00" in corpo["resposta"] and "14/01/2027" in corpo["resposta"]
    assert "100,00% do valor vigente" in corpo["resposta"]
    assert corpo["sintetico"] is False
    (citacao,) = corpo["citacoes"]
    assert citacao["fonte_id"] == "pe_portal"
    assert citacao["url_origem"].startswith("https://sistemas.tcepe.tc.br/DadosAbertos/Contratos!json")

    recibo = http.get(f"/recibos/{corpo['recibo_id']}", headers=cabecalho("ana@alfa.demo")).json()
    assert erros(recibo["conteudo"]) == [] and recibo["hash"] == hash_recibo(recibo["conteudo"])
    (fonte,) = recibo["conteudo"]["fontes"]
    assert fonte["fonte_id"] == "pe_portal" and fonte["nome"] == "TCE-PE Dados Abertos"
    # A linha citada aponta para a execução da pipeline que a gravou.
    status = banco_superusuario.execute(
        "select status from execucoes_ingestao where id = %s", (fonte["execucao_id"],)
    ).fetchone()
    assert status == ("ok",)


def test_contrato_encerrado_vira_abstencao_com_data_da_coleta(perguntar):
    corpo = perguntar("ana@alfa.demo", f"Quais os contratos vigentes do CNPJ {GARANHUNS}?").json()
    assert corpo["status"] == "abstencao"
    assert corpo["resposta"].startswith(f"Não encontrei contratos vigentes do fornecedor {GARANHUNS}")
    assert "Fontes coletadas até" in corpo["resposta"]  # data da última execução da pipeline


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Defeito conhecido (T05/T08): empenho e liquidação vão para `pagamentos` e o resumo soma os dois. "
        "Garanhuns tem empenho de R$ 40.000 e duas liquidações de R$ 20.000 dele: o pago é R$ 40.000, "
        "a resposta diz R$ 80.000. Quando corrigirem, este teste passa e o xfail estrito acusa: tire a marca."
    ),
)
def test_valor_pago_nao_soma_empenho_com_liquidacao(perguntar):
    corpo = perguntar("ana@alfa.demo", f"Qual o resumo do fornecedor {GARANHUNS}?").json()
    assert "num total de R$ 40.000,00" in corpo["resposta"]


# ------------------------------------------------------------------ PNCP (AL) e escopo
def test_contratos_do_pncp_em_al_para_quem_tem_al(perguntar):
    corpo = perguntar("bia@beta.demo", f"Qual o resumo do fornecedor {PNCP_AL}?").json()
    assert corpo["status"] == "respondida"
    assert "R$ 517.541,15" in corpo["resposta"] and "(AL)" in corpo["resposta"]
    assert {c["fonte_id"] for c in corpo["citacoes"]} == {"pncp"}
    assert all(c["url_origem"].startswith("https://pncp.gov.br/app/contratos/") for c in corpo["citacoes"])


def test_quem_so_tem_pe_nao_ve_o_fornecedor_de_al_nem_o_valor(perguntar):
    corpo = perguntar("ana@alfa.demo", f"Qual o resumo do fornecedor {PNCP_AL}?").json()
    assert corpo["status"] == "abstencao"
    assert "517" not in corpo["resposta"] and corpo["citacoes"] == []


def test_admin_com_pe_e_al_ve_os_dois(perguntar):
    corpo = perguntar("admin@alfa.demo", f"Qual o resumo do fornecedor {PNCP_AL}?").json()
    assert "R$ 517.541,15" in corpo["resposta"] and "(AL, PE)" in corpo["resposta"]


def test_pedir_al_sendo_de_pe_e_403_e_fica_na_auditoria(perguntar, banco_superusuario):
    r = perguntar("ana@alfa.demo", f"Qual o resumo do fornecedor {PNCP_AL} em Alagoas?")
    assert r.status_code == 403 and r.json()["erro"]["codigo"] == "ESCOPO_NEGADO"
    evento = banco_superusuario.execute(
        "select evento, detalhes->>'motivo' from auditoria order by seq desc limit 1"
    ).fetchone()
    assert evento == ("negado", "uf_fora_do_escopo")


# ------------------------------------------------------------------ CEIS/CNEP
@pytest.mark.parametrize("email", ["ana@alfa.demo", "bia@beta.demo"])
def test_sancao_real_do_ceis_e_nacional(perguntar, email):
    corpo = perguntar(email, f"O fornecedor {SANCIONADA} tem sanção no CEIS ou no CNEP?").json()
    assert corpo["status"] == "respondida"
    assert "vigente" in corpo["resposta"] and "sinal para investigar" in corpo["resposta"]
    assert {c["fonte_id"] for c in corpo["citacoes"]} <= {"ceis", "cnep"}


# ------------------------------------------------------------------ injeção armazenada (seed 020)
def test_injecao_armazenada_nao_chega_a_resposta(perguntar):
    corpo = perguntar("ana@alfa.demo", "Resuma os contratos do CNPJ 99.999.999/0001-91.").json()
    assert "999.999.999,99" not in corpo["resposta"]
    assert "Ignore" not in corpo["resposta"] and "prompt" not in corpo["resposta"].lower()
    assert corpo["sintetico"] is True


# ------------------------------------------------------------------ registro e trilha
def test_consulta_aparece_na_listagem_e_o_auditor_ve(perguntar, http, cabecalho):
    feita = perguntar("admin@alfa.demo", f"O fornecedor {SANCIONADA} tem sanção?").json()
    do_auditor = http.get("/consultas?limite=200", headers=cabecalho("caio@alfa.demo")).json()
    assert feita["consulta_id"] in {c["id"] for c in do_auditor}
    da_bia = http.get("/consultas?limite=200", headers=cabecalho("bia@beta.demo")).json()
    assert feita["consulta_id"] not in {c["id"] for c in da_bia}


def test_consultas_em_paralelo_mantem_a_trilha_encadeada(perguntar, banco_superusuario):
    """24 consultas simultâneas de dois tenants: nenhuma falha e a cadeia de hashes continua íntegra."""
    pedidos = [("admin@alfa.demo", f"O fornecedor {SANCIONADA} tem sanção?")] * 12 + [
        ("bia@beta.demo", f"Qual o resumo do fornecedor {PNCP_AL}?")
    ] * 12
    with ThreadPoolExecutor(max_workers=12) as pool:
        codigos = list(pool.map(lambda p: perguntar(*p).status_code, pedidos))
    assert codigos == [200] * 24

    # Recalcula a cadeia com a mesma fórmula do trigger auditoria_encadear (001_schema.sql).
    quebras = banco_superusuario.execute(
        """
        with cadeia as (
          select seq, tenant_id, hash, hash_anterior,
                 coalesce(lag(hash) over (partition by tenant_id order by seq), repeat('0', 64)) as esperado_anterior,
                 encode(digest(hash_anterior || '|' || coalesce(tenant_id::text, '') || '|' ||
                               coalesce(usuario_id::text, '') || '|' || evento || '|' ||
                               coalesce(detalhes::text, '') || '|' || extract(epoch from criado_em)::text,
                        'sha256'), 'hex') as recalculado
            from auditoria
        )
        select count(*) filter (where hash_anterior <> esperado_anterior),
               count(*) filter (where hash <> recalculado),
               count(*)
          from cadeia
        """
    ).fetchone()
    assert quebras[:2] == (0, 0), f"cadeia quebrada: {quebras}"
    assert quebras[2] >= 24
