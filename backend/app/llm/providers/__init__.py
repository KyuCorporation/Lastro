"""Escolha do provedor de LLM por `LLM_PROVIDER`.

`mock` (padrão) não usa rede: o planejador cai direto no roteador por regras. `gemini` sem chave também cai
no mock, com aviso no log.
"""

import logging

from app.core.config import Settings
from app.llm.providers.base import ProvedorIndisponivel, ProvedorLLM

log = logging.getLogger("lastro.llm")

# Conferido em 06/11/2026: o gemini-2.5-flash não aceita mais contas novas (404). Troque por LLM_MODEL no .env.
MODELO_GEMINI_PADRAO = "gemini-3.6-flash"

__all__ = ["ProvedorIndisponivel", "ProvedorLLM", "obter_provedor"]


def obter_provedor(settings: Settings) -> ProvedorLLM | None:
    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            log.warning("LLM_PROVIDER=gemini sem GEMINI_API_KEY; usando o modo mock")
            return None
        from app.llm.providers.gemini import ProvedorGemini

        return ProvedorGemini(
            settings.gemini_api_key,
            settings.llm_model or MODELO_GEMINI_PADRAO,
            raciocinio=settings.llm_raciocinio,
        )
    return None
