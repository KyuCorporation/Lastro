import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import type { ConteudoRecibo } from "../api/types";
import { Carregando } from "../components/Carregando";
import { LinkOrigem } from "../components/LinkOrigem";
import { MensagemErro } from "../components/MensagemErro";
import { Selo } from "../components/Selo";
import { TituloPagina } from "../components/TituloPagina";
import { ValoresDaResposta } from "../features/consulta/ValoresDaResposta";
import {
  contagemPrincipal,
  contextoCarteira,
  moeda,
  nomesFontes,
  parametrosLegiveis,
  temDadoSintetico,
  valorPrincipal,
} from "../features/recibo/leitura";
import { useRecibo, useVerificacaoRecibo } from "../features/recibo/useRecibo";
import { nomeIntent, nomeMotivo } from "../lib/apresentacao";
import { dataHora, nomeFonte, nomeTabela } from "../lib/formato";

const VERIFICACAO: Record<string, string> = {
  aprovado: "aprovado pelo verificador",
  fallback: "resposta padrão do sistema, com os valores do banco",
  abstencao: "sem registros nas fontes autorizadas",
  negado: "negado",
};

/** Selo de integridade: o servidor recalcula o sha256 do conteúdo gravado e compara com o hash guardado. */
function SeloIntegridade({ id }: { id: string }) {
  const v = useVerificacaoRecibo(id);
  let tom: "verde" | "vermelho" | "neutro" = "neutro";
  let texto = "Verificando a integridade…";
  if (v.isError) texto = "Não foi possível verificar a integridade agora";
  else if (v.data?.integro) {
    tom = "verde";
    texto = "Íntegro · hash recalculado confere com o gravado";
  } else if (v.data) {
    tom = "vermelho";
    texto = "Alterado depois de gravado · hash recalculado não confere";
  }
  return (
    <p role="status" aria-label="Integridade do recibo" aria-live="polite">
      <Selo tom={tom}>{texto}</Selo>
    </p>
  );
}

function Secao({ id, titulo, children }: { id: string; titulo: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="cartao p-6">
      <h2 id={id} className="text-xl font-bold text-kyu-texto">
        {titulo}
      </h2>
      {children}
    </section>
  );
}

const CLASSE_DL = "mt-3 grid gap-x-6 gap-y-2 text-kyu-texto sm:grid-cols-[max-content_1fr]";

/** Destaque do topo: o total em reais ou, em consulta sem valor (sanções), a contagem principal. */
function Destaque({ id, conteudo }: { id: string; conteudo: ConteudoRecibo }) {
  const principal = valorPrincipal(conteudo);
  const contagem = principal ? null : contagemPrincipal(conteudo);
  const titulo = principal ? "Valor total identificado" : (contagem?.rotulo ?? "Valor total identificado");
  const valor = principal ? moeda(principal.valor) : (contagem?.texto ?? "Sem valor em reais");
  const n = conteudo.linhas.length;
  return (
    <section aria-labelledby="titulo-valor" className="cartao flex flex-wrap items-start justify-between gap-4 p-7">
      <div>
        <h2 id="titulo-valor" className="text-sm font-bold uppercase tracking-wide text-kyu-suave">
          {titulo}
        </h2>
        <p className="mt-2 text-4xl font-extrabold text-kyu-texto sm:text-5xl">{valor}</p>
        <p className="mt-3 text-sm font-semibold text-kyu-suave">
          Calculado pelo banco a partir dos registros de origem abaixo
          {temDadoSintetico(conteudo) && " · inclui registro sintético de teste"}
        </p>
      </div>
      <div className="flex flex-col items-end gap-2">
        <Selo tom="verde">
          {n} registro{n === 1 ? "" : "s"} relacionado{n === 1 ? "" : "s"}
        </Selo>
        <SeloIntegridade id={id} />
      </div>
    </section>
  );
}

function Producao({ conteudo }: { conteudo: ConteudoRecibo }) {
  const { ia, verificacao } = conteudo;
  const plano = ia.planejador_por_regras ? "regras do sistema, sem IA" : `modelo ${ia.modelo ?? ia.provedor ?? "de IA"}`;
  const motivos = verificacao.motivos ?? [];
  const versoes = [ia.versao_prompt_planejador, ia.versao_prompt_redator].filter(Boolean).join(" · ");
  return (
    <Secao id="titulo-producao" titulo="Como a resposta foi produzida">
      <dl className={CLASSE_DL}>
        <dt className="font-semibold">Plano</dt>
        <dd>{plano}</dd>
        <dt className="font-semibold">Texto</dt>
        <dd>
          {VERIFICACAO[verificacao.status] ?? verificacao.status}
          {motivos.length > 0 && (
            <ul className="mt-1 list-inside list-disc text-sm text-kyu-suave">
              {motivos.map((m) => (
                <li key={m}>{nomeMotivo(m)}</li>
              ))}
            </ul>
          )}
        </dd>
        <dt className="font-semibold">Números</dt>
        <dd>inseridos pelo sistema a partir dos registros; a IA não escreve valores</dd>
      </dl>
      {versoes && <p className="mt-3 text-sm text-kyu-suave">Versões das instruções: {versoes}</p>}
    </Secao>
  );
}

function CopiarSelo({ hash }: { hash: string }) {
  const [copiado, setCopiado] = useState(false);
  async function copiar() {
    try {
      await navigator.clipboard.writeText(hash);
      setCopiado(true);
    } catch {
      setCopiado(false); // sem permissão de área de transferência: o selo continua visível para copiar à mão
    }
  }
  return (
    <span className="ml-3 inline-flex items-center gap-2 font-sans">
      <button type="button" onClick={() => void copiar()} className="foco rounded-md border border-kyu-borda px-2 py-0.5 text-sm">
        Copiar selo
      </button>
      <span role="status" aria-live="polite" className="text-sm text-kyu-verde">
        {copiado ? "Selo copiado" : ""}
      </span>
    </span>
  );
}

/** Tela 02 do design: recibo de evidências de uma resposta (GET /recibos/{id}), com o que o SPEC §12 lista. */
export function ReciboPage() {
  const { id } = useParams();
  const recibo = useRecibo(id);

  if (recibo.isPending) return <Carregando texto="Carregando o recibo…" />;
  if (recibo.isError) {
    return (
      <div className="space-y-4">
        <TituloPagina numero="02" titulo="Recibo de evidências" />
        <MensagemErro erro={recibo.error} titulo="Não foi possível abrir o recibo" />
        <Link to="/" className="foco font-semibold text-kyu-laranja underline">
          Voltar para a consulta
        </Link>
      </div>
    );
  }

  const r = recibo.data;
  const c = r.conteudo;
  const n = c.linhas.length;

  return (
    <div className="space-y-6">
      <TituloPagina numero="02" titulo="Recibo de evidências">
        Confira os registros utilizados para sustentar uma resposta do KYU.
      </TituloPagina>

      <Destaque id={r.id} conteudo={c} />

      <Secao id="titulo-registros" titulo="Registros de origem">
        {n === 0 ? (
          <p className="mt-4 text-kyu-suave">Nenhum registro: a consulta não encontrou dados nas fontes autorizadas.</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[44rem] border-collapse text-left">
              <caption className="sr-only">Registros usados na resposta, com a fonte e o link para a origem</caption>
              <thead className="tabela-cabecalho">
                <tr>
                  <th scope="col" className="rounded-l-md px-4 py-3">ID</th>
                  <th scope="col" className="px-4 py-3">Tipo</th>
                  <th scope="col" className="px-4 py-3">Fonte</th>
                  <th scope="col" className="px-4 py-3">Coletado em</th>
                  <th scope="col" className="rounded-r-md px-4 py-3">Referência</th>
                </tr>
              </thead>
              <tbody>
                {c.linhas.map((linha, i) => (
                  <tr key={linha.id} className="border-b border-kyu-linha">
                    <td className="break-all px-4 py-4 font-bold">{linha.id_origem}</td>
                    <td className="px-4 py-4">{nomeTabela(linha.tabela)}</td>
                    <td className="px-4 py-4">{nomeFonte(linha.fonte_id)}</td>
                    <td className="px-4 py-4">{dataHora(linha.coletado_em)}</td>
                    <td className="px-4 py-4 font-semibold">
                      <LinkOrigem url={linha.url_origem}>Registro {String(i + 1).padStart(2, "0")}</LinkOrigem>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <ValoresDaResposta conteudo={c} />
      </Secao>

      <Secao id="titulo-plano" titulo="Plano e parâmetros">
        <dl className={CLASSE_DL}>
          <dt className="font-semibold">Consulta escolhida</dt>
          <dd>{nomeIntent(c.execucao.consulta_catalogo)}</dd>
          <dt className="font-semibold">Versão no catálogo</dt>
          <dd className="font-mono text-sm">{c.execucao.consulta_catalogo}</dd>
          {parametrosLegiveis(c).map((p) => (
            <div key={p.nome} className="contents">
              <dt className="font-semibold">{p.nome}</dt>
              <dd>{p.texto}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-3 text-sm text-kyu-suave">
          A consulta é um SQL fixo do catálogo, executado com o seu acesso. A IA só escolhe qual consulta usar.
        </p>
      </Secao>

      <Secao id="titulo-fontes" titulo="Fontes">
        {c.fontes.length === 0 ? (
          <p className="mt-3 text-kyu-suave">Nenhuma fonte citada.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {c.fontes.map((f) => (
              <li key={f.fonte_id}>
                <span className="font-semibold">{f.nome}</span>{" "}
                <span className="text-kyu-suave">· coletada em {dataHora(f.coletado_em)}</span>
                {f.sintetico && (
                  <span className="ml-2">
                    <Selo tom="neutro">Registro sintético de teste</Selo>
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Secao>

      <Producao conteudo={c} />

      <Secao id="titulo-rastreabilidade" titulo="Rastreabilidade">
        <dl className={CLASSE_DL}>
          <dt className="font-semibold">Origem</dt>
          <dd>{nomesFontes(c).join(" · ") || "nenhuma fonte citada"}</dd>
          <dt className="font-semibold">Pergunta</dt>
          <dd>{c.pergunta}</dd>
          <dt className="font-semibold">Contexto</dt>
          <dd>{contextoCarteira(c) ?? "Sem carteira"}</dd>
          <dt className="font-semibold">Escopo</dt>
          <dd>{c.execucao.ufs_efetivas.join(", ") || c.ufs_autorizadas.join(", ")}</dd>
          <dt className="font-semibold">Registrado em</dt>
          <dd>{dataHora(r.criado_em)}</dd>
          <dt className="font-semibold">Selo (sha256)</dt>
          <dd className="break-all font-mono text-sm">
            {r.hash}
            <CopiarSelo hash={r.hash} />
          </dd>
        </dl>
        <p className="mt-4 text-sm text-kyu-suave">
          Cada linha abre o registro original ou apresenta seu identificador de origem.
        </p>
      </Secao>

      <p>
        <Link to="/" className="foco font-semibold text-kyu-laranja underline">
          Voltar para a consulta
        </Link>
      </p>
    </div>
  );
}
