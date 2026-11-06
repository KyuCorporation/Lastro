"""JSON canônico e hash do recibo (contracts/recibo.schema.json: "sha256 do JSON canônico deste objeto,
chaves ordenadas, sem espaços, UTF-8").

O conteúdo é convertido para tipos JSON puros (`para_json`) antes de gravar, então ler o jsonb de volta e
recalcular o hash dá o mesmo valor (base do `/recibos/{id}/verificar`, T15). Dinheiro e percentual viram
string decimal; datas, ISO 8601.
"""

import hashlib
import json
import math
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID


def para_json(valor: Any) -> Any:
    """Converte para str/int/bool/None/list/dict. Recusa o que não sabe representar sem perda."""
    if valor is None or isinstance(valor, bool | int | str):
        return valor
    if isinstance(valor, float):
        # Só a confiança do plano. O repr do Python é o menor texto que volta ao mesmo float e o jsonb guarda
        # o decimal exato, então a ida e volta é estável. NaN e infinito não têm JSON.
        if not math.isfinite(valor):
            raise ValueError("float não finito no recibo")
        return valor
    if isinstance(valor, Decimal):
        return format(valor, "f")
    if isinstance(valor, datetime | date):
        return valor.isoformat()
    if isinstance(valor, UUID):
        return str(valor)
    if isinstance(valor, Enum):
        return para_json(valor.value)
    if isinstance(valor, Mapping):
        return {str(k): para_json(v) for k, v in valor.items()}
    if isinstance(valor, list | tuple | set | frozenset):
        itens = [para_json(v) for v in valor]
        return sorted(itens, key=json.dumps) if isinstance(valor, set | frozenset) else itens
    raise TypeError(f"tipo sem representação canônica no recibo: {type(valor).__name__}")


def json_canonico(conteudo: Mapping[str, Any]) -> str:
    return json.dumps(para_json(conteudo), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_recibo(conteudo: Mapping[str, Any]) -> str:
    return hashlib.sha256(json_canonico(conteudo).encode("utf-8")).hexdigest()
