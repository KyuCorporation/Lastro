import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import type { Finalidade } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { pode } from "../auth/permissoes";
import { Carregando } from "../components/Carregando";
import { MensagemErro } from "../components/MensagemErro";
import { TituloPagina } from "../components/TituloPagina";
import { separarCnpjs, useCarteiras, useCriarCarteira } from "../features/carteiras/hooks";
import { NOME_FINALIDADE } from "../lib/apresentacao";
import { dataCurta } from "../lib/formato";

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
