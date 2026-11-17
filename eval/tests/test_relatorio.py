"""Relatórios do eval: cada execução grava o arquivo do modo e uma cópia por provedor de LLM."""

import json

from lastro_eval.relatorio import escrever_json

METRICAS = {"n_casos": 2, "bloqueados": 2, "vazamentos": 0}


def test_grava_o_relatorio_do_modo_e_a_copia_do_provedor(tmp_path):
    escrever_json(tmp_path, "ataques", "gemini", METRICAS, [])
    principal = json.loads((tmp_path / "ataques.json").read_text(encoding="utf-8"))
    copia = json.loads((tmp_path / "ataques.gemini.json").read_text(encoding="utf-8"))
    assert principal == copia
    assert principal["provedor_llm"] == "gemini"


def test_execucao_com_outro_provedor_nao_apaga_a_anterior(tmp_path):
    escrever_json(tmp_path, "gabarito", "gemini", METRICAS, [])
    escrever_json(tmp_path, "gabarito", "mock", METRICAS, [])
    assert json.loads((tmp_path / "gabarito.json").read_text(encoding="utf-8"))["provedor_llm"] == "mock"
    assert (
        json.loads((tmp_path / "gabarito.gemini.json").read_text(encoding="utf-8"))["provedor_llm"]
        == "gemini"
    )
    assert (tmp_path / "gabarito.mock.json").exists()


def test_nome_de_provedor_estranho_nao_vira_caminho(tmp_path):
    escrever_json(tmp_path, "ataques", "../fora", METRICAS, [])
    assert (tmp_path / "ataques.json").exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["ataques.json"]
