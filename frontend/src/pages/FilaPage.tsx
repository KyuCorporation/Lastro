import { Link, useLocation, useParams } from "react-router-dom";

import type { ItemFila } from "../api/types";
import { Carregando } from "../components/Carregando";
import { MensagemErro } from "../components/MensagemErro";
import { Selo } from "../components/Selo";
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

function Item({ item, posicao, carteiraId }: { item: ItemFila; posicao: number; carteiraId: string }) {
  const nome = item.razao_social ?? "Razão social não informada";
  const pergunta = `Qual o resumo do fornecedor ${cnpj(item.cnpj)}?`;
  const consulta = `/?${new URLSearchParams({ carteira: carteiraId, pergunta }).toString()}`;
  // Nenhum dado visível para este CNPJ: o dossiê responderia "não encontrado".
  const semRegistros = item.razao_social === null && item.sinais.length === 0 && Number(item.valor_exposto) === 0;
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
      {semRegistros ? (
        <p className="mt-4">
          <Selo tom="neutro">Sem registros nas fontes autorizadas para você</Selo>
        </p>
      ) : (
        <>
          <div className="mt-4">
            <ListaSinais sinais={item.sinais} />
          </div>
          <Atalhos item={item} nome={nome} consulta={consulta} />
        </>
      )}
    </li>
  );
}

function Atalhos({ item, nome, consulta }: { item: ItemFila; nome: string; consulta: string }) {
  return (
    <p className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
      <Link to={`/fornecedores/${item.cnpj}`} className="foco font-semibold text-kyu-laranja underline">
        Abrir dossiê<span className="sr-only"> de {nome}</span>
      </Link>
      <Link to={consulta} className="foco font-semibold text-kyu-laranja underline">
        Perguntar sobre este fornecedor<span className="sr-only">: {nome}, no contexto desta carteira</span>
      </Link>
    </p>
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
        <TituloPagina titulo="Fila da carteira" />
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
      <TituloPagina titulo="Fila da carteira">
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
        Valor exposto é o valor vigente do fornecedor nos estados do seu acesso. Os sinais vêm do último cálculo da
        base; a data de cada um está no dossiê.
      </p>

      {itens.length === 0 ? (
        <p className="cartao p-5 text-kyu-suave">A carteira não tem fornecedores.</p>
      ) : (
        <ol className="space-y-4">
          {itens.map((item, i) => (
            <Item key={item.cnpj} item={item} posicao={i + 1} carteiraId={carteira.id} />
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
