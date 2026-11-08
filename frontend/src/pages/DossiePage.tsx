import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import type { ContratoDossie, Dossie } from "../api/types";
import { Carregando } from "../components/Carregando";
import { LinkOrigem } from "../components/LinkOrigem";
import { MensagemErro } from "../components/MensagemErro";
import { Selo } from "../components/Selo";
import { TituloPagina } from "../components/TituloPagina";
import { useDossie } from "../features/fornecedores/useDossie";
import { ListaSinais } from "../features/sinais/ListaSinais";
import { nomeUf } from "../lib/apresentacao";
import { cnpj, dataCurta, dataHora, moeda, nomeFonte } from "../lib/formato";

function Secao({ id, titulo, children }: { id: string; titulo: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="cartao p-6">
      <h2 id={id} className="text-xl font-bold text-kyu-texto">
        {titulo}
      </h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Tabela({ legenda, colunas, children }: { legenda: string; colunas: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[44rem] border-collapse text-left">
        <caption className="sr-only">{legenda}</caption>
        <thead className="tabela-cabecalho">
          <tr>
            {colunas.map((c, i) => (
              <th
                key={c}
                scope="col"
                className={`px-4 py-3 ${i === 0 ? "rounded-l-md" : ""} ${i === colunas.length - 1 ? "rounded-r-md" : ""}`}
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

const CELULA = "px-4 py-4 align-top";

function Contratos({ contratos, legenda, vazio }: { contratos: ContratoDossie[]; legenda: string; vazio: string }) {
  if (contratos.length === 0) return <p className="text-kyu-suave">{vazio}</p>;
  return (
    <Tabela legenda={legenda} colunas={["Registro", "Órgão", "Objeto", "Valor", "Vigência até"]}>
      {contratos.map((c) => (
        <tr key={c.id} className="border-b border-kyu-linha">
          <td className={`${CELULA} break-all`}>
            <LinkOrigem url={c.url_origem}>{c.id_origem}</LinkOrigem>
            <span className="block text-sm text-kyu-suave">
              {nomeFonte(c.fonte_id)} · {c.uf}
            </span>
          </td>
          <td className={CELULA}>{c.orgao_nome ?? "Órgão não informado"}</td>
          <td className={`${CELULA} max-w-sm`}>{c.objeto ?? "—"}</td>
          <td className={`${CELULA} whitespace-nowrap font-semibold`}>{c.valor_global ? moeda(c.valor_global) : "—"}</td>
          <td className={`${CELULA} whitespace-nowrap`}>{c.vigencia_fim ? dataCurta(c.vigencia_fim) : "—"}</td>
        </tr>
      ))}
    </Tabela>
  );
}

function Conteudo({ d }: { d: Dossie }) {
  const n = d.sinais.length;
  return (
    <>
      <section aria-labelledby="titulo-fornecedor" className="cartao flex flex-wrap items-start justify-between gap-4 p-7">
        <div>
          <h2 id="titulo-fornecedor" className="text-2xl font-extrabold text-kyu-texto sm:text-3xl">
            {d.fornecedor.razao_social ?? "Razão social não informada"}
          </h2>
          <p className="mt-2 font-mono text-kyu-suave">CNPJ {cnpj(d.fornecedor.cnpj)}</p>
          {d.fornecedor.uf_sede && <p className="text-kyu-suave">Sede em {nomeUf(d.fornecedor.uf_sede)}</p>}
        </div>
        <Selo tom={n === 0 ? "verde" : "ambar"}>
          {n === 0 ? "Nenhum sinal para investigar" : `${n} sina${n === 1 ? "l" : "is"} para investigar`}
        </Selo>
      </section>

      <Secao id="titulo-resumo" titulo="Resumo por estado">
        {d.resumo_por_uf.length === 0 ? (
          <p className="text-kyu-suave">Nenhum contrato ou pagamento nos estados do seu acesso.</p>
        ) : (
          <Tabela
            legenda="Contratos e pagamentos por estado"
            colunas={["Estado", "Contratos", "Valor contratado", "Valor vigente", "Pagamentos", "Valor pago", "Valor empenhado"]}
          >
            {d.resumo_por_uf.map((r) => (
              <tr key={r.uf} className="border-b border-kyu-linha">
                <th scope="row" className={`${CELULA} font-semibold`}>
                  {nomeUf(r.uf)}
                </th>
                <td className={CELULA}>{r.n_contratos}</td>
                <td className={`${CELULA} whitespace-nowrap`}>{moeda(r.valor_contratado)}</td>
                <td className={`${CELULA} whitespace-nowrap`}>{moeda(r.valor_vigente)}</td>
                <td className={CELULA}>{r.n_pagamentos}</td>
                <td className={`${CELULA} whitespace-nowrap`}>{moeda(r.valor_pago)}</td>
                <td className={`${CELULA} whitespace-nowrap`}>{moeda(r.valor_empenhado)}</td>
              </tr>
            ))}
          </Tabela>
        )}
      </Secao>

      <Secao id="titulo-sinais" titulo="Sinais para investigar">
        <ListaSinais sinais={d.sinais} />
      </Secao>

      <Secao id="titulo-vigentes" titulo="Contratos vigentes">
        <Contratos contratos={d.contratos_vigentes} legenda="Contratos vigentes, com o registro de origem"
          vazio="Nenhum contrato vigente nos estados do seu acesso." />
      </Secao>

      <Secao id="titulo-vencendo" titulo="Vencendo em 180 dias">
        <Contratos contratos={d.vencendo_180d} legenda="Contratos que terminam nos próximos 180 dias"
          vazio="Nenhum contrato termina nos próximos 180 dias." />
      </Secao>

      <Secao id="titulo-sancoes" titulo="Sanções">
        {d.sancoes.length === 0 ? (
          <p className="text-kyu-suave">Nenhuma sanção no CEIS ou no CNEP.</p>
        ) : (
          <Tabela legenda="Sanções do fornecedor, com o registro de origem"
            colunas={["Registro", "Tipo", "Órgão sancionador", "Período", "Situação"]}>
            {d.sancoes.map((s) => (
              <tr key={s.id} className="border-b border-kyu-linha">
                <td className={`${CELULA} break-all`}>
                  <LinkOrigem url={s.url_origem}>{s.id_origem}</LinkOrigem>
                  <span className="block text-sm text-kyu-suave">{nomeFonte(s.fonte_id)}</span>
                </td>
                <td className={CELULA}>{s.tipo ?? "—"}</td>
                <td className={CELULA}>{s.orgao_sancionador ?? "—"}</td>
                <td className={`${CELULA} whitespace-nowrap`}>
                  {s.data_inicio ? dataCurta(s.data_inicio) : "—"} a {s.data_fim ? dataCurta(s.data_fim) : "sem fim"}
                </td>
                <td className={CELULA}>
                  <Selo tom={s.vigente ? "vermelho" : "neutro"}>{s.vigente ? "Vigente" : "Encerrada"}</Selo>
                </td>
              </tr>
            ))}
          </Tabela>
        )}
      </Secao>

      <Secao id="titulo-socios" titulo="Sócios">
        {d.socios === null ? (
          <p className="text-kyu-suave">Seu perfil não acessa o quadro societário.</p>
        ) : d.socios.length === 0 ? (
          <p className="text-kyu-suave">Nenhum sócio na fonte consultada.</p>
        ) : (
          <ul className="space-y-2">
            {d.socios.map((s, i) => (
              <li key={`${s.socio_exibicao}-${i}`}>
                <span className="font-mono">{s.socio_exibicao}</span>{" "}
                <span className="text-sm text-kyu-suave">
                  · {s.socio_tipo === "PF" ? "pessoa física, exibição mascarada" : "pessoa jurídica"} ·{" "}
                  {nomeFonte(s.fonte_id)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Secao>

      <Secao id="titulo-fontes" titulo="Fontes consultadas">
        {d.fontes.length === 0 ? (
          <p className="text-kyu-suave">Nenhuma linha de fonte no dossiê.</p>
        ) : (
          <ul className="space-y-2">
            {d.fontes.map((f) => (
              <li key={f.fonte_id}>
                <span className="font-semibold">{f.nome}</span>{" "}
                <span className="text-kyu-suave">· coleta mais recente em {dataHora(f.coletado_em)}</span>
                {f.sintetico && <span className="ml-2"><Selo tom="neutro">Registro sintético de teste</Selo></span>}
              </li>
            ))}
          </ul>
        )}
      </Secao>
    </>
  );
}

/** Tela 07: dossiê do fornecedor (GET /fornecedores/{cnpj}/dossie). Cada item leva à linha de origem. */
export function DossiePage() {
  const { cnpj: param } = useParams();
  const dossie = useDossie(param);

  return (
    <div className="space-y-6">
      <TituloPagina numero="07" titulo="Dossiê do fornecedor">
        Tudo o que as fontes autorizadas registram sobre o fornecedor, com o link de cada registro.
      </TituloPagina>
      {dossie.isPending ? (
        <Carregando texto="Montando o dossiê…" />
      ) : dossie.isError ? (
        <MensagemErro erro={dossie.error} titulo="Não foi possível montar o dossiê" />
      ) : (
        <Conteudo d={dossie.data} />
      )}
      <p>
        <Link to="/carteiras" className="foco font-semibold text-kyu-laranja underline">
          Voltar para as carteiras
        </Link>
      </p>
    </div>
  );
}
