import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";

import type { ConsultaSaida, Recibo } from "../../api/types";
import { SeloSintetico } from "../../components/SeloSintetico";
import { Selo } from "../../components/Selo";
import { STATUS_CONSULTA } from "../../lib/apresentacao";
import { nomeTabela } from "../../lib/formato";
import { consultouSancoes, moeda, periodo, valorPrincipal } from "../recibo/leitura";
import { IntegridadeConsulta } from "./IntegridadeConsulta";
import { ListaCitacoes } from "./ListaCitacoes";
import { TextoResposta } from "./TextoResposta";

interface Props {
  resultado: ConsultaSaida;
  simulado: boolean;
  /** Recibo da resposta (GET /recibos/{id}), quando houver e já tiver chegado. */
  recibo?: Recibo;
  ufs: string[];
}

function rotuloValor(origem: string): string {
  return origem.includes("pagamentos") ? "Valor pago registrado" : "Valor total registrado";
}

function ResumoDaConsulta({ recibo }: { recibo: Recibo }) {
  const c = recibo.conteudo;
  const tipos = [...new Set(c.linhas.map((l) => nomeTabela(l.tabela).toLowerCase()))];
  const n = c.execucao.n_linhas;
  const p = periodo(c);
  return (
    <div className="mt-5 border-t border-kyu-linha pt-5">
      <h3 className="text-sm font-semibold text-kyu-suave">Resumo da consulta</h3>
      <ul className="mt-3 list-inside list-disc space-y-1.5 text-kyu-texto">
        <li>
          {n} registro{n === 1 ? "" : "s"}
          {tipos.length > 0 && ` de ${tipos.join(" e ")}`} encontrado{n === 1 ? "" : "s"}
        </li>
        {p && <li>Período considerado: {p}</li>}
        <li>
          {consultouSancoes(c)
            ? "Sanções consultadas no CEIS e no CNEP"
            : "Nenhuma informação de sanção foi consultada nesta busca"}
        </li>
      </ul>
    </div>
  );
}

/** Resultado da consulta (tela 01): resposta com evidências à esquerda, integridade à direita. */
export function ResultadoConsulta({ resultado, simulado, recibo, ufs }: Props) {
  const titulo = useRef<HTMLHeadingElement>(null);
  const apresentacao = STATUS_CONSULTA[resultado.status] ?? STATUS_CONSULTA.erro;
  const idCitacao = (n: number) => `citacao-${resultado.consulta_id}-${n}`;
  const valor = recibo ? valorPrincipal(recibo.conteudo) : null;
  const idTitulo = `titulo-resultado-${resultado.consulta_id}`;

  // Leva o foco para a resposta: quem usa teclado ou leitor de tela chega direto nela.
  useEffect(() => titulo.current?.focus(), [resultado.consulta_id]);

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1.85fr)_minmax(0,1fr)]">
      <section aria-labelledby={idTitulo} className="cartao p-6">
        <h2 id={idTitulo} ref={titulo} tabIndex={-1} className="foco mb-4 inline-block rounded-md">
          <Selo tom={apresentacao.tom}>{apresentacao.selo}</Selo>
        </h2>
        {(resultado.sintetico || simulado) && (
          <div className="mb-4">
            <SeloSintetico simulado={simulado} />
          </div>
        )}
        <TextoResposta texto={resultado.resposta} idCitacao={idCitacao} />
        {valor && (
          <p className="mt-2 text-xl text-kyu-texto">
            {rotuloValor(valor.origem)}: {moeda(valor.valor)}
          </p>
        )}

        {recibo && <ResumoDaConsulta recibo={recibo} />}
        <ListaCitacoes citacoes={resultado.citacoes} idCitacao={idCitacao} />

        {resultado.status === "respondida" || resultado.status === "abstencao" ? (
          <p className="mt-6 text-sm text-kyu-suave">A resposta considera somente os registros disponíveis na base KYU.</p>
        ) : null}
        {resultado.recibo_id && (
          <p className="mt-3">
            <Link to={`/recibos/${resultado.recibo_id}`} className="botao-primario inline-block px-10 py-2 text-sm">
              Ver evidências
            </Link>
          </p>
        )}
      </section>

      <IntegridadeConsulta resultado={resultado} recibo={recibo} ufs={ufs} />
    </div>
  );
}
