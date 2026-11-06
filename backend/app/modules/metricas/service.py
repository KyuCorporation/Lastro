"""GET /metricas: lê os relatórios do eval (eval/reports/*.json), gerados por make eval e make eval-ataques.

Relatório ausente ou ilegível vira nulo: a tela de métricas mostra "ainda não rodado" em vez de quebrar.
O cronômetro (T23) virá de eval/reports/cronometro.json quando existir.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

PASTAS_CANDIDATAS = (Path(__file__).resolve().parents[4] / "eval" / "reports", Path("/eval/reports"))


def pasta_relatorios() -> Path | None:
    return next((p for p in PASTAS_CANDIDATAS if p.is_dir()), None)


def _ler(pasta: Path | None, nome: str) -> dict[str, Any] | None:
    if pasta is None:
        return None
    try:
        dados = json.loads((pasta / f"{nome}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return dados if isinstance(dados, dict) else None


def _resumo(relatorio: dict[str, Any] | None) -> dict[str, Any] | None:
    if relatorio is None:
        return None
    return {
        "gerado_em": relatorio.get("gerado_em"),
        "provedor_llm": relatorio.get("provedor_llm"),
        "n_casos": relatorio.get("n_casos"),
        **(relatorio.get("metricas") or {}),
    }


def metricas(pasta: Path | None = None) -> dict[str, Any]:
    pasta = pasta if pasta is not None else pasta_relatorios()
    partes = {nome: _resumo(_ler(pasta, nome)) for nome in ("gabarito", "ataques", "cronometro")}
    datas = [p["gerado_em"] for p in partes.values() if p and isinstance(p.get("gerado_em"), str)]
    ultima = max(datas, key=lambda d: datetime.fromisoformat(d)) if datas else None
    return {
        "eval": partes["gabarito"],
        "ataques": partes["ataques"],
        "cronometro": partes["cronometro"],
        "ultima_atualizacao": ultima,
    }
