import type { Citacao } from "../../api/types";
import { dataHora, nomeFonte, nomeTabela } from "../../lib/formato";

export function ListaCitacoes({ citacoes, idCitacao }: { citacoes: Citacao[]; idCitacao: (n: number) => string }) {
  if (citacoes.length === 0) return null;
  return (
    <section aria-labelledby="titulo-citacoes" className="mt-5">
      <h3 id="titulo-citacoes" className="text-sm font-semibold text-kyu-suave">
        Fontes citadas
      </h3>
      <ol className="mt-2 space-y-2">
        {citacoes.map((c) => (
          <li
            key={c.n}
            id={idCitacao(c.n)}
            tabIndex={-1}
            className="rounded-md border border-kyu-linha p-3 text-sm text-kyu-texto target:border-kyu-laranja target:ring-2 target:ring-kyu-laranja"
          >
            <p>
              <strong>[{c.n}]</strong> {nomeTabela(c.tabela)} · {nomeFonte(c.fonte_id)} · coletado em{" "}
              {dataHora(c.coletado_em)}
            </p>
            <p className="mt-1 break-all text-kyu-suave">
              {c.url_origem ? (
                <a
                  href={c.url_origem}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="foco font-semibold text-kyu-laranja underline"
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
