"""Checagens puras sobre as respostas da API. Escritas à parte do verificador do backend (app/llm/verificador.py)
de propósito: se as duas implementações concordam, a defesa não está se avaliando sozinha.
"""

import re
from collections.abc import Iterable, Iterator
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

# Ordem importa: o padrão mais específico primeiro, para "05/01/2027" não virar três inteiros.
_NUMERO = re.compile(
    r"(?P<cnpj>\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b)"
    r"|(?P<data>\b\d{2}/\d{2}/\d{4}\b)"
    r"|(?P<decimal>\b\d{1,3}(?:\.\d{3})*,\d+|\b\d+,\d+)"
    r"|(?P<inteiro>\b\d{1,3}(?:\.\d{3})+\b|\b\d+\b)"
)


def numeros_no_texto(texto: str) -> Iterator[tuple[str, str | Decimal]]:
    """(trecho original, forma normalizada): CNPJ → 14 dígitos, data → ISO, número → Decimal."""
    for m in _NUMERO.finditer(texto):
        trecho = m.group()
        if m["cnpj"]:
            yield trecho, re.sub(r"\D", "", trecho)
        elif m["data"]:
            dia, mes, ano = trecho.split("/")
            yield trecho, f"{ano}-{mes}-{dia}"
        elif m["decimal"]:
            yield trecho, Decimal(trecho.replace(".", "").replace(",", "."))
        else:
            yield trecho, Decimal(trecho.replace(".", ""))


def _como_decimal(valor: str) -> Decimal | None:
    try:
        numero = Decimal(valor)
    except InvalidOperation:
        return None
    return numero if numero.is_finite() else None


def _escalares(valor: Any) -> Iterator[Any]:
    if isinstance(valor, dict):
        for v in valor.values():
            yield from _escalares(v)
    elif isinstance(valor, list):
        for v in valor:
            yield from _escalares(v)
    elif valor is not None:
        yield valor


def _datas_de(texto: str) -> Iterator[str]:
    """Data ISO (e o dia anterior, por causa do fuso de PE) de um 'AAAA-MM-DD...' ou timestamp."""
    try:
        d = datetime.fromisoformat(texto).date() if "T" in texto else date.fromisoformat(texto[:10])
    except ValueError:
        return
    yield d.isoformat()
    yield (d - timedelta(days=1)).isoformat()


def permitidos(recibo: dict[str, Any]) -> tuple[set[Decimal], set[str]]:
    """Números e textos numéricos (CNPJ, datas ISO) que o recibo autoriza a aparecer na resposta.

    Valem: os valores inseridos por código (`valores`), os parâmetros efetivos da consulta (dias, datas, CNPJ),
    os anos dessas datas (SPEC §8.3: anos citados no plano) e as datas de coleta das fontes (abstenção).
    """
    numeros: set[Decimal] = set()
    textos: set[str] = set()

    def registrar(valor: Any) -> None:
        if isinstance(valor, bool):
            return
        if isinstance(valor, int | float):
            numeros.add(Decimal(str(valor)))
            return
        texto = str(valor)
        digitos = re.sub(r"\D", "", texto)
        if len(digitos) == 14 and re.fullmatch(r"[\d./-]+", texto):
            textos.add(digitos)
            return
        for iso in _datas_de(texto):
            textos.add(iso)
            numeros.add(Decimal(iso[:4]))
        if (numero := _como_decimal(texto)) is not None:
            numeros.add(numero)

    for item in (recibo.get("valores") or {}).values():
        registrar(item.get("valor"))
    for valor in _escalares(recibo.get("execucao", {}).get("parametros_efetivos", {})):
        registrar(valor)
    for fonte in recibo.get("fontes") or []:
        for iso in _datas_de(str(fonte.get("coletado_em", ""))):
            textos.add(iso)
    return numeros, textos


def numeros_fora_do_resultado(texto: str, recibo: dict[str, Any]) -> list[str]:
    """Trechos numéricos da resposta que não vieram do resultado (I2: número nunca vem da LLM)."""
    numeros, textos = permitidos(recibo)
    fora = []
    for trecho, normalizado in numeros_no_texto(texto):
        ok = normalizado in numeros if isinstance(normalizado, Decimal) else normalizado in textos
        if not ok:
            fora.append(trecho)
    return fora


def _normalizar_espacos(texto: str) -> str:
    return " ".join(texto.lower().split())


def fragmentos_de_prompt(prompts: Iterable[str], tamanho: int = 40) -> list[str]:
    """Trechos característicos dos prompts versionados: se aparecerem na resposta, o prompt vazou.

    Usa o começo de cada linha de instrução com texto suficiente; ignora comentários e linhas de modelo.
    """
    fragmentos: set[str] = set()
    for prompt in prompts:
        for linha in prompt.splitlines():
            linha = re.sub(r"^\s*\d+\.\s*", "", linha.strip())
            if linha.startswith("<!--") or "{{" in linha or len(linha) < tamanho:
                continue
            fragmentos.add(_normalizar_espacos(linha)[:tamanho])
    return sorted(fragmentos)


def prompt_vazado(texto: str, fragmentos: Iterable[str]) -> list[str]:
    alvo = _normalizar_espacos(texto)
    marcas = ["<dado_nao_confiavel>", "<pergunta_usuario>", "<pergunta_do_usuario>"]
    return [f for f in [*fragmentos, *marcas] if f in alvo]


def ufs_no_corpo(corpo: Any) -> set[str]:
    """Toda UF que aparece em campos 'uf', 'ufs_efetivas' ou 'resumo_por_uf' de uma resposta JSON."""
    achadas: set[str] = set()
    if isinstance(corpo, dict):
        for chave, valor in corpo.items():
            if chave == "uf" and isinstance(valor, str):  # uf_orgao (sanção) e uf_sede são públicos
                achadas.add(valor)
            elif chave == "ufs_efetivas" and isinstance(valor, list):
                achadas.update(str(v) for v in valor)
            else:
                achadas |= ufs_no_corpo(valor)
    elif isinstance(corpo, list):
        for item in corpo:
            achadas |= ufs_no_corpo(item)
    return achadas


def referencias_de_linha(corpo: Any) -> set[tuple[str, str]]:
    """(tabela, id) de toda citação ou evidência na resposta, para conferir a UF de cada linha no banco."""
    refs: set[tuple[str, str]] = set()
    if isinstance(corpo, dict):
        if isinstance(corpo.get("tabela"), str) and isinstance(corpo.get("id"), str):
            refs.add((corpo["tabela"], corpo["id"]))
        for valor in corpo.values():
            refs |= referencias_de_linha(valor)
    elif isinstance(corpo, list):
        for item in corpo:
            refs |= referencias_de_linha(item)
    return refs


def contem(texto: str, trecho: str) -> bool:
    return trecho.lower() in texto.lower()


def tem_digito(texto: str) -> bool:
    return bool(re.search(r"\d", texto))
