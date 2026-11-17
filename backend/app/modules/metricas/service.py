"""GET /metricas: lê os relatórios do eval (eval/reports/*.json), gerados por make eval e make eval-ataques.

Relatório ausente ou ilegível vira nulo: a tela de métricas mostra "ainda não rodado" em vez de quebrar.
O cronômetro (T23) virá de eval/reports/cronometro.json quando existir.

Gabarito e ataques trazem também `por_provedor`: o resultado de cada provedor de LLM com que a avaliação rodou
(`<modo>.<provedor>.json`, gravado pelo harness), para a tela mostrar o modo sem LLM ao lado do Gemini.
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PASTAS_CANDIDATAS = (Path(__file__).resolve().parents[4] / "eval" / "reports", Path("/eval/reports"))
PROVEDOR_VALIDO = re.compile(r"[a-z0-9_-]{1,32}")


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


def _com_provedores(pasta: Path | None, modo: str) -> dict[str, Any] | None:
    """Resumo da última execução do modo, com o resultado de cada provedor em `por_provedor`."""
    principal = _resumo(_ler(pasta, modo))
    por_provedor: dict[str, dict[str, Any]] = {}
    if pasta is not None:
        for arquivo in sorted(pasta.glob(f"{modo}.*.json")):
            provedor = arquivo.name[len(modo) + 1 : -len(".json")]
            resumo = _resumo(_ler(pasta, arquivo.stem)) if PROVEDOR_VALIDO.fullmatch(provedor) else None
            if resumo is not None:
                por_provedor[provedor] = resumo
    if principal is None:
        # Só há cópias por provedor: a mais recente faz o papel do relatório principal.
        if not por_provedor:
            return None
        principal = max(por_provedor.values(), key=lambda r: _data(r.get("gerado_em")))
    provedor = principal.get("provedor_llm")
    if isinstance(provedor, str) and PROVEDOR_VALIDO.fullmatch(provedor):
        # Relatório gravado antes das cópias por provedor: conta pelo provedor que ele declara.
        por_provedor.setdefault(provedor, dict(principal))
    return {**principal, "por_provedor": por_provedor}


def _data(valor: Any) -> datetime:
    try:
        return datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=UTC)


def metricas(pasta: Path | None = None) -> dict[str, Any]:
    pasta = pasta if pasta is not None else pasta_relatorios()
    partes = {nome: _com_provedores(pasta, nome) for nome in ("gabarito", "ataques")}
    partes["cronometro"] = _resumo(_ler(pasta, "cronometro"))
    datas = [p["gerado_em"] for p in partes.values() if p and isinstance(p.get("gerado_em"), str)]
    ultima = max(datas, key=lambda d: datetime.fromisoformat(d)) if datas else None
    return {
        "eval": partes["gabarito"],
        "ataques": partes["ataques"],
        "cronometro": partes["cronometro"],
        "ultima_atualizacao": ultima,
    }
