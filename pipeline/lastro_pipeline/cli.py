"""CLI da pipeline: `python -m lastro_pipeline.cli --help`."""

import logging

import typer

from lastro_pipeline import connectors, db, fixtures, runner
from lastro_pipeline.config import Settings, get_settings
from lastro_pipeline.connectors.base import Conector
from lastro_pipeline.http import ClienteHttp, FonteBloqueada, FonteIndisponivel

app = typer.Typer(help="Ingestão, qualidade e sinais do Lastro.", no_args_is_help=True)

AJUDA_FONTE = "pe_portal, pncp, sancoes (ceis + cnep), ceis, cnep ou todas"


def _cliente(conector: Conector, settings: Settings) -> ClienteHttp:
    return ClienteHttp(conector.fonte_id, settings.cache_dir, settings.requests_per_second)


def _gravar_amostra(conector: Conector, settings: Settings, linhas: int) -> None:
    with _cliente(conector, settings) as cliente:
        respostas = conector.amostra(cliente, linhas)
    destino = settings.fixtures_dir / conector.fonte_id / "amostra"
    fixtures.salvar(destino, respostas, f"Amostra real de até {linhas} linhas de PJ, gerada por --amostra")
    typer.echo(f"{conector.fonte_id}: amostra gravada em {destino}")


def _ingerir(conector: Conector, settings: Settings, offline: bool) -> runner.ResumoExecucao:
    with db.conectar(settings.database_url) as conn:
        if offline:
            respostas = fixtures.ler_fonte(settings.fixtures_dir / conector.fonte_id)
            return runner.executar(conn, conector, respostas, "offline", raw_dir=None)
        with _cliente(conector, settings) as cliente:
            return runner.executar(conn, conector, conector.coletar(cliente), "online", settings.raw_dir)


@app.command()
def ingest(
    fonte: str = typer.Argument(..., help=AJUDA_FONTE),
    offline: bool = typer.Option(False, help="Usa só data/fixtures, sem rede"),
    amostra: int | None = typer.Option(None, help="Grava uma fixture com N linhas (não grava no banco)"),
) -> None:
    """Coleta uma fonte e grava bronze e tabelas normalizadas."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    try:
        selecionados = connectors.conectores(fonte, settings)
    except KeyError:
        typer.echo(f"Fonte desconhecida: {fonte}. Use {AJUDA_FONTE}.", err=True)
        raise typer.Exit(code=2) from None

    falhas = 0
    for conector in selecionados:
        try:
            if amostra is not None:
                _gravar_amostra(conector, settings, amostra)
                continue
            resumo = _ingerir(conector, settings, offline)
            c = resumo.contagem
            typer.echo(
                f"{resumo.fonte_id}: {resumo.status} | lidos {c.lidos}, novos {c.novos}, "
                f"atualizados {c.atualizados}, descartados {c.descartados}"
            )
        except (FonteIndisponivel, FonteBloqueada) as erro:
            falhas += 1
            typer.echo(
                f"{conector.fonte_id}: fonte fora ou bloqueada ({erro}). Use --offline ou o download manual.",
                err=True,
            )
    if falhas:
        raise typer.Exit(code=1)


@app.command()
def sinais() -> None:
    """Recalcula os sinais de risco por fornecedor e UF."""
    typer.echo("'sinais' ainda não implementado.", err=True)
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
