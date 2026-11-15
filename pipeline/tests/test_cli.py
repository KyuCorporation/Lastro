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


def test_manifesto_da_fixture_e_utf8_em_qualquer_sistema(tmp_path):
    """No Windows, `write_text` sem codificação gravava cp1252 e o contêiner Linux não lia o manifesto."""
    from lastro_pipeline import fixtures

    fixtures.salvar(tmp_path, [], "Amostra real de até 200 linhas")
    assert "até".encode() in (tmp_path / fixtures.MANIFESTO).read_bytes()
    assert b"\r\n" not in (tmp_path / fixtures.MANIFESTO).read_bytes()
    assert list(fixtures.ler(tmp_path)) == []
