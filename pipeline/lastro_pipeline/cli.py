"""CLI da pipeline: `python -m lastro_pipeline.cli --help`."""

import typer

app = typer.Typer(help="Ingestão, qualidade e sinais do Lastro.", no_args_is_help=True)


def _nao_implementado(comando: str) -> None:
    typer.echo(f"'{comando}' ainda não implementado.", err=True)
    raise typer.Exit(code=1)


@app.command()
def ingest(
    fonte: str = typer.Argument(..., help="pe_portal, pncp, sancoes, qsa ou todas"),
    offline: bool = typer.Option(False, help="Usa só data/fixtures, sem rede"),
    amostra: int | None = typer.Option(None, help="Grava uma fixture com N linhas"),
) -> None:
    """Coleta uma fonte e grava bronze e tabelas normalizadas."""
    _nao_implementado(f"ingest {fonte}")


@app.command()
def sinais() -> None:
    """Recalcula os sinais de risco por fornecedor e UF."""
    _nao_implementado("sinais")


if __name__ == "__main__":
    app()
