"""Configuração da API. Tudo vem de variáveis de ambiente (.env); nenhum segredo no código."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    cors_origin: str = "http://localhost:5173"
    llm_provider: str = "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
