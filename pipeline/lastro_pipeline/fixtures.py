"""Fixtures versionadas em `data/fixtures/<fonte>/<conjunto>/`.

Cada conjunto tem os arquivos brutos e um `manifest.json` com a URL de origem e a hora da coleta de cada um,
para que a ingestão offline grave a mesma proveniência que a online.

Conjuntos: `amostra/` (gerado por `ingest <fonte> --amostra N`, dado real recortado) e `exemplo_manual/`
(escrito à mão, sintético, cobre casos de borda como credor pessoa física).
"""

import json
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path

from lastro_pipeline.modelos import RespostaBruta

MANIFESTO = "manifest.json"


def salvar(diretorio: Path, respostas: Iterable[RespostaBruta], descricao: str) -> Path:
    diretorio.mkdir(parents=True, exist_ok=True)
    itens = []
    for r in respostas:
        (diretorio / r.nome).write_bytes(r.conteudo)
        itens.append(
            {
                "arquivo": r.nome,
                "url_origem": r.url_origem,
                "coletado_em": r.coletado_em.isoformat(),
                "metadados": r.metadados,
            }
        )
    manifesto = {"descricao": descricao, "arquivos": itens}
    (diretorio / MANIFESTO).write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n")
    return diretorio


def conjuntos(diretorio_fonte: Path) -> list[Path]:
    """Conjuntos de uma fonte, em ordem estável. `amostra` (real) vem antes de `exemplo_manual`."""
    if not diretorio_fonte.exists():
        return []
    return sorted(p.parent for p in diretorio_fonte.glob(f"*/{MANIFESTO}"))


def ler(diretorio: Path) -> Iterator[RespostaBruta]:
    manifesto = json.loads((diretorio / MANIFESTO).read_text())
    for item in manifesto["arquivos"]:
        yield RespostaBruta(
            conteudo=(diretorio / item["arquivo"]).read_bytes(),
            url_origem=item["url_origem"],
            nome=item["arquivo"],
            coletado_em=datetime.fromisoformat(item["coletado_em"]),
            metadados=item.get("metadados", {}),
        )


def ler_fonte(diretorio_fonte: Path) -> Iterator[RespostaBruta]:
    for conjunto in conjuntos(diretorio_fonte):
        yield from ler(conjunto)
