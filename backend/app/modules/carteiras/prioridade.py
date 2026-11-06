"""Prioridade na fila (SPEC §9): peso da gravidade × log10(1 + valor exposto).

Pesos: forte = 10, atenção = 3, info = 1; com vários sinais, os pesos somam. O valor exposto é o valor vigente
do fornecedor nas UFs do usuário.

Ajuste deliberado: o fator de exposição tem piso 1. Pela fórmula pura, um fornecedor sancionado sem contrato
vigente nas UFs do usuário (caso típico de homologação) teria prioridade 0 e iria para o fim da fila, atrás de
qualquer sinal de atenção. Com o piso, a fórmula do SPEC vale exatamente a partir de R$ 9,00 de exposição
(log10(10) = 1), e abaixo disso o peso do sinal decide sozinho.
"""

import math
from collections.abc import Iterable
from decimal import Decimal

PESOS = {"forte": 10, "atencao": 3, "info": 1}
REGRA = "soma dos pesos (forte 10, atenção 3, info 1) × max(1, log10(1 + valor exposto))"


def fator_exposicao(valor_exposto: Decimal) -> float:
    return max(1.0, math.log10(1 + max(float(valor_exposto), 0.0)))


def prioridade(gravidades: Iterable[str], valor_exposto: Decimal) -> float:
    peso = sum(PESOS.get(g, 0) for g in gravidades)
    if peso == 0:
        return 0.0
    return round(peso * fator_exposicao(valor_exposto), 4)
