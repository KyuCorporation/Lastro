import { Selo } from "../components/Selo";
import { TituloPagina } from "../components/TituloPagina";

// Conteúdo de docs/catalogo-fontes.md. Sem contagens nem status de sincronização: GET /fontes ainda não existe
// (T26), e o design pede para não exibir como real o que não veio de uma sincronização.
const CATALOGO = [
  { conjunto: "Contratos", campos: "Identificador, órgão, fornecedor, objeto, valor, vigência" },
  { conjunto: "Despesas / pagamentos", campos: "Identificador, órgão, favorecido, valor, data (empenho e liquidação)" },
  { conjunto: "Fornecedores", campos: "Identificador, nome/razão social, CNPJ (pessoa física é descartada)" },
];

const COMPLEMENTARES = [
  { nome: "PNCP", uso: "contratos das outras UFs, como AL na demonstração" },
  { nome: "CEIS e CNEP", uso: "sanções de empresas, nacionais" },
];

const ETAPAS = ["Fonte TCE-PE / TomeConta", "Captura", "Normalização", "Catálogo KYU"];

/** Tela 05 do design: fonte e catálogo de dados. */
export function FontesPage() {
  return (
    <div className="space-y-6">
      <TituloPagina numero="05" titulo="Fonte e catálogo de dados">
        Uma origem institucional no MVP: TCE-PE · TomeConta. A integração deve ser validada.
      </TituloPagina>

      <section aria-labelledby="titulo-fonte" className="cartao grid gap-6 p-6 md:grid-cols-[1.4fr_1fr]">
        <div>
          <h2 id="titulo-fonte" className="text-xl font-bold text-kyu-texto">
            Fonte configurada
          </h2>
          <p className="mt-3">
            <Selo tom="verde">Fonte selecionada</Selo>
          </p>
          <p className="mt-4 text-2xl font-bold text-kyu-texto">Tribunal de Contas do Estado de Pernambuco (TCE-PE)</p>
          <p className="mt-3 text-lg text-kyu-texto">Portal de referência: TomeConta</p>
          <p className="mt-1 text-sm text-kyu-suave">
            A disponibilidade e os campos de cada conjunto precisam ser confirmados antes da captura.
          </p>
        </div>
        <div className="md:pt-14">
          <p className="text-sm font-semibold text-kyu-suave">Status da integração</p>
          <p className="mt-2 text-lg font-bold text-kyu-ambar">A validar · API / endpoint</p>
          <p className="mt-2 text-sm text-kyu-suave">
            A API de dados abertos só responde a IP brasileiro. Até a amostra real, a demonstração usa registros
            sintéticos no formato previsto.
          </p>
        </div>
      </section>

      <section aria-labelledby="titulo-catalogo" className="cartao p-6">
        <h2 id="titulo-catalogo" className="text-xl font-bold text-kyu-texto">
          Catálogo previsto para o MVP
        </h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[36rem] border-collapse text-left">
            <caption className="sr-only">Conjuntos do TCE-PE e os campos que o catálogo mapeia</caption>
            <thead className="tabela-cabecalho">
              <tr>
                <th scope="col" className="rounded-l-md px-4 py-3">Conjunto</th>
                <th scope="col" className="px-4 py-3">Campos a mapear</th>
                <th scope="col" className="rounded-r-md px-4 py-3">Situação</th>
              </tr>
            </thead>
            <tbody>
              {CATALOGO.map((linha) => (
                <tr key={linha.conjunto} className="border-b border-kyu-linha">
                  <th scope="row" className="px-4 py-4 font-bold">{linha.conjunto}</th>
                  <td className="px-4 py-4">{linha.campos}</td>
                  <td className="px-4 py-4 text-sm font-bold text-kyu-ambar">A confirmar</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-sm text-kyu-suave">
          Fontes complementares já integradas:{" "}
          {COMPLEMENTARES.map((f, i) => (
            <span key={f.nome}>
              {i > 0 && "; "}
              <strong className="text-kyu-texto">{f.nome}</strong> ({f.uso})
            </span>
          ))}
          .
        </p>
      </section>

      <section aria-labelledby="titulo-pipeline" className="cartao p-6">
        <h2 id="titulo-pipeline" className="text-xl font-bold text-kyu-texto">
          Pipeline de dados
        </h2>
        <ol className="mt-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          {ETAPAS.map((etapa, i) => (
            <li key={etapa} className="flex items-center gap-3 text-lg font-bold text-kyu-texto">
              <span>
                <span aria-hidden="true">{String(i + 1).padStart(2, "0")} </span>
                {etapa}
              </span>
              {i < ETAPAS.length - 1 && (
                <span aria-hidden="true" className="hidden text-xl text-kyu-laranja md:inline">
                  →
                </span>
              )}
            </li>
          ))}
        </ol>
        <p className="mt-5 text-kyu-suave">
          Guardar data da captura, identificador de origem, campos normalizados e erros de importação.
        </p>
        <p className="mt-5 font-semibold text-kyu-vermelho">
          Não exibir contagens ou status como reais até a primeira sincronização bem-sucedida.
        </p>
      </section>
    </div>
  );
}
