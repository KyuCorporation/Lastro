"""Validador do contrato contracts/recibo.schema.json (com o $ref para plano_consulta.schema.json)."""

import json
from functools import cache

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from app.conftest import arquivo_do_repo


@cache
def validador() -> Draft202012Validator:
    recibo = json.loads(arquivo_do_repo("contracts/recibo.schema.json").read_text(encoding="utf-8"))
    plano = json.loads(arquivo_do_repo("contracts/plano_consulta.schema.json").read_text(encoding="utf-8"))
    # O $ref "plano_consulta.schema.json" é relativo ao $id do recibo ("lastro/recibo.v1").
    base = recibo["$id"].rsplit("/", 1)[0]
    registro = Registry().with_resources(
        [
            (recibo["$id"], Resource.from_contents(recibo)),
            (f"{base}/plano_consulta.schema.json", Resource.from_contents(plano)),
        ]
    )
    return Draft202012Validator(recibo, registry=registro, format_checker=Draft202012Validator.FORMAT_CHECKER)


def erros(conteudo: dict) -> list[str]:
    return [f"{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in validador().iter_errors(conteudo)]
