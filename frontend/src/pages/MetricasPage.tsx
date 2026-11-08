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

/** Um número com rótulo, detalhe e, se houver, a meta e se foi atingida (sempre em texto). */
function Indicador(props: {
  rotulo: string;
  valor: string;
  detalhe?: string;
  meta?: { texto: string; atingida: boolean };
}) {
  const id = useId();
  return (
    <div role="group" aria-labelledby={id} className="rounded-lg border border-kyu-linha p-5">
      <h3 id={id} className="text-sm font-bold uppercase tracking-wide text-kyu-suave">
        {props.rotulo}
      </h3>
      <p className="mt-2 text-3xl font-extrabold text-kyu-texto">{props.valor}</p>
      {props.detalhe && <p className="mt-1 text-sm text-kyu-suave">{props.detalhe}</p>}
      {props.meta && (
        <p className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-kyu-suave">{props.meta.texto}</span>
          <Selo tom={props.meta.atingida ? "verde" : "vermelho"}>
            {props.meta.atingida ? "Meta atingida" : "Abaixo da meta"}
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
  return (
    <>
      <p className="mb-4 font-semibold text-kyu-texto">
        {m.ok ?? 0} de {m.n_casos ?? 0} perguntas sem falha
      </p>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Indicador
          rotulo="Acerto de intent"
          valor={pct(m.acerto_intent)}
          detalhe={typeof m.n_intent_avaliada === "number" ? plural(m.n_intent_avaliada, "pergunta avaliada", "perguntas avaliadas") : undefined}
          meta={{ texto: `meta ≥ ${decimal(meta)}%`, atingida: (m.acerto_intent ?? 0) >= meta }}
        />
        <Indicador rotulo="Comportamento esperado" valor={pct(m.acerto_comportamento)}
          detalhe="responder, pedir detalhe, abster-se ou negar" />
        <Indicador
          rotulo="Citação correta"
          valor={pct(m.citacao_correta)}
          detalhe={typeof m.n_com_citacao === "number" ? plural(m.n_com_citacao, "resposta com citação", "respostas com citação") : undefined}
        />
        <Indicador
          rotulo="Resultado igual ao SQL de referência"
          valor={pct(m.acerto_resultado)}
          detalhe={plural(nSql, "pergunta com SQL de referência", "perguntas com SQL de referência")}
        />
        <Indicador rotulo="Texto trocado pelo modelo padrão" valor={pct(m.taxa_fallback)}
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
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <Indicador
          rotulo="Ataques bloqueados"
          valor={`${m.bloqueados ?? 0} de ${m.n_casos ?? 0}`}
          detalhe={pct(m.pct_bloqueado)}
          meta={{ texto: `meta ≥ ${META_BLOQUEIO}%`, atingida: (m.pct_bloqueado ?? 0) >= META_BLOQUEIO }}
        />
        <Indicador
          rotulo="Vazamentos"
          valor={String(vazamentos)}
          detalhe="dado de outro estado ou cliente na resposta"
          meta={{ texto: "meta: zero", atingida: vazamentos === 0 }}
        />
      </div>
      {categorias.length > 0 && (
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[32rem] border-collapse text-left">
            <caption className="sr-only">Ataques por categoria</caption>
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

function Cronometro({ dados }: { dados: Record<string, unknown> }) {
  const campos = Object.entries(dados).filter(([, v]) => typeof v === "string" || typeof v === "number");
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

function subtitulo(parte: { gerado_em?: string; provedor_llm?: string } | null, comando: string): ReactNode {
  if (!parte) return `Gerado por ${comando}.`;
  const quando = parte.gerado_em ? `em ${dataHora(parte.gerado_em)}` : "";
  return `Gerado por ${comando} ${quando} · ${nomeProvedor(parte.provedor_llm)}`;
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
      <Secao id="titulo-cronometro" titulo="Cronômetro de diligência"
        subtitulo="Tempo para analisar um fornecedor com e sem o Lastro.">
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
