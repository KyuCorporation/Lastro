import { useQuery } from "@tanstack/react-query";
import { useId, type ReactNode } from "react";

import { useApi } from "../api/ApiProvider";
import type { ErroApi } from "../api/http";
import type { Metricas, MetricasAtaques, MetricasGabarito } from "../api/types";
import { Carregando } from "../components/Carregando";
import { MensagemErro } from "../components/MensagemErro";
import { Selo } from "../components/Selo";
import { TituloPagina } from "../components/TituloPagina";
import { dataHora, decimal } from "../lib/formato";

// Metas do SPEC §14.6. A de intent vem do próprio relatório (meta_intent); estas não estão nele.
const META_BLOQUEIO = 95;

function pct(v: number | null | undefined): string {
  return typeof v === "number" ? `${decimal(v)}%` : "—";
}

function plural(n: number, singular: string, pluralForma: string): string {
  return `${n} ${n === 1 ? singular : pluralForma}`;
}

function nomeProvedor(provedor: string | undefined): string {
  if (!provedor) return "provedor não informado";
  return provedor === "mock" ? "modelo determinístico (sem LLM)" : `LLM ${provedor}`;
}

/** Rótulo curto de um provedor na comparação: "Sem LLM", "Gemini". */
function rotuloProvedor(provedor: string): string {
  if (provedor === "mock") return "Sem LLM";
  return provedor.charAt(0).toUpperCase() + provedor.slice(1);
}

/** O mesmo provedor no meio de uma frase: "sem LLM", "com Gemini". */
function emFrase(provedor: string | undefined): string {
  if (!provedor) return "provedor não informado";
  return provedor === "mock" ? "sem LLM" : `com ${rotuloProvedor(provedor)}`;
}

/** Execuções por provedor (GET /metricas, `por_provedor`), a sem LLM primeiro. Comparação só com duas ou mais. */
function porProvedor<T extends { por_provedor?: Record<string, T> }>(m: T): [string, T][] {
  return Object.entries(m.por_provedor ?? {}).sort(([a], [b]) =>
    a === "mock" ? -1 : b === "mock" ? 1 : a.localeCompare(b),
  );
}

type ValorDoProvedor = { provedor: string; valor: string };

/** Meta conferida em cada provedor: o selo diz em qual ficou abaixo. */
function metaPorProvedor<T>(lista: [string, T][], texto: string, atinge: (m: T) => boolean) {
  const abaixo = lista.filter(([, m]) => !atinge(m)).map(([p]) => emFrase(p));
  return { texto, atingida: abaixo.length === 0, abaixoEm: abaixo };
}

/** Um número com rótulo, detalhe e, se houver, a meta e se foi atingida (sempre em texto). */
function Indicador(props: {
  rotulo: string;
  valor: string;
  detalhe?: string;
  meta?: { texto: string; atingida: boolean; abaixoEm?: string[] };
  /** Comparação entre provedores: substitui `valor` por uma linha para cada um. */
  valores?: ValorDoProvedor[];
}) {
  const id = useId();
  return (
    <div role="group" aria-labelledby={id} className="rounded-lg border border-kyu-linha p-5">
      <h3 id={id} className="text-sm font-bold uppercase tracking-wide text-kyu-suave">
        {props.rotulo}
      </h3>
      {props.valores ? (
        <ul className="mt-2 space-y-1">
          {props.valores.map((v) => (
            <li key={v.provedor} className="flex items-baseline justify-between gap-3">
              <span className="text-sm font-semibold text-kyu-suave">{rotuloProvedor(v.provedor)}</span>
              <span className="text-2xl font-extrabold text-kyu-texto">{v.valor}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-3xl font-extrabold text-kyu-texto">{props.valor}</p>
      )}
      {props.detalhe && <p className="mt-1 text-sm text-kyu-suave">{props.detalhe}</p>}
      {props.meta && (
        <p className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-kyu-suave">{props.meta.texto}</span>
          <Selo tom={props.meta.atingida ? "verde" : "vermelho"}>
            {props.meta.atingida
              ? "Meta atingida"
              : props.meta.abaixoEm?.length
                ? `Abaixo da meta ${props.meta.abaixoEm.join(" e ")}`
                : "Abaixo da meta"}
          </Selo>
        </p>
      )}
    </div>
  );
}

function Secao({ id, titulo, subtitulo, children }: { id: string; titulo: string; subtitulo?: ReactNode; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="cartao p-6">
      <h2 id={id} className="text-xl font-bold text-kyu-texto">
        {titulo}
      </h2>
      {subtitulo && <p className="mt-1 text-sm text-kyu-suave">{subtitulo}</p>}
      <div className="mt-5">{children}</div>
    </section>
  );
}

function NaoGerado({ comando }: { comando: string }) {
  return (
    <p className="text-kyu-suave">
      Relatório ainda não gerado. Rode <code className="font-mono">{comando}</code>.
    </p>
  );
}

function Gabarito({ m }: { m: MetricasGabarito }) {
  const meta = m.meta_intent ?? 90;
  const nSql = m.n_com_sql_referencia ?? 0;
  const lista = porProvedor(m);
  const comparar = lista.length > 1;
  const serie = (f: (r: MetricasGabarito) => string): ValorDoProvedor[] | undefined =>
    comparar ? lista.map(([provedor, r]) => ({ provedor, valor: f(r) })) : undefined;
  const textoMeta = `meta ≥ ${decimal(meta)}%`;
  return (
    <>
      <p className="mb-4 font-semibold text-kyu-texto">
        {comparar
          ? lista
              .map(([p, r]) => `${rotuloProvedor(p)}: ${r.ok ?? 0} de ${r.n_casos ?? 0} perguntas sem falha`)
              .join(" · ")
          : `${m.ok ?? 0} de ${m.n_casos ?? 0} perguntas sem falha`}
      </p>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Indicador
          rotulo="Acerto de intent"
          valor={pct(m.acerto_intent)}
          valores={serie((r) => pct(r.acerto_intent))}
          detalhe={typeof m.n_intent_avaliada === "number" ? plural(m.n_intent_avaliada, "pergunta avaliada", "perguntas avaliadas") : undefined}
          meta={
            comparar
              ? metaPorProvedor(lista, textoMeta, (r) => (r.acerto_intent ?? 0) >= meta)
              : { texto: textoMeta, atingida: (m.acerto_intent ?? 0) >= meta }
          }
        />
        <Indicador rotulo="Comportamento esperado" valor={pct(m.acerto_comportamento)}
          valores={serie((r) => pct(r.acerto_comportamento))}
          detalhe="responder, pedir detalhe, abster-se ou negar" />
        <Indicador
          rotulo="Citação correta"
          valor={pct(m.citacao_correta)}
          valores={serie((r) => pct(r.citacao_correta))}
          detalhe={typeof m.n_com_citacao === "number" ? plural(m.n_com_citacao, "resposta com citação", "respostas com citação") : undefined}
        />
        <Indicador
          rotulo="Resultado igual ao SQL de referência"
          valor={pct(m.acerto_resultado)}
          valores={serie((r) => pct(r.acerto_resultado))}
          detalhe={plural(nSql, "pergunta com SQL de referência", "perguntas com SQL de referência")}
        />
        <Indicador rotulo="Texto trocado pelo modelo padrão" valor={pct(m.taxa_fallback)}
          valores={serie((r) => pct(r.taxa_fallback))}
          detalhe="quando o verificador recusa o texto da IA" />
      </div>
    </>
  );
}

// Categorias de eval/ataques/ataques.yaml.
const NOME_CATEGORIA: Record<string, string> = {
  abuso: "Abuso de volume",
  armazenada: "Injeção armazenada em dado de fonte",
  autenticacao: "Autenticação",
  direta: "Injeção direta na pergunta",
  entrada_invalida: "Entrada inválida",
  idor: "Recurso de outro usuário (IDOR)",
  outra_uf: "Dado de outro estado",
  outro_tenant: "Dado de outro cliente",
  perfil: "Perfil sem permissão",
  sql_param: "Injeção de SQL",
  vazar_prompt: "Pedido do prompt do sistema",
};

function nomeCategoria(c: string): string {
  if (c in NOME_CATEGORIA) return NOME_CATEGORIA[c];
  const texto = c.replace(/_/g, " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function Ataques({ m }: { m: MetricasAtaques }) {
  const categorias = Object.entries(m.por_categoria ?? {});
  const vazamentos = m.vazamentos ?? 0;
  const lista = porProvedor(m);
  const comparar = lista.length > 1;
  const textoBloqueio = `meta ≥ ${META_BLOQUEIO}%`;
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <Indicador
          rotulo="Ataques bloqueados"
          valor={`${m.bloqueados ?? 0} de ${m.n_casos ?? 0}`}
          valores={
            comparar
              ? lista.map(([provedor, r]) => ({ provedor, valor: `${r.bloqueados ?? 0} de ${r.n_casos ?? 0}` }))
              : undefined
          }
          detalhe={comparar ? undefined : pct(m.pct_bloqueado)}
          meta={
            comparar
              ? metaPorProvedor(lista, textoBloqueio, (r) => (r.pct_bloqueado ?? 0) >= META_BLOQUEIO)
              : { texto: textoBloqueio, atingida: (m.pct_bloqueado ?? 0) >= META_BLOQUEIO }
          }
        />
        <Indicador
          rotulo="Vazamentos"
          valor={String(vazamentos)}
          valores={comparar ? lista.map(([provedor, r]) => ({ provedor, valor: String(r.vazamentos ?? 0) })) : undefined}
          detalhe="dado de outro estado ou cliente na resposta"
          meta={
            comparar
              ? metaPorProvedor(lista, "meta: zero", (r) => (r.vazamentos ?? 0) === 0)
              : { texto: "meta: zero", atingida: vazamentos === 0 }
          }
        />
      </div>
      {categorias.length > 0 && (
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[32rem] border-collapse text-left">
            {comparar ? (
              <caption className="mb-2 text-left text-sm text-kyu-suave">
                Ataques por categoria, {emFrase(m.provedor_llm)}
              </caption>
            ) : (
              <caption className="sr-only">Ataques por categoria</caption>
            )}
            <thead className="tabela-cabecalho">
              <tr>
                <th scope="col" className="rounded-l-md px-4 py-3">Categoria</th>
                <th scope="col" className="px-4 py-3 text-right">Casos</th>
                <th scope="col" className="px-4 py-3 text-right">Bloqueados</th>
                <th scope="col" className="rounded-r-md px-4 py-3 text-right">Vazamentos</th>
              </tr>
            </thead>
            <tbody>
              {categorias.map(([nome, c]) => (
                <tr key={nome} className="border-b border-kyu-linha">
                  <th scope="row" className="px-4 py-3 font-semibold">{nomeCategoria(nome)}</th>
                  <td className="px-4 py-3 text-right">{c.n}</td>
                  <td className="px-4 py-3 text-right">{c.bloqueados}</td>
                  <td className="px-4 py-3 text-right">{c.vazamentos}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

// Metadados do relatório: vão para o subtítulo, não para a lista de medidas.
const METADADOS = new Set(["gerado_em", "provedor_llm", "n_casos", "modo"]);

function Cronometro({ dados }: { dados: Record<string, unknown> }) {
  const campos = Object.entries(dados).filter(
    ([k, v]) => !METADADOS.has(k) && (typeof v === "string" || typeof v === "number"),
  );
  return (
    <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-[max-content_1fr]">
      {campos.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="font-semibold">{nomeCategoria(k)}</dt>
          <dd>{typeof v === "number" ? decimal(v) : String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

type Parte = { gerado_em?: string; provedor_llm?: string; por_provedor?: Record<string, Parte> };

function subtitulo(parte: Parte | null, comando: string): ReactNode {
  if (!parte) return `Gerado por ${comando}.`;
  const lista = porProvedor(parte);
  if (lista.length > 1) {
    const execucoes = lista
      .map(([p, r]) => `${emFrase(p)}${r.gerado_em ? ` em ${dataHora(r.gerado_em)}` : ""}`)
      .join("; ");
    return (
      `Gerado por ${comando} ${execucoes}. ` +
      "Sem LLM, o planejador é o roteador por regras e o texto vem do modelo determinístico."
    );
  }
  const quando = parte.gerado_em ? `em ${dataHora(parte.gerado_em)}` : "";
  return `Gerado por ${comando} ${quando} · ${nomeProvedor(parte.provedor_llm)}`;
}

function subtituloCronometro(c: Record<string, unknown> | null): string {
  const base = "Tempo para analisar um fornecedor com e sem o Lastro.";
  if (!c) return base;
  const quando = typeof c.gerado_em === "string" ? ` Medido em ${dataHora(c.gerado_em)}` : "";
  const n = typeof c.n_casos === "number" ? `, com ${plural(c.n_casos, "fornecedor", "fornecedores")}` : "";
  return quando ? `${base}${quando}${n}.` : base;
}

function Conteudo({ m }: { m: Metricas }) {
  return (
    <>
      <Secao id="titulo-gabarito" titulo="Gabarito de perguntas" subtitulo={subtitulo(m.eval, "make eval")}>
        {m.eval ? <Gabarito m={m.eval} /> : <NaoGerado comando="make eval" />}
      </Secao>
      <Secao id="titulo-ataques" titulo="Ataques de injeção e escopo" subtitulo={subtitulo(m.ataques, "make eval-ataques")}>
        {m.ataques ? <Ataques m={m.ataques} /> : <NaoGerado comando="make eval-ataques" />}
      </Secao>
      <Secao id="titulo-cronometro" titulo="Cronômetro de diligência" subtitulo={subtituloCronometro(m.cronometro)}>
        {m.cronometro ? <Cronometro dados={m.cronometro} /> : <p className="text-kyu-suave">Ainda não medido.</p>}
      </Secao>
    </>
  );
}

/** Tela 08: resultados do eval/ (GET /metricas), com cada meta do SPEC §14.6 escrita ao lado do número. */
export function MetricasPage() {
  const api = useApi();
  const metricas = useQuery<Metricas, ErroApi>({ queryKey: ["metricas"], queryFn: () => api.metricas.obter() });

  return (
    <div className="space-y-6">
      <TituloPagina numero="08" titulo="Métricas de qualidade">
        Números gerados pela avaliação automática do repositório, sem edição manual.
        {metricas.data?.ultima_atualizacao && ` Última atualização em ${dataHora(metricas.data.ultima_atualizacao)}.`}
      </TituloPagina>
      {metricas.isPending ? (
        <Carregando texto="Carregando as métricas…" />
      ) : metricas.isError ? (
        <MensagemErro erro={metricas.error} titulo="Não foi possível carregar as métricas" />
      ) : (
        <Conteudo m={metricas.data} />
      )}
    </div>
  );
}
