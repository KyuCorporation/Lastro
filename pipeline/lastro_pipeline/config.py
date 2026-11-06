"""Configuração da pipeline. Tudo vem de variáveis de ambiente (.env); nenhum segredo no código."""

from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

USER_AGENT = "lastro-hackathon"


def _lista(valor: str) -> list[str]:
    return [item.strip() for item in valor.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = ""
    data_dir: Path = Path("/data")
    requests_per_second: float = 1.0

    pncp_base_url: str = "https://pncp.gov.br/api/consulta"
    pncp_ufs: str = "AL"
    pncp_pe_fallback: bool = False
    pncp_data_inicial: str = "20250101"
    pncp_data_final: str = "20261031"
    pncp_tamanho_pagina: int = 500

    tcepe_base_url: str = "https://sistemas.tcepe.tc.br/DadosAbertos"
    tcepe_anos: str = "2025,2026"
    tcepe_esferas: str = "E,M"
    tcepe_municipios: str = ""

    sancoes_download_url: str = "https://portaldatransparencia.gov.br/download-de-dados"
    sancoes_dias_retroativos: int = 7

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def fixtures_dir(self) -> Path:
        return self.data_dir / "fixtures"

    @property
    def cache_dir(self) -> Path:
        return self.raw_dir / "_cache"

    @property
    def ufs_pncp(self) -> list[str]:
        """UFs que o PNCP carrega. PE só entra com o fallback ligado (sem sobreposição com o TCE-PE)."""
        ufs = [uf.upper() for uf in _lista(self.pncp_ufs)]
        if self.pncp_pe_fallback:
            return sorted(set(ufs) | {"PE"})
        return [uf for uf in ufs if uf != "PE"]

    @property
    def periodo_pncp(self) -> tuple[date, date]:
        return (
            datetime.strptime(self.pncp_data_inicial, "%Y%m%d").date(),
            datetime.strptime(self.pncp_data_final, "%Y%m%d").date(),
        )

    @property
    def anos_tcepe(self) -> list[int]:
        return [int(ano) for ano in _lista(self.tcepe_anos)]

    @property
    def esferas_tcepe(self) -> list[str]:
        return [e.upper() for e in _lista(self.tcepe_esferas)]

    @property
    def municipios_tcepe(self) -> list[str]:
        return _lista(self.tcepe_municipios)


@lru_cache
def get_settings() -> Settings:
    return Settings()
