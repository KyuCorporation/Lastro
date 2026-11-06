import type { Citacao } from "../../api/types";
import { dataHora, nomeFonte, nomeTabela } from "../../lib/formato";

export function ListaCitacoes({ citacoes, idCitacao }: { citacoes: Citacao[]; idCitacao: (n: number) => string }) {
  if (citacoes.length === 0) return null;
  return (
    <section aria-labelledby="titulo-citacoes" className="mt-6">
      <h3 id="titulo-citacoes" className="text-base font-semibold text-slate-900">
        Fontes citadas
      </h3>
      <ol className="mt-2 space-y-2">
        {citacoes.map((c) => (
          <li
            key={c.n}
            id={idCitacao(c.n)}
            tabIndex={-1}
            className="rounded-md border border-slate-300 p-3 text-sm text-slate-900 target:border-blue-700 target:ring-2 target:ring-blue-700"
          >
            <p>
              <strong>[{c.n}]</strong> {nomeTabela(c.tabela)} · {nomeFonte(c.fonte_id)} · coletado em{" "}
              {dataHora(c.coletado_em)}
            </p>
            <p className="mt-1 break-all text-slate-700">
              {c.url_origem ? (
                <a
                  href={c.url_origem}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-800 underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700"
                >
                  Abrir na fonte oficial<span className="sr-only"> (abre em nova aba)</span>
                </a>
              ) : (
                <span>Sem endereço público (dado sintético ou arquivo).</span>
              )}{" "}
              · registro {c.id}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
