"""Limite de requisições por chave numa janela deslizante (contracts/api.md: 30 consultas por minuto).

Em memória, por processo: basta para a API única do Compose. Com mais réplicas, trocar por um contador
compartilhado mantendo a mesma interface (`permitir`).
"""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable, Hashable


class LimitadorJanela:
    def __init__(self, maximo: int, janela_s: float, relogio: Callable[[], float] = time.monotonic) -> None:
        if maximo < 1 or janela_s <= 0:
            raise ValueError("limite e janela precisam ser positivos")
        self.maximo, self.janela_s = maximo, janela_s
        self._relogio = relogio
        self._eventos: dict[Hashable, deque[float]] = defaultdict(deque)
        self._trava = threading.Lock()

    def permitir(self, chave: Hashable) -> bool:
        """Conta a tentativa e diz se ela cabe no limite. Tentativa recusada não ocupa vaga."""
        agora = self._relogio()
        with self._trava:
            eventos = self._eventos[chave]
            while eventos and agora - eventos[0] >= self.janela_s:
                eventos.popleft()
            if len(eventos) >= self.maximo:
                return False
            eventos.append(agora)
            return True

    def limpar(self) -> None:
        with self._trava:
            self._eventos.clear()
