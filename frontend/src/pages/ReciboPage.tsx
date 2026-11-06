import { Link, useParams } from "react-router-dom";

import { Carregando } from "../components/Carregando";
import { MensagemErro } from "../components/MensagemErro";
import { Selo } from "../components/Selo";
import { TituloPagina } from "../components/TituloPagina";
import { moeda, nomesFontes, temDadoSintetico, valorPrincipal, valoresMoeda } from "../features/recibo/leitura";
import { useRecibo } from "../features/recibo/useRecibo";
import { nomeIntent } from "../lib/apresentacao";
import { dataHora, nomeFonte, nomeTabela } from "../lib/formato";

const DESCRICAO_ORIGEM: Record<string, string> = {
  "sum(contratos.valor_global)": "soma do valor global dos contratos",
  "sum(valor_global)": "soma do valor global dos contratos",
  "sum(valor_global) vigentes": "soma do valor dos contratos vigentes",
  "sum(pagamentos.valor)": "soma dos pagamentos",
};

const VERIFICACAO: Record<string, string> = {
  aprovado: "aprovado pelo verificador",
  fallback: "texto pronto do sistema (o texto da IA não passou na conferência)",
  abstencao: "abstenção: sem registros nas fontes autorizadas",
  negado: "negado",
};

/** Tela 02 do design: recibo de evidências de uma resposta (GET /recibos/{id}). */
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
  const principal = valorPrincipal(c);
  const valores = valoresMoeda(c);
  const sintetico = temDadoSintetico(c);
  const n = c.linhas.length;

  return (
    <div className="space-y-6">
      <TituloPagina numero="02" titulo="Recibo de evidências">
        Confira os registros utilizados para sustentar uma resposta do KYU.
      </TituloPagina>

      <section aria-labelledby="titulo-valor" className="cartao flex flex-wrap items-start justify-between gap-4 p-7">
        <div>
          <h2 id="titulo-valor" className="text-sm font-bold uppercase tracking-wide text-kyu-suave">
            Valor total identificado
          </h2>
          <p className="mt-2 text-4xl font-extrabold text-kyu-texto sm:text-5xl">
            {principal ? moeda(principal.valor) : "Sem valor em reais"}
          </p>
          <p className={`mt-3 text-sm font-semibold ${sintetico ? "text-kyu-ambar" : "text-kyu-suave"}`}>
            {sintetico
              ? "Exemplo demonstrativo · valores fictícios · não representa consulta oficial"
              : "Calculado pelo banco a partir dos registros de origem abaixo"}
          </p>
        </div>
        <Selo tom="verde">
          {n} registro{n === 1 ? "" : "s"} relacionado{n === 1 ? "" : "s"}
        </Selo>
      </section>

      <section aria-labelledby="titulo-registros" className="cartao p-6">
        <h2 id="titulo-registros" className="text-xl font-bold text-kyu-texto">
          Registros de origem
        </h2>
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
                      {linha.url_origem && /^https?:\/\//.test(linha.url_origem) ? (
                        <a href={linha.url_origem} target="_blank" rel="noopener noreferrer"
                          className="foco text-kyu-laranja underline">
                          Registro {String(i + 1).padStart(2, "0")}
                          <span className="sr-only"> (abre a fonte oficial em nova aba)</span>
                        </a>
                      ) : (
                        <span className="text-kyu-suave">Registro {String(i + 1).padStart(2, "0")} · sem link público</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {valores.length > 0 && (
          <ul className="mt-6 space-y-1 font-semibold text-kyu-verde">
            {valores.map((v) => (
              <li key={v.marcador}>
                Total reproduzível: {DESCRICAO_ORIGEM[v.origem] ?? v.origem} = {moeda(v.valor)}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="titulo-rastreabilidade" className="cartao p-6">
        <h2 id="titulo-rastreabilidade" className="text-xl font-bold text-kyu-texto">
          Rastreabilidade
        </h2>
        <dl className="mt-3 grid gap-x-6 gap-y-2 text-kyu-texto sm:grid-cols-[max-content_1fr]">
          <dt className="font-semibold">Origem</dt>
          <dd>{nomesFontes(c).join(" · ") || "nenhuma fonte citada"}</dd>
          <dt className="font-semibold">Pergunta</dt>
          <dd>{c.pergunta}</dd>
          <dt className="font-semibold">Consulta</dt>
          <dd>
            {nomeIntent(c.execucao.consulta_catalogo)} ({c.execucao.consulta_catalogo}) · escopo{" "}
            {c.execucao.ufs_efetivas.join(", ") || c.ufs_autorizadas.join(", ")}
          </dd>
          <dt className="font-semibold">Verificação</dt>
          <dd>{VERIFICACAO[c.verificacao.status] ?? c.verificacao.status}</dd>
          <dt className="font-semibold">Registrado em</dt>
          <dd>{dataHora(r.criado_em)}</dd>
          <dt className="font-semibold">Selo (sha256)</dt>
          <dd className="break-all font-mono text-sm">{r.hash}</dd>
        </dl>
        <p className="mt-4 text-sm text-kyu-suave">
          Cada linha abre o registro original ou apresenta seu identificador de origem.
        </p>
      </section>

      <p>
        <Link to="/" className="foco font-semibold text-kyu-laranja underline">
          Voltar para a consulta
        </Link>
      </p>
    </div>
  );
}
