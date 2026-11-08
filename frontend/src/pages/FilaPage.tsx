import { Link, useLocation, useParams } from "react-router-dom";

import type { ItemFila } from "../api/types";
import { Carregando } from "../components/Carregando";
import { MensagemErro } from "../components/MensagemErro";
import { TituloPagina } from "../components/TituloPagina";
import { useFila } from "../features/carteiras/hooks";
import { ListaSinais } from "../features/sinais/ListaSinais";
import { NOME_FINALIDADE } from "../lib/apresentacao";
import { cnpj, decimal, moeda } from "../lib/formato";
import type { EstadoCarteiraCriada } from "./CarteirasPage";

function avisoInvalidos(invalidos: string[]): string {
  const um = invalidos.length === 1;
  return `${invalidos.length} CNPJ${um ? "" : "s"} ignorado${um ? "" : "s"} por ser${um ? "" : "em"} inválido${um ? "" : "s"}: ${invalidos.join(", ")}`;
}

function Item({ item, posicao }: { item: ItemFila; posicao: number }) {
  const nome = item.razao_social ?? "Razão social não informada";
  return (
    <li aria-label={`Fornecedor ${posicao}: ${nome}`} className="cartao p-6">
      <div className="flex flex-wrap items-start justify-between gap-4 sm:flex-nowrap">
        <div className="min-w-0">
          <p className="text-sm font-bold uppercase tracking-wide text-kyu-suave">#{posicao} na fila</p>
          <h3 className="mt-1 break-words text-xl font-bold text-kyu-texto">{nome}</h3>
          <p className="font-mono text-sm text-kyu-suave">{cnpj(item.cnpj)}</p>
        </div>
        <div className="shrink-0 sm:text-right">
          <p className="text-lg">
            Prioridade <strong>{decimal(item.prioridade)}</strong>
          </p>
          <p className="text-sm text-kyu-suave">
            Valor exposto <strong className="text-kyu-texto">{moeda(item.valor_exposto)}</strong>
          </p>
        </div>
      </div>
      <div className="mt-4">
        <ListaSinais sinais={item.sinais} />
      </div>
      <p className="mt-4">
        <Link to={`/fornecedores/${item.cnpj}`} className="foco font-semibold text-kyu-laranja underline">
          Abrir dossiê<span className="sr-only"> de {nome}</span>
        </Link>
      </p>
    </li>
  );
}

/** Fila priorizada de uma carteira (GET /carteiras/{id}/fila). A ordem vem pronta do backend. */
export function FilaPage() {
  const { id } = useParams();
  const estado = useLocation().state as EstadoCarteiraCriada | null;
  const fila = useFila(id);

  if (fila.isPending) return <Carregando texto="Carregando a fila…" />;
  if (fila.isError) {
    return (
      <div className="space-y-4">
        <TituloPagina numero="06" titulo="Fila da carteira" />
        <MensagemErro erro={fila.error} titulo="Não foi possível abrir a carteira" />
        <Link to="/carteiras" className="foco font-semibold text-kyu-laranja underline">
          Voltar para as carteiras
        </Link>
      </div>
    );
  }

  const { carteira, itens } = fila.data;
  const invalidos = estado?.cnpjsInvalidos ?? [];

  return (
    <div className="space-y-6">
      <TituloPagina numero="06" titulo="Fila da carteira">
        {carteira.nome} · {NOME_FINALIDADE[carteira.finalidade] ?? carteira.finalidade} · {itens.length} fornecedor
        {itens.length === 1 ? "" : "es"}
      </TituloPagina>

      {invalidos.length > 0 && (
        <p role="status" className="rounded-md bg-kyu-ambar-fundo p-4 font-semibold text-kyu-ambar">
          {avisoInvalidos(invalidos)}
        </p>
      )}

      <p className="cartao p-5 text-sm text-kyu-suave">
        Prioridade = soma do peso da gravidade × log10(1 + valor exposto). Pesos: forte 10, atenção 3, informativo 1.
        O fator de exposição vale no mínimo 1, para que uma sanção sem contrato vigente não vá para o fim da fila.
        Valor exposto é o valor vigente do fornecedor nos estados do seu acesso.
      </p>

      {itens.length === 0 ? (
        <p className="cartao p-5 text-kyu-suave">A carteira não tem fornecedores.</p>
      ) : (
        <ol className="space-y-4">
          {itens.map((item, i) => (
            <Item key={item.cnpj} item={item} posicao={i + 1} />
          ))}
        </ol>
      )}

      <p>
        <Link to="/carteiras" className="foco font-semibold text-kyu-laranja underline">
          Voltar para as carteiras
        </Link>
      </p>
    </div>
  );
}
