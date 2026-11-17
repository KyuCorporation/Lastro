"""Conector TCE-PE Dados Abertos (`pe_portal`, SPEC §10). Obrigatório (R1).

A API só responde a IP brasileiro: agente de nuvem usa `--offline` (fixtures) e nunca tenta contornar.
Formato conferido na API real em 15/11/2026 (docs/catalogo-fontes.md).

Volume. A API não pagina: devolve tudo de uma vez e corta em silêncio em `limiteResultado` (100 mil). Por isso a
coleta é fatiada em recortes pequenos, cada um uma URL com cache próprio:
- contratos: ano do contrato × esfera, desde `TCEPE_CONTRATOS_ANO_INICIAL` (contrato antigo pode estar vigente);
- despesas do estado: exercício × unidade gestora; liquidações só das UGs que tiveram empenho;
- despesas dos municípios de `TCEPE_MUNICIPIOS`: exercício × mês; liquidações por UG vista nas despesas.
Recorte de exercício encerrado fica em cache por `TCEPE_CACHE_DIAS`; o do exercício corrente, só no dia. Recorte
que bate no limite falha (`RecorteTruncado`) em vez de gravar dado cortado.

LGPD. Toda resposta passa por `normalize.pe_portal.sanear` antes de ir para o cache e para o bronze: registro de
pessoa física vira marcador, e o CPF (que a API manda inteiro) nunca é gravado em disco.

A liquidação não traz o credor. O conector guarda, por empenho de PJ já normalizado, o CNPJ e o órgão, e a
liquidação os busca pela chave do empenho. Por isso as despesas vêm sempre antes das liquidações.
"""

import json
from collections import Counter
from collections.abc import Iterator
from dataclasses import replace
from datetime import date
from functools import partial
from itertools import product
from typing import Any

from lastro_pipeline.config import Settings, hoje_recife
from lastro_pipeline.connectors.base import RegistroOrigem
from lastro_pipeline.http import ClienteHttp, FonteIndisponivel, montar_url
from lastro_pipeline.modelos import Normalizacao, RegistroNormalizado, RespostaBruta
from lastro_pipeline.normalize import pe_portal as mapa
from lastro_pipeline.normalize.cnpj import classificar
from lastro_pipeline.normalize.valores import campo, lista_de_registros

CONTRATOS = "Contratos!json"
DESPESAS_ESTADUAIS = "DespesasEstaduais!json"
DESPESAS_MUNICIPAIS = "DespesasMunicipais!json"
LIQUIDACOES = "EmpenhoLiquidacao!json"
UGS_ESTADUAIS = "UnidadesJurisdicionadasEstaduais!json"
MUNICIPIOS = "Municipios!json"

Coletado = tuple[RespostaBruta, list[RegistroOrigem]]


class RecorteTruncado(FonteIndisponivel):
    """A resposta bateu no limite de registros da API: o recorte precisa ser menor."""


class ConectorPePortal:
    fonte_id = mapa.FONTE_ID

    def __init__(self, settings: Settings, hoje: date | None = None) -> None:
        self._base = settings.tcepe_base_url
        self._anos = settings.anos_tcepe
        self._anos_contratos = settings.anos_contratos_tcepe
        self._esferas = settings.esferas_tcepe
        self._municipios = settings.municipios_tcepe
        self._ugs_estaduais = settings.ugs_estaduais_tcepe
        self._cache_dias = settings.tcepe_cache_dias
        self._hoje = hoje or hoje_recife()
        # chave do empenho (`<UG>:<exercício>:<empenho>`) → (CNPJ do credor, órgão)
        self._credores: dict[str, tuple[str, str | None]] = {}

    def filtros(self) -> dict[str, Any]:
        return {
            "anos": self._anos,
            "contratos_desde": self._anos_contratos[0],
            "esferas": self._esferas,
            "municipios": self._municipios,
            "ugs_estaduais": self._ugs_estaduais,
        }

    # ------------------------------------------------------------------ coleta
    def coletar(self, cliente: ClienteHttp) -> Iterator[RespostaBruta]:
        for resposta, registros in self._coletar(cliente, amostra=False):
            if registros:  # recorte vazio não vira arquivo no bronze
                yield resposta

    def _coletar(self, cliente: ClienteHttp, amostra: bool) -> Iterator[Coletado]:
        """`amostra=True` reduz o plano a um recorte de cada tipo e esfera (poucas requisições)."""
        anos = [a for a in self._anos if a <= self._hoje.year]
        anos_contratos = [a for a in self._anos_contratos if a <= self._hoje.year]
        if amostra:
            anos, anos_contratos = anos[-1:], anos_contratos[-1:]
        municipios = self._resolver_municipios(cliente) if "M" in self._esferas else []
        if amostra:
            municipios = municipios[:1]

        for ano, esfera in product(anos_contratos, self._esferas):
            params: dict[str, Any] = {"AnoContrato": ano, "Esfera": esfera}
            if amostra and esfera == "M" and municipios:
                params["Municipio"] = municipios[0][0]
            yield self._buscar(
                cliente, "contrato", CONTRATOS, params, ano, esfera, f"contrato_{ano}_{esfera}"
            )

        for ano in anos:
            if "E" in self._esferas:
                yield from self._despesas_estaduais(cliente, ano, amostra)
            for nome, codigo in municipios:
                yield from self._despesas_municipais(cliente, ano, nome, codigo, amostra)

    def _despesas_estaduais(self, cliente: ClienteHttp, ano: int, amostra: bool) -> Iterator[Coletado]:
        for ug in self._ugs_estaduais or self._listar_ugs_estaduais(cliente):
            params = {"ANOREFERENCIA": ano, "ID_UNIDADE_GESTORA": ug}
            despesas = self._buscar(
                cliente, "empenho", DESPESAS_ESTADUAIS, params, ano, "E", f"empenho_{ano}_E_ug{ug}"
            )
            yield despesas
            if not _tem_pj(despesas[1]):
                continue  # sem empenho de PJ não há liquidação aproveitável: poupa uma requisição
            yield self._buscar(
                cliente,
                "liquidacao",
                LIQUIDACOES,
                {**params, "ESFERA": "E"},
                ano,
                "E",
                f"liquidacao_{ano}_E_ug{ug}",
            )
            self._credores.clear()  # as liquidações desta UG já foram normalizadas
            if amostra:
                return

    def _despesas_municipais(
        self, cliente: ClienteHttp, ano: int, nome: str, codigo: str, amostra: bool
    ) -> Iterator[Coletado]:
        ultimo_mes = self._hoje.month if ano == self._hoje.year else 12
        ugs: Counter[str] = Counter()
        for mes in range(1, 2 if amostra else ultimo_mes + 1):
            params = {"CODIGO_MUNICIPIO": codigo, "ANOREFERENCIA": ano, "MESREFERENCIA": mes}
            arquivo = f"empenho_{ano}_M_{codigo}_m{mes:02d}"
            despesas = self._buscar(cliente, "empenho", DESPESAS_MUNICIPAIS, params, ano, "M", arquivo)
            ugs.update(str(r["ID_UNIDADE_GESTORA"]) for r in despesas[1] if r.get("ID_UNIDADE_GESTORA"))
            yield despesas
        escolhidas = [ug for ug, _ in ugs.most_common(1)] if amostra else sorted(ugs)
        for ug in escolhidas:
            params = {"ANOREFERENCIA": ano, "ESFERA": "M", "ID_UNIDADE_GESTORA": ug}
            yield self._buscar(
                cliente, "liquidacao", LIQUIDACOES, params, ano, "M", f"liquidacao_{ano}_M_ug{ug}"
            )
        self._credores.clear()

    def _buscar(
        self,
        cliente: ClienteHttp,
        tipo: mapa.Tipo,
        caminho: str,
        params: dict[str, Any],
        ano: int,
        esfera: str,
        arquivo: str,
    ) -> Coletado:
        url = montar_url(self._base, caminho, params)
        r = cliente.get(url, validade_dias=self._validade(ano), tratar=partial(mapa.sanear, tipo=tipo))
        dados = json.loads(mapa.decodificar(r.conteudo))
        _conferir(dados, url)
        resposta = RespostaBruta(
            conteudo=r.conteudo,
            url_origem=url,
            nome=f"{arquivo}.json",
            coletado_em=r.coletado_em,
            metadados={"tipo": tipo, "esfera": esfera},
        )
        return resposta, lista_de_registros(dados, mapa.ENVELOPES)

    def _validade(self, ano: int) -> int:
        return self._cache_dias if ano < self._hoje.year else 1

    def _lista_auxiliar(
        self, cliente: ClienteHttp, caminho: str, params: dict[str, Any]
    ) -> list[RegistroOrigem]:
        """Tabelas de apoio da API (unidades gestoras, municípios): sem dado pessoal, mudam pouco."""
        url = montar_url(self._base, caminho, params)
        dados = json.loads(mapa.decodificar(cliente.get(url, validade_dias=self._cache_dias).conteudo))
        _conferir(dados, url)
        return lista_de_registros(dados, mapa.ENVELOPES)

    def _listar_ugs_estaduais(self, cliente: ClienteHttp) -> list[str]:
        registros = self._lista_auxiliar(cliente, UGS_ESTADUAIS, {})
        return sorted({str(r["ID_UNIDADEGESTORA"]).strip() for r in registros if r.get("ID_UNIDADEGESTORA")})

    def _resolver_municipios(self, cliente: ClienteHttp) -> list[tuple[str, str]]:
        """Nomes de `TCEPE_MUNICIPIOS` → (nome como a API escreve, código do município no TCE)."""
        if not self._municipios:
            return []
        registros = self._lista_auxiliar(cliente, MUNICIPIOS, {"UNIDADEFEDERATIVA": "PE"})
        por_nome = {
            str(r["MUNICIPIO"]).strip().casefold(): (str(r["MUNICIPIO"]).strip(), str(r["CODIGO"]).strip())
            for r in registros
            if str(r.get("UNIDADEFEDERATIVA", "")).strip() == "PE"
        }
        faltando = [m for m in self._municipios if m.casefold() not in por_nome]
        if faltando:
            raise ValueError(f"TCEPE_MUNICIPIOS: município não encontrado na lista do TCE-PE: {faltando}")
        return [por_nome[m.casefold()] for m in self._municipios]

    # ------------------------------------------------------------------ interpretação e normalização
    def interpretar(self, resposta: RespostaBruta) -> Iterator[RegistroOrigem]:
        yield from lista_de_registros(json.loads(mapa.decodificar(resposta.conteudo)), mapa.ENVELOPES)

    def normalizar(self, registro: RegistroOrigem, resposta: RespostaBruta) -> Normalizacao:
        tipo = resposta.metadados["tipo"]
        credor = self._credores.get(mapa.chave_empenho(registro) or "") if tipo == "liquidacao" else None
        normalizado = mapa.normalizar(
            registro, tipo, resposta.url_origem, resposta.metadados.get("esfera"), credor
        )
        if tipo == "empenho" and isinstance(normalizado, RegistroNormalizado):
            fato = normalizado.fato
            self._credores[fato.id_origem.removeprefix("emp:")] = (fato.fornecedor_cnpj, fato.orgao_id)
        return normalizado

    # ------------------------------------------------------------------ amostra
    def amostra(self, cliente: ClienteHttp, linhas: int) -> list[RespostaBruta]:
        """Até `linhas` registros de PJ, só com os campos usados, divididos entre tipos e esferas.

        Liquidação só entra se o empenho dela também entrou (senão ficaria sem credor na ingestão offline).
        """
        por_recorte = max(1, linhas // 6)  # contrato, empenho e liquidação × estado e município
        empenhos: set[str] = set()
        amostras = []
        for resposta, registros in self._coletar(cliente, amostra=True):
            tipo = resposta.metadados["tipo"]
            if tipo == "liquidacao":
                escolhidos = [r for r in registros if mapa.chave_empenho(r) in empenhos]
            else:
                escolhidos = [r for r in registros if _e_pj(r)]
            escolhidos = escolhidos[:por_recorte]
            if tipo == "empenho":
                empenhos.update(chave for r in escolhidos if (chave := mapa.chave_empenho(r)))
            if escolhidos:
                recorte = [mapa.recortar_para_amostra(r, tipo) for r in escolhidos]
                conteudo = json.dumps(recorte, ensure_ascii=False, indent=1).encode()
                amostras.append(replace(resposta, conteudo=conteudo))
        return amostras


def _e_pj(registro: RegistroOrigem) -> bool:
    return mapa.OMITIDO not in registro and classificar(campo(registro, *mapa.CAMPOS_DOCUMENTO))[0] == "cnpj"


def _tem_pj(registros: list[RegistroOrigem]) -> bool:
    return any(_e_pj(r) for r in registros)


def _conferir(dados: Any, url: str) -> None:
    """Recusa resposta de erro e resposta cortada no limite da API."""
    envelope = dados.get("resposta") if isinstance(dados, dict) else None
    if not isinstance(envelope, dict):
        return
    status = str(envelope.get("status", "OK")).upper()
    if status != "OK":
        raise FonteIndisponivel(f"pe_portal: {url} respondeu status {status}")
    tamanho, limite = str(envelope.get("tamanhoResultado", "")), str(envelope.get("limiteResultado", ""))
    if tamanho.isdigit() and limite.isdigit() and int(tamanho) >= int(limite):
        raise RecorteTruncado(
            f"pe_portal: {url} devolveu {tamanho} registros, o limite da API. O recorte foi cortado: "
            "reduza-o (TCEPE_UGS_ESTADUAIS, TCEPE_MUNICIPIOS, TCEPE_ANOS)."
        )
