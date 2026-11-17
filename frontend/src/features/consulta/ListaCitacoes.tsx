import type { Citacao, ConteudoRecibo } from "../../api/types";
import { LinkOrigem } from "../../components/LinkOrigem";
import { dataHora, nomeFonte, nomeTabela } from "../../lib/formato";

/** Quantas citações aparecem abertas; o resto fica recolhido. */
const VISIVEIS = 5;

type Linha = ConteudoRecibo["linhas"][number];

function Item({ c, linha }: { c: Citacao; linha?: Linha }) {
  return (
    <li className="rounded-md border border-kyu-linha p-3 text-sm text-kyu-texto">
      <p>
        <strong>[{c.n}]</strong> {nomeTabela(c.tabela)} · {nomeFonte(c.fonte_id)} · coletado em {dataHora(c.coletado_em)}
      </p>
      <p className="mt-1 break-all text-kyu-suave">
        <LinkOrigem url={c.url_origem} semLink="Registro sem link público">
          Abrir na fonte oficial
        </LinkOrigem>{" "}
        · <span title={c.id}>{linha ? `registro ${linha.id_origem}` : `registro ${c.id}`}</span>
      </p>
    </li>
  );
}

/** Fontes citadas pela resposta. O identificador de origem vem das linhas do recibo, quando já chegou. */
export function ListaCitacoes({ citacoes, linhas }: { citacoes: Citacao[]; linhas?: Linha[] }) {
  if (citacoes.length === 0) return null;
  const porId = new Map((linhas ?? []).map((l) => [l.id, l]));
  const abertas = citacoes.slice(0, VISIVEIS);
  const recolhidas = citacoes.slice(VISIVEIS);
  const n = recolhidas.length;
  return (
    <section aria-labelledby="titulo-citacoes" className="mt-5">
      <h3 id="titulo-citacoes" className="text-sm font-semibold text-kyu-suave">
        Fontes citadas
      </h3>
      <ol aria-labelledby="titulo-citacoes" className="mt-2 space-y-2">
        {abertas.map((c) => (
          <Item key={c.n} c={c} linha={porId.get(c.id)} />
        ))}
      </ol>
      {n > 0 && (
        <details className="mt-2">
          <summary className="foco cursor-pointer rounded-md text-sm font-semibold text-kyu-laranja">
            {n === 1 ? "Ver a outra fonte" : `Ver as outras ${n} fontes`}
          </summary>
          <ol className="mt-2 space-y-2" start={VISIVEIS + 1}>
            {recolhidas.map((c) => (
              <Item key={c.n} c={c} linha={porId.get(c.id)} />
            ))}
          </ol>
        </details>
      )}
    </section>
  );
}
