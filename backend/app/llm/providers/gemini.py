import logging
import time

from google import genai
from google.genai import errors, types

from app.llm.providers.base import ProvedorIndisponivel

log = logging.getLogger("lastro.llm")

# 503 "high demand" do Google é passageiro: vale uma segunda tentativa curta antes de cair no fallback.
PAUSA_ANTES_DE_REPETIR_S = 0.8


class ProvedorGemini:
    nome = "gemini"

    def __init__(self, api_key: str, modelo: str, *, raciocinio: bool = False, cliente=None):
        self.modelo = modelo
        # Raciocínio interno desligado por padrão: o planejador só escolhe uma intent de um formulário fixo e o
        # redator só preenche marcadores. Medido em 06/11/2026 (gemini-3.6-flash): 15–21 s com raciocínio,
        # 2–3 s sem, com o mesmo plano.
        self.raciocinio = raciocinio
        self._cliente = cliente or genai.Client(api_key=api_key)

    def _config(
        self, *, json: bool, timeout_s: float, temperatura: float, sem_raciocinio: bool
    ) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            temperature=temperatura,
            response_mime_type="application/json" if json else None,
            http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
            thinking_config=types.ThinkingConfig(thinking_budget=0) if sem_raciocinio else None,
        )

    def gerar(self, prompt: str, *, json: bool = False, timeout_s: float, temperatura: float = 0.0) -> str:
        sem_raciocinio = not self.raciocinio
        repetiu_5xx = False
        while True:
            config = self._config(
                json=json, timeout_s=timeout_s, temperatura=temperatura, sem_raciocinio=sem_raciocinio
            )
            try:
                resposta = self._cliente.models.generate_content(
                    model=self.modelo, contents=prompt, config=config
                )
                break
            except errors.ServerError as exc:  # 5xx: sobrecarga ou falha passageira do Google
                if not repetiu_5xx:
                    repetiu_5xx = True
                    log.info("gemini respondeu %s; repetindo uma vez", exc.code)
                    time.sleep(PAUSA_ANTES_DE_REPETIR_S)
                    continue
                log.warning("gemini indisponível: %s %s", type(exc).__name__, exc.code)
                raise ProvedorIndisponivel(f"{type(exc).__name__} {exc.code}") from exc
            except errors.ClientError as exc:
                # Alguns modelos (ex.: gemini-3.5-flash-lite) recusam desligar o raciocínio com 400. Tenta sem a
                # configuração e, se passar, não manda mais para este modelo.
                if exc.code == 400 and sem_raciocinio:
                    log.info(
                        "modelo %s recusou desligar o raciocínio; seguindo sem a configuração", self.modelo
                    )
                    sem_raciocinio = False
                    continue
                log.warning("gemini indisponível: %s %s", type(exc).__name__, exc.code)
                raise ProvedorIndisponivel(f"{type(exc).__name__} {exc.code}") from exc
            except Exception as exc:  # rede, timeout: todos levam ao fallback
                # Não loga o prompt: ele pode conter dado de terceiros (AGENTS.md §3, regra 8).
                log.warning("gemini indisponível: %s", type(exc).__name__)
                raise ProvedorIndisponivel(type(exc).__name__) from exc
        if sem_raciocinio != (not self.raciocinio):
            self.raciocinio = True  # o modelo só aceita com raciocínio: lembra para as próximas chamadas
        if not resposta.text:
            raise ProvedorIndisponivel("resposta vazia")
        return resposta.text
