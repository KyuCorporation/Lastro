"""Data de referência da pipeline: o dia em Pernambuco, como na API (o container roda em UTC)."""

from datetime import UTC, date, datetime
from pathlib import Path

from lastro_pipeline.config import hoje_recife

PACOTE = Path(__file__).resolve().parents[1] / "lastro_pipeline"


def test_madrugada_em_utc_ainda_e_o_dia_anterior_em_recife():
    assert hoje_recife(datetime(2026, 11, 17, 1, 30, tzinfo=UTC)) == date(2026, 11, 16)
    assert hoje_recife(datetime(2026, 11, 17, 3, 0, tzinfo=UTC)) == date(2026, 11, 17)


def test_nenhum_modulo_usa_a_data_do_servidor():
    usos = [
        f"{p.relative_to(PACOTE)}:{n}"
        for p in PACOTE.rglob("*.py")
        for n, linha in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if "date.today" in linha
    ]
    assert usos == []
