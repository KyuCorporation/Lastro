from typer.testing import CliRunner

from lastro_pipeline.cli import app

runner = CliRunner()


def test_help_lista_os_comandos():
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    assert "ingest" in r.output
    assert "sinais" in r.output


def test_sinais_recusa_data_mal_formada():
    r = runner.invoke(app, ["sinais", "--hoje", "06/11/2026"])
    assert r.exit_code != 0
    assert "AAAA-MM-DD" in r.output
