import { useQuery } from "@tanstack/react-query";

import { useApi } from "../api/ApiProvider";
import type { ErroApi } from "../api/http";
import type { Fonte } from "../api/types";
import { Carregando } from "../components/Carregando";
import { MensagemErro } from "../components/MensagemErro";
import { Selo } from "../components/Selo";
import { TituloPagina } from "../components/TituloPagina";
import type { Tom } from "../lib/apresentacao";
import { dataHora } from "../lib/formato";

// O que cada fonte traz para o Lastro (docs/catalogo-fontes.md). A coleta vem de GET /fontes.
const CONTEUDO: Record<string, { conteudo: string; ordem: number }> = {
  pe_portal: {
    conteudo: "Contratos, empenhos e liquidações de PE (amostra de homologação; nesta base, os contratos de PE vêm do PNCP)",
    ordem: 1,
  },
  pncp: { conteudo: "Contratos públicos de todas as esferas (PE e AL)", ordem: 2 },
  ceis: { conteudo: "Empresas inidôneas e suspensas, de todo o país", ordem: 3 },
  cnep: { conteudo: "Empresas punidas pela Lei Anticorrupção, de todo o país", ordem: 4 },
};

const SITUACAO: Record<string, { rotulo: string; tom: Tom }> = {
  ok: { rotulo: "Coletada", tom: "verde" },
  parcial: { rotulo: "Coleta parcial", tom: "ambar" },
  falhou: { rotulo: "Falhou", tom: "vermelho" },
};

const CATALOGO = [
  { conjunto: "Contratos", fontes: "TCE-PE, PNCP", campos: "Órgão, fornecedor, objeto, valor, vigência" },
  { conjunto: "Pagamentos", fontes: "TCE-PE", campos: "Órgão, favorecido, valor, data (empenho e liquidação)" },
  { conjunto: "Sanções", fontes: "CEIS, CNEP", campos: "Tipo, órgão sancionador, início e fim, fundamentação" },
  { conjunto: "Fornecedores", fontes: "Todas", campos: "CNPJ e razão social (pessoa física é descartada)" },
];

const ETAPAS = ["Fontes oficiais", "Captura", "Normalização", "Catálogo KYU"];

function LinhaFonte({ f }: { f: Fonte }) {
  const e = f.ultima_execucao;
  const situacao = e ? (SITUACAO[e.status] ?? { rotulo: e.status, tom: "neutro" as Tom }) : null;
  return (
    <tr className="border-b border-kyu-linha align-top">
      <th scope="row" className="px-4 py-4 font-bold">{f.nome}</th>
      <td className="px-4 py-4">{CONTEUDO[f.id]?.conteudo}</td>
      <td className="px-4 py-4">
        {e?.finalizada_em ? dataHora(e.finalizada_em) : "—"}
        {e?.registros_novos ? (
          <span className="block text-sm text-kyu-suave">{e.registros_novos.toLocaleString("pt-BR")} registros novos</span>
        ) : null}
      </td>
      <td className="px-4 py-4">{situacao ? <Selo tom={situacao.tom}>{situacao.rotulo}</Selo> : <Selo tom="neutro">Sem coleta</Selo>}</td>
    </tr>
  );
}

/** Tela 05: fontes integradas, com a última coleta lida do banco (GET /fontes), e o catálogo. */
export function FontesPage() {
  const api = useApi();
  const fontes = useQuery<Fonte[], ErroApi>({ queryKey: ["fontes"], queryFn: () => api.fontes.listar() });
  const lista = (fontes.data ?? [])
    .filter((f) => f.id in CONTEUDO)
    .sort((a, b) => CONTEUDO[a.id].ordem - CONTEUDO[b.id].ordem);

  return (
    <div className="space-y-6">
      <TituloPagina numero="05" titulo="Fonte e catálogo de dados">
        Dados públicos oficiais. Cada registro guarda a origem, a data da coleta e o hash do conteúdo.
      </TituloPagina>

      <section aria-labelledby="titulo-fontes" className="cartao p-6">
        <h2 id="titulo-fontes" className="text-xl font-bold text-kyu-texto">
          Fontes integradas
        </h2>
        {fontes.isPending ? (
          <Carregando texto="Carregando as fontes…" />
        ) : fontes.isError ? (
          <div className="mt-4">
            <MensagemErro erro={fontes.error} titulo="Não foi possível carregar as fontes" />
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[44rem] border-collapse text-left">
              <caption className="sr-only">Fontes integradas e a última coleta de cada uma</caption>
              <thead className="tabela-cabecalho">
                <tr>
                  <th scope="col" className="rounded-l-md px-4 py-3">Fonte</th>
                  <th scope="col" className="px-4 py-3">Conteúdo</th>
                  <th scope="col" className="px-4 py-3">Última coleta</th>
                  <th scope="col" className="rounded-r-md px-4 py-3">Situação</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((f) => (
                  <LinhaFonte key={f.id} f={f} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="titulo-catalogo" className="cartao p-6">
        <h2 id="titulo-catalogo" className="text-xl font-bold text-kyu-texto">
          Catálogo de dados
        </h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[36rem] border-collapse text-left">
            <caption className="sr-only">Conjuntos do catálogo, a fonte de cada um e os campos</caption>
            <thead className="tabela-cabecalho">
              <tr>
                <th scope="col" className="rounded-l-md px-4 py-3">Conjunto</th>
                <th scope="col" className="px-4 py-3">Fontes</th>
                <th scope="col" className="rounded-r-md px-4 py-3">Campos</th>
              </tr>
            </thead>
            <tbody>
              {CATALOGO.map((linha) => (
                <tr key={linha.conjunto} className="border-b border-kyu-linha">
                  <th scope="row" className="px-4 py-4 font-bold">{linha.conjunto}</th>
                  <td className="px-4 py-4">{linha.fontes}</td>
                  <td className="px-4 py-4">{linha.campos}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="titulo-pipeline" className="cartao p-6">
        <h2 id="titulo-pipeline" className="text-xl font-bold text-kyu-texto">
          Pipeline de dados
        </h2>
        <ol className="mt-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          {ETAPAS.map((etapa, i) => (
            <li key={etapa} className="flex items-center gap-3 text-lg font-bold text-kyu-texto">
              <span>
                <span aria-hidden="true">{String(i + 1).padStart(2, "0")} </span>
                {etapa}
              </span>
              {i < ETAPAS.length - 1 && (
                <span aria-hidden="true" className="hidden text-xl text-kyu-laranja md:inline">
                  →
                </span>
              )}
            </li>
          ))}
        </ol>
        <p className="mt-5 text-kyu-suave">
          Captura a 1 requisição por segundo, guarda a resposta bruta com sha256, normaliza campo a campo, descarta
          pessoa física e grava sem duplicar: rodar de novo não muda as contagens.
        </p>
      </section>
    </div>
  );
}
