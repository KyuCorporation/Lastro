"""Configuração da API. Tudo vem de variáveis de ambiente (.env); nenhum segredo no código."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_exp_minutes: int = 480
    cors_origin: str = "http://localhost:5173"
    llm_provider: str = "mock"
    llm_model: str = ""
    gemini_api_key: str = ""
    llm_timeout_seconds: float = 20.0
    # Teto de tempo das chamadas à LLM numa consulta (planejador + redator). Esgotado, a resposta sai pelo
    # roteador por regras e pelo modelo determinístico (SPEC §14.6: P95 abaixo de 10 s com LLM).
    llm_orcamento_segundos: float = 12.0
    # Raciocínio interno do modelo (Gemini 2.5+). Desligado: mesma resposta, de 5 a 8 vezes mais rápido.
    llm_raciocinio: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
