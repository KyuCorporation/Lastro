"""T07: conectores CEIS e CNEP. Fixture real recortada + caso sintético de pessoa física."""

import io
import zipfile
from datetime import date

import httpx
import pytest

from lastro_pipeline import fixtures
from lastro_pipeline.connectors.sancoes import ArquivoInvalido, ConectorSancoes, ler_csv
from lastro_pipeline.http import ClienteHttp, FonteIndisponivel
from lastro_pipeline.modelos import Descarte, RegistroNormalizado, Sancao
from tests.conftest import FIXTURES

CABECALHO_REAL = (
    "CADASTRO;CÓDIGO DA SANÇÃO;TIPO DE PESSOA;CPF OU CNPJ DO SANCIONADO;NOME DO SANCIONADO;"
    "CATEGORIA DA SANÇÃO;DATA INÍCIO SANÇÃO;DATA FINAL SANÇÃO;ÓRGÃO SANCIONADOR;UF ÓRGÃO SANCIONADOR;"
    "FUNDAMENTAÇÃO LEGAL"
)


def _zip_cgu(linhas: list[str]) -> bytes:
    """Zip no formato da CGU: CSV em latin-1 com cabeçalho acentuado."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("20261105_CEIS.csv", "\n".join([CABECALHO_REAL, *linhas]).encode("latin-1"))
    return buffer.getvalue()


def _processar(settings, cadastro):
    conector = ConectorSancoes(settings, cadastro)
    saidas = []
    for resposta in fixtures.ler_fonte(FIXTURES / cadastro):
        for registro in conector.interpretar(resposta):
            saidas.append(conector.normalizar(registro, resposta))
    return saidas


@pytest.mark.parametrize("cadastro", ["ceis", "cnep"])
def test_fixture_real_normaliza_sancoes_de_pj(settings, cadastro):
    validos = [s.fato for s in _processar(settings, cadastro) if isinstance(s, RegistroNormalizado)]
    assert len(validos) >= 50
    assert all(isinstance(f, Sancao) and f.fonte_id == cadastro for f in validos)
    assert all(len(f.cnpj) == 14 and f.data_inicio for f in validos)
    assert len({f.id_origem for f in validos}) == len(validos)


def test_pessoa_fisica_descartada_e_data_final_vazia_aceita(settings):
    saidas = _processar(settings, "ceis")
    assert [d.motivo for d in saidas if isinstance(d, Descarte)] == ["pessoa_fisica"]
    sem_fim = next(
        s.fato for s in saidas if isinstance(s, RegistroNormalizado) and s.fato.id_origem == "9000002"
    )
    assert sem_fim.data_fim is None
    assert sem_fim.uf_orgao == "PE"


def test_le_zip_latin1_da_cgu():
    linha = "CEIS;1;J;99.000.004/0001-37;EMPRESA;Suspensão;01/01/2026;;ÓRGÃO;PE;Lei"
    cabecalho, linhas = ler_csv(_zip_cgu([linha]))
    assert "CODIGO DA SANCAO" in cabecalho
    assert next(linhas)[3] == "99.000.004/0001-37"


def test_arquivo_sem_colunas_obrigatorias_e_rejeitado():
    with pytest.raises(ArquivoInvalido):
        ler_csv(b"A;B\n1;2\n")


def test_dia_sem_arquivo_volta_para_o_dia_anterior(settings, cliente_falso):
    pedidos = []

    def rotas(req: httpx.Request) -> httpx.Response:
        pedidos.append(req.url.path.rsplit("/", 1)[-1])
        if req.url.path.endswith("20261106"):
            return httpx.Response(403, content=b"<Error>AccessDenied</Error>")
        return httpx.Response(200, content=_zip_cgu([]))

    conector = ConectorSancoes(settings, "ceis", hoje=date(2026, 11, 6))
    with cliente_falso(rotas) as cliente:
        respostas = list(conector.coletar(cliente))
    assert pedidos == ["20261106", "20261105"]
    assert respostas[0].url_origem.endswith("/ceis/20261105")


def test_sem_download_usa_arquivo_manual(settings, cliente_falso):
    manual = settings.raw_dir / "sancoes"
    manual.mkdir(parents=True)
    (manual / "20261101_CEIS.zip").write_bytes(_zip_cgu([]))
    conector = ConectorSancoes(settings, "ceis", hoje=date(2026, 11, 6))
    with cliente_falso(lambda _r: httpx.Response(403)) as cliente:
        respostas = list(conector.coletar(cliente))
    assert [r.nome for r in respostas] == ["20261101_CEIS.zip"]


def test_sem_download_e_sem_manual_explica_o_que_fazer(settings, cliente_falso):
    conector = ConectorSancoes(settings, "cnep", hoje=date(2026, 11, 6))
    with (
        cliente_falso(lambda _r: httpx.Response(403)) as cliente,
        pytest.raises(FonteIndisponivel, match="manual"),
    ):
        list(conector.coletar(cliente))


def test_amostra_guarda_so_pj_e_colunas_usadas(settings, cliente_falso):
    linhas = [
        "CEIS;1;J;99000004000137;EMPRESA;Suspensão;01/01/2026;;ÓRGÃO;PE;Lei",
        "CEIS;2;F;***.456.789-**;FULANO SINTETICO;Suspensão;01/01/2026;;ÓRGÃO;PE;Lei",
    ]
    conector = ConectorSancoes(settings, "ceis", hoje=date(2026, 11, 6))
    with cliente_falso(lambda _r: httpx.Response(200, content=_zip_cgu(linhas))) as cliente:
        amostra = conector.amostra(cliente, 10)
    texto = amostra[0].conteudo.decode()
    assert "99000004000137" in texto
    assert "FULANO" not in texto
    assert "456.789" not in texto


@pytest.mark.rede
def test_download_real(settings):
    conector = ConectorSancoes(settings, "cnep")
    with ClienteHttp("cnep", None) as cliente:
        resposta = next(conector.coletar(cliente))
    assert next(conector.interpretar(resposta))
