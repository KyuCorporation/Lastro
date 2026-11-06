"""Fixtures da matriz de acesso: dados sintéticos do catálogo e o cliente da API com ambiente fixo."""

from app.modules.catalogo.tests.conftest import dados_catalogo  # noqa: F401
from app.modules.consulta.tests.conftest import api, autenticar, com_ambiente  # noqa: F401
