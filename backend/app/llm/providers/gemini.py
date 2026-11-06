import logging

from google import genai
from google.genai import types

from app.llm.providers.base import ProvedorIndisponivel

log = logging.getLogger("lastro.llm")


class ProvedorGemini:
    nome = "gemini"

    def __init__(self, api_key: str, modelo: str):
        self.modelo = modelo
        self._cliente = genai.Client(api_key=api_key)

    def gerar(self, prompt: str, *, json: bool = False, timeout_s: float, temperatura: float = 0.0) -> str:
        config = types.GenerateContentConfig(
            temperature=temperatura,
            response_mime_type="application/json" if json else None,
            http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
        )
        try:
            resposta = self._cliente.models.generate_content(
                model=self.modelo, contents=prompt, config=config
            )
        except Exception as exc:  # erro de rede, cota, timeout ou da API: todos levam ao fallback
            # Não loga o prompt: ele pode conter dado de terceiros (AGENTS.md §3, regra 8).
            log.warning("gemini indisponível: %s", type(exc).__name__)
            raise ProvedorIndisponivel(type(exc).__name__) from exc
        if not resposta.text:
            raise ProvedorIndisponivel("resposta vazia")
        return resposta.text
