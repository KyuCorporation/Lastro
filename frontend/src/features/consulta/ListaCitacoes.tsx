import type { Citacao } from "../../api/types";
import { LinkOrigem } from "../../components/LinkOrigem";
import { dataHora, nomeFonte } from "../../lib/formato";

/** Quantas citações aparecem abertas; o resto fica recolhido. */
const VISIVEIS = 5;

function Item({ c }: { c: Citacao }) {
  return (
    <li className="rounded-md border border-kyu-linha p-3 text-sm text-kyu-texto">
      <p>
        <strong>[{c.n}]</strong> {c.resumo}
      </p>
      <p className="mt-1 break-all text-kyu-suave">
        {nomeFonte(c.fonte_id)} · coletado em {dataHora(c.coletado_em)} ·{" "}
        <LinkOrigem url={c.url_origem} semLink="Registro sem link público">
          Abrir na fonte oficial
        </LinkOrigem>{" "}
        · <span title={c.id}>registro {c.id_origem}</span>
      </p>
    </li>
  );
}

/** Fontes citadas pela resposta: o que é cada registro, de onde veio e o link para a fonte. */
export function ListaCitacoes({ citacoes }: { citacoes: Citacao[] }) {
  if (citacoes.length === 0) return null;
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
          <Item key={c.n} c={c} />
        ))}
      </ol>
      {n > 0 && (
        <details className="mt-2">
          <summary className="foco cursor-pointer rounded-md text-sm font-semibold text-kyu-laranja">
            {n === 1 ? "Ver a outra fonte" : `Ver as outras ${n} fontes`}
          </summary>
          <ol className="mt-2 space-y-2" start={VISIVEIS + 1}>
            {recolhidas.map((c) => (
              <Item key={c.n} c={c} />
            ))}
          </ol>
        </details>
      )}
    </section>
  );
}
