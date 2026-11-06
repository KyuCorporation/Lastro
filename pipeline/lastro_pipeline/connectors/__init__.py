"""Registro de conectores. Fonte nova: implemente `Conector` (base.py) e acrescente uma linha aqui."""

from collections.abc import Callable

from lastro_pipeline.config import Settings
from lastro_pipeline.connectors.base import Conector
from lastro_pipeline.connectors.pe_portal import ConectorPePortal
from lastro_pipeline.connectors.pncp import ConectorPncp
from lastro_pipeline.connectors.sancoes import ConectorSancoes

# Nome aceito pela CLI → fábricas dos conectores que ele dispara (sancoes = CEIS + CNEP).
FONTES: dict[str, list[Callable[[Settings], Conector]]] = {
    "pe_portal": [ConectorPePortal],
    "pncp": [ConectorPncp],
    "sancoes": [lambda s: ConectorSancoes(s, "ceis"), lambda s: ConectorSancoes(s, "cnep")],
    "ceis": [lambda s: ConectorSancoes(s, "ceis")],
    "cnep": [lambda s: ConectorSancoes(s, "cnep")],
}
FONTES["todas"] = FONTES["pe_portal"] + FONTES["pncp"] + FONTES["sancoes"]


def conectores(fonte: str, settings: Settings) -> list[Conector]:
    if fonte not in FONTES:
        raise KeyError(fonte)
    return [fabrica(settings) for fabrica in FONTES[fonte]]
