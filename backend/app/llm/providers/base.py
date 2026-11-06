from typing import Protocol


class ProvedorIndisponivel(Exception):
    """Falha de rede, timeout, cota ou resposta vazia. Quem chama cai no caminho sem LLM."""


class ProvedorLLM(Protocol):
    nome: str
    modelo: str

    def gerar(
        self, prompt: str, *, json: bool = False, timeout_s: float, temperatura: float = 0.0
    ) -> str: ...
