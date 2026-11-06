"""Relatório de qualidade de uma execução (SPEC §10, regra 3).

Mede completude, duplicidade, datas fora de faixa e descartes. Queda de volume maior que 50% em relação à
execução anterior comparável marca a execução como `parcial`. Nada é apagado.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from lastro_pipeline.modelos import Contrato, Descarte, Fato, Pagamento, Sancao

DATA_MINIMA = date(1990, 1, 1)
LIMITE_QUEDA_VOLUME = 0.5

# Campos cuja ausência torna a linha pouco útil para as consultas do catálogo.
CAMPOS_ESSENCIAIS: dict[type[Fato], tuple[str, ...]] = {
    Contrato: ("orgao_id", "objeto", "valor_global", "data_assinatura", "vigencia_fim", "url_origem"),
    Pagamento: ("orgao_id", "data_pagamento", "valor", "url_origem"),
    Sancao: ("tipo", "orgao_sancionador", "data_inicio", "url_origem"),
}

# Datas que não podem estar no futuro. Vigência pode (contrato vigente).
DATAS_PASSADAS: dict[type[Fato], tuple[str, ...]] = {
    Contrato: ("data_assinatura",),
    Pagamento: ("data_pagamento",),
    Sancao: ("data_inicio",),
}


@dataclass
class AvaliadorQualidade:
    hoje: date = field(default_factory=date.today)
    total: int = 0
    _vazios: Counter[str] = field(default_factory=Counter)
    _vistos: set[tuple[str, str]] = field(default_factory=set)
    duplicados: int = 0
    datas_fora_de_faixa: int = 0
    vigencia_invertida: int = 0
    descartes: Counter[str] = field(default_factory=Counter)

    def observar(self, fato: Fato) -> None:
        self.total += 1
        chave = (fato.tabela, fato.id_origem)
        if chave in self._vistos:
            self.duplicados += 1
        self._vistos.add(chave)
        for nome in CAMPOS_ESSENCIAIS.get(type(fato), ()):
            if getattr(fato, nome) in (None, ""):
                self._vazios[f"{fato.tabela}.{nome}"] += 1
        self._checar_datas(fato)

    def descartar(self, descarte: Descarte) -> None:
        self.descartes[descarte.motivo] += 1

    def _checar_datas(self, fato: Fato) -> None:
        limite_futuro = self.hoje + timedelta(days=1)
        for nome in DATAS_PASSADAS.get(type(fato), ()):
            valor = getattr(fato, nome)
            if valor is not None and not (DATA_MINIMA <= valor <= limite_futuro):
                self.datas_fora_de_faixa += 1
        if (
            isinstance(fato, Contrato)
            and fato.vigencia_inicio
            and fato.vigencia_fim
            and fato.vigencia_fim < fato.vigencia_inicio
        ):
            self.vigencia_invertida += 1

    def completude(self) -> dict[str, float]:
        if self.total == 0:
            return {}
        return {campo: round(1 - vazios / self.total, 4) for campo, vazios in sorted(self._vazios.items())}

    def queda_de_volume(self, lidos_agora: int, lidos_antes: int | None) -> bool:
        if not lidos_antes:
            return False
        return lidos_agora < lidos_antes * (1 - LIMITE_QUEDA_VOLUME)

    def relatorio(self, lidos_agora: int, lidos_antes: int | None) -> dict[str, Any]:
        return {
            "registros_validos": self.total,
            "completude": self.completude(),
            "duplicados": self.duplicados,
            "datas_fora_de_faixa": self.datas_fora_de_faixa,
            "vigencia_invertida": self.vigencia_invertida,
            "descartes": dict(sorted(self.descartes.items())),
            "volume_anterior": lidos_antes,
            "queda_de_volume": self.queda_de_volume(lidos_agora, lidos_antes),
        }
