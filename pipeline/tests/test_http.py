import httpx
import pytest

from lastro_pipeline.http import FonteBloqueada, FonteIndisponivel, LimitadorTaxa, montar_url


def test_limitador_respeita_intervalo_minimo():
    relogio = [0.0]
    esperas: list[float] = []

    def dormir(segundos: float) -> None:
        esperas.append(segundos)
        relogio[0] += segundos

    limitador = LimitadorTaxa(1.0, relogio=lambda: relogio[0], dormir=dormir)
    limitador.aguardar()
    relogio[0] += 0.3
    limitador.aguardar()
    limitador.aguardar()
    assert esperas == pytest.approx([0.7, 1.0])


def test_envia_user_agent_sem_email(cliente_falso):
    vistos = []

    def rotas(req: httpx.Request) -> httpx.Response:
        vistos.append(req.headers["User-Agent"])
        return httpx.Response(200, content=b"ok")

    with cliente_falso(rotas) as cliente:
        cliente.get("https://exemplo.test/a")
    assert vistos == ["lastro-hackathon"]


def test_retry_em_404_intermitente(cliente_falso):
    respostas = iter([httpx.Response(404), httpx.Response(503), httpx.Response(200, content=b"dado")])
    with cliente_falso(lambda _req: next(respostas)) as cliente:
        assert cliente.get("https://exemplo.test/a").conteudo == b"dado"


def test_desiste_depois_das_tentativas(cliente_falso):
    with cliente_falso(lambda _req: httpx.Response(503)) as cliente, pytest.raises(FonteIndisponivel):
        cliente.get("https://exemplo.test/a")


def test_bloqueio_nao_e_contornado(cliente_falso):
    chamadas = []

    def rotas(req: httpx.Request) -> httpx.Response:
        chamadas.append(req)
        return httpx.Response(403)

    with cliente_falso(rotas) as cliente, pytest.raises(FonteBloqueada):
        cliente.get("https://exemplo.test/a")
    assert len(chamadas) == 1


def test_status_aceito_pelo_conector(cliente_falso):
    with cliente_falso(lambda _req: httpx.Response(204)) as cliente:
        assert cliente.get("https://exemplo.test/a", aceitar=frozenset({200, 204})).status == 204


def test_cache_em_disco_evita_segunda_requisicao(cliente_falso, tmp_path):
    chamadas = []

    def rotas(req: httpx.Request) -> httpx.Response:
        chamadas.append(req)
        return httpx.Response(200, content=b"dado")

    with cliente_falso(rotas, tmp_path) as cliente:
        primeira = cliente.get("https://exemplo.test/a")
    with cliente_falso(rotas, tmp_path) as cliente:
        segunda = cliente.get("https://exemplo.test/a")
    assert len(chamadas) == 1
    assert segunda.do_cache and segunda.conteudo == primeira.conteudo


def test_resposta_que_nao_e_200_nao_vai_para_o_cache(cliente_falso, tmp_path):
    chamadas = []

    def rotas(req: httpx.Request) -> httpx.Response:
        chamadas.append(req)
        return httpx.Response(204)

    for _ in range(2):
        with cliente_falso(rotas, tmp_path) as cliente:
            cliente.get("https://exemplo.test/a", aceitar=frozenset({204}))
    assert len(chamadas) == 2


def test_montar_url_ignora_parametro_vazio():
    assert montar_url("https://x.test/", "/Contratos!json", {"Ano": 2025, "Mun": None}) == (
        "https://x.test/Contratos!json?Ano=2025"
    )
