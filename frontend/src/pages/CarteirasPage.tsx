import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import type { Alerta, CarteiraListada, Finalidade } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { pode } from "../auth/permissoes";
import { Carregando } from "../components/Carregando";
import { MensagemErro } from "../components/MensagemErro";
import { Selo } from "../components/Selo";
import { TituloPagina } from "../components/TituloPagina";
import { useAlertas, useAtualizarAlerta } from "../features/alertas/hooks";
import { separarCnpjs, useCarteiras, useCriarCarteira } from "../features/carteiras/hooks";
import { GRAVIDADE, NOME_FINALIDADE, nomeSinal } from "../lib/apresentacao";
import { cnpj as formatarCnpj, dataCurta } from "../lib/formato";

const FINALIDADES = Object.keys(NOME_FINALIDADE) as Finalidade[];

/** Estado passado para a fila logo depois de criar a carteira. */
export interface EstadoCarteiraCriada {
  cnpjsInvalidos: string[];
}

function NovaCarteira() {
  const navegar = useNavigate();
  const criar = useCriarCarteira();
  const [nome, setNome] = useState("");
  const [finalidade, setFinalidade] = useState<Finalidade>("homologacao");
  const [texto, setTexto] = useState("");
  const cnpjs = separarCnpjs(texto);

  function enviar(e: FormEvent) {
    e.preventDefault();
    criar.mutate(
      { nome: nome.trim(), finalidade, cnpjs },
      {
        onSuccess: (criada) => {
          const estado: EstadoCarteiraCriada = { cnpjsInvalidos: criada.cnpjs_invalidos };
          navegar(`/carteiras/${criada.id}`, { state: estado });
        },
      },
    );
  }

  return (
    <section aria-labelledby="titulo-nova" className="cartao p-6">
      <h2 id="titulo-nova" className="text-xl font-bold text-kyu-texto">
        Nova carteira
      </h2>
      <p className="mt-1 text-sm text-kyu-suave">
        Cole os CNPJs dos fornecedores. A fila ordena quem olhar primeiro, com os sinais e as evidências.
      </p>
      <form onSubmit={enviar} className="mt-5 grid gap-5 lg:grid-cols-2">
        <div className="space-y-5">
          <div>
            <label htmlFor="nome-carteira" className="block font-semibold">
              Nome da carteira
            </label>
            <input
              id="nome-carteira"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              maxLength={120}
              required
              className="foco mt-2 w-full rounded-md border border-kyu-borda px-3 py-2"
            />
          </div>
          <div>
            <label htmlFor="finalidade" className="block font-semibold">
              Finalidade
            </label>
            <select
              id="finalidade"
              value={finalidade}
              onChange={(e) => setFinalidade(e.target.value as Finalidade)}
              className="foco mt-2 w-full rounded-md border border-kyu-borda bg-white px-3 py-2"
            >
              {FINALIDADES.map((f) => (
                <option key={f} value={f}>
                  {NOME_FINALIDADE[f]}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label htmlFor="cnpjs" className="block font-semibold">
            CNPJs <span className="font-normal text-kyu-suave">(um por linha ou separados por vírgula)</span>
          </label>
          <textarea
            id="cnpjs"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            rows={5}
            required
            aria-describedby="contagem-cnpjs"
            className="foco mt-2 w-full rounded-md border border-kyu-borda px-3 py-2 font-mono text-sm"
          />
          <p id="contagem-cnpjs" className="mt-1 text-sm text-kyu-suave">
            {cnpjs.length} CNPJ{cnpjs.length === 1 ? "" : "s"} na lista
          </p>
        </div>
        <div className="lg:col-span-2">
          {criar.isError && (
            <div className="mb-4">
              <MensagemErro erro={criar.error} titulo="Não foi possível criar a carteira" />
            </div>
          )}
          <button type="submit" className="botao-primario" disabled={criar.isPending || cnpjs.length === 0 || !nome.trim()}>
            {criar.isPending ? "Criando…" : "Criar carteira"}
          </button>
        </div>
      </form>
    </section>
  );
}

function SinalDoAlerta({ sinal }: { sinal: Alerta["sinal"] }) {
  if (!sinal) return <span className="text-kyu-suave">Sinal de UF fora do seu escopo</span>;
  const gravidade = GRAVIDADE[sinal.gravidade] ?? GRAVIDADE.info;
  return (
    <div>
      <p className="flex flex-wrap items-center gap-2 font-semibold">
        {nomeSinal(sinal.tipo)}
        {sinal.uf && <span className="font-normal text-kyu-suave">em {sinal.uf}</span>}
        <Selo tom={gravidade.tom}>{gravidade.rotulo}</Selo>
      </p>
      <p className="mt-1 text-sm">{sinal.explicacao}</p>
      {sinal.id === null && (
        <p className="mt-1 text-sm text-kyu-suave">Deixou de valer no último cálculo dos sinais.</p>
      )}
    </div>
  );
}

/** Alertas abertos (GET /alertas?status=aberto): sinal novo de fornecedor de carteira. Some se não houver nenhum. */
function AcoesDoAlerta({ alerta }: { alerta: Alerta }) {
  const atualizar = useAtualizarAlerta();
  const rotulo = `${formatarCnpj(alerta.cnpj)}, ${alerta.sinal ? nomeSinal(alerta.sinal.tipo) : "sinal fora do seu escopo"}`;
  return (
    <div className="flex flex-wrap gap-2">
      <button
        type="button"
        aria-label={`Marcar como visto: ${rotulo}`}
        className="botao-secundario"
        disabled={atualizar.isPending}
        onClick={() => atualizar.mutate({ id: alerta.id, status: "visto" })}
      >
        Marcar como visto
      </button>
      <button
        type="button"
        aria-label={`Resolver: ${rotulo}`}
        className="botao-secundario"
        disabled={atualizar.isPending}
        onClick={() => atualizar.mutate({ id: alerta.id, status: "resolvido" })}
      >
        Resolver
      </button>
      {atualizar.isError && <MensagemErro erro={atualizar.error} titulo="Não foi possível atualizar o alerta" />}
    </div>
  );
}

function AlertasAbertos({ carteiras, podeAtualizar }: { carteiras: CarteiraListada[]; podeAtualizar: boolean }) {
  const alertas = useAlertas("aberto");
  if (!alertas.isSuccess || alertas.data.length === 0) return null;
  const nomes = new Map(carteiras.map((c) => [c.id, c.nome]));
  const n = alertas.data.length;
  return (
    <section aria-labelledby="titulo-alertas" className="cartao p-6">
      <h2 id="titulo-alertas" className="text-xl font-bold text-kyu-texto">
        Alertas abertos
      </h2>
      <p className="mt-1 text-sm text-kyu-suave">
        {n} sina{n === 1 ? "l" : "is"} para investigar em fornecedores das suas carteiras. O alerta nasce quando a
        carteira é criada ou a fila é aberta depois de um novo cálculo dos sinais.
      </p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[40rem] border-collapse text-left">
          <caption className="sr-only">Alertas abertos do cliente</caption>
          <thead className="tabela-cabecalho">
            <tr>
              <th scope="col" className="rounded-l-md px-4 py-3">Fornecedor</th>
              <th scope="col" className="px-4 py-3">Sinal</th>
              <th scope="col" className="px-4 py-3">Carteira</th>
              <th scope="col" className={`px-4 py-3 ${podeAtualizar ? "" : "rounded-r-md"}`}>Desde</th>
              {podeAtualizar && (
                <th scope="col" className="rounded-r-md px-4 py-3">
                  <span className="sr-only">Ações</span>
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {alertas.data.map((a) => (
              <tr key={a.id} className="border-b border-kyu-linha align-top">
                <th scope="row" className="px-4 py-4 font-normal">
                  <Link to={`/fornecedores/${a.cnpj}`} className="foco font-mono text-kyu-laranja underline">
                    {formatarCnpj(a.cnpj)}
                  </Link>
                </th>
                <td className="px-4 py-4">
                  <SinalDoAlerta sinal={a.sinal} />
                </td>
                <td className="px-4 py-4">
                  {a.carteira_id ? (
                    <Link to={`/carteiras/${a.carteira_id}`} className="foco text-kyu-laranja underline">
                      {nomes.get(a.carteira_id) ?? "Abrir a fila"}
                    </Link>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-4 py-4">{dataCurta(a.criado_em)}</td>
                {podeAtualizar && (
                  <td className="px-4 py-4">
                    <AcoesDoAlerta alerta={a} />
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/** Tela 06: carteiras do cliente e criação por colagem de CNPJs (GET e POST /carteiras). */
export function CarteirasPage() {
  const { usuario } = useAuth();
  const carteiras = useCarteiras();
  if (!usuario) return null;

  return (
    <div className="space-y-6">
      <TituloPagina numero="06" titulo="Carteiras e fila">
        Fornecedores agrupados por finalidade, com a fila de quem olhar primeiro.
      </TituloPagina>

      <AlertasAbertos carteiras={carteiras.data ?? []} podeAtualizar={pode(usuario.perfil, "atualizar_alerta")} />

      {pode(usuario.perfil, "editar_carteira") && <NovaCarteira />}

      <section aria-labelledby="titulo-carteiras" className="cartao p-6">
        <h2 id="titulo-carteiras" className="text-xl font-bold text-kyu-texto">
          Carteiras
        </h2>
        {carteiras.isPending ? (
          <Carregando texto="Carregando as carteiras…" />
        ) : carteiras.isError ? (
          <div className="mt-4">
            <MensagemErro erro={carteiras.error} titulo="Não foi possível carregar as carteiras" />
          </div>
        ) : carteiras.data.length === 0 ? (
          <p className="mt-4 text-kyu-suave">Nenhuma carteira criada ainda.</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[36rem] border-collapse text-left">
              <caption className="sr-only">Carteiras do cliente {usuario.tenant.nome}</caption>
              <thead className="tabela-cabecalho">
                <tr>
                  <th scope="col" className="rounded-l-md px-4 py-3">Carteira</th>
                  <th scope="col" className="px-4 py-3">Finalidade</th>
                  <th scope="col" className="px-4 py-3">Fornecedores</th>
                  <th scope="col" className="rounded-r-md px-4 py-3">Criada em</th>
                </tr>
              </thead>
              <tbody>
                {carteiras.data.map((c) => (
                  <tr key={c.id} className="border-b border-kyu-linha">
                    <th scope="row" className="px-4 py-4 font-semibold">
                      <Link to={`/carteiras/${c.id}`} className="foco text-kyu-laranja underline">
                        {c.nome}
                      </Link>
                    </th>
                    <td className="px-4 py-4">{NOME_FINALIDADE[c.finalidade] ?? c.finalidade}</td>
                    <td className="px-4 py-4">{c.n_itens}</td>
                    <td className="px-4 py-4">{dataCurta(c.criada_em)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
