"""CLI da pipeline: `python -m lastro_pipeline.cli --help`."""

import logging
from datetime import date, datetime

import typer

from lastro_pipeline import connectors, db, fixtures, runner
from lastro_pipeline.config import Settings, get_settings
from lastro_pipeline.connectors.base import Conector
from lastro_pipeline.http import ClienteHttp, FonteBloqueada, FonteIndisponivel
from lastro_pipeline.sinais import calculo

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


def _data(valor: str | None) -> date:
    if valor is None:
        return date.today()
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        raise typer.BadParameter("use o formato AAAA-MM-DD") from None


@app.command()
def sinais(
    hoje: str | None = typer.Option(None, help="Data de referência AAAA-MM-DD (padrão: hoje)"),
) -> None:
    """Recalcula os sinais de risco (sanção direta, penhasco, concentração) por fornecedor e UF."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    referencia = _data(hoje)
    with db.conectar(get_settings().database_url) as conn:
        resumo = calculo.recalcular(conn, referencia)
    por_tipo = ", ".join(f"{tipo} {n}" for tipo, n in resumo.por_tipo.items())
    typer.echo(
        f"sinais ({referencia.isoformat()}): {resumo.total} ({por_tipo}) | novos {resumo.novos}, "
        f"atualizados {resumo.atualizados}, apagados {resumo.apagados}"
    )
    if resumo.mantidos_por_alerta:
        typer.echo(f"{resumo.mantidos_por_alerta} sinal(is) obsoleto(s) mantido(s) por ter alerta.", err=True)


if __name__ == "__main__":
    app()
