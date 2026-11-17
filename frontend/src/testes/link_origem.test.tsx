// LinkOrigem: o mesmo componente para citações, recibo, dossiê e evidências de sinais.

import { render, screen } from "@testing-library/react";

import { LinkOrigem } from "../components/LinkOrigem";

describe("LinkOrigem", () => {
  it("abre só http(s), em nova aba, com o aviso para leitor de tela", () => {
    render(<LinkOrigem url="https://pncp.gov.br/contrato/1">Abrir na fonte oficial</LinkOrigem>);
    const link = screen.getByRole("link", { name: "Abrir na fonte oficial (abre a fonte oficial em nova aba)" });
    expect(link).toHaveAttribute("href", "https://pncp.gov.br/contrato/1");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("sem link público mostra o texto padrão", () => {
    render(<LinkOrigem url={null}>Registro 01</LinkOrigem>);
    expect(screen.getByText("Registro 01 · sem link público")).toBeInTheDocument();
  });

  it("aceita outro texto para quando não há link (citações)", () => {
    render(
      <LinkOrigem url="javascript:alert(1)" semLink="Registro sem link público">
        Abrir na fonte oficial
      </LinkOrigem>,
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("Registro sem link público")).toBeInTheDocument();
    expect(screen.queryByText(/Abrir na fonte oficial/)).not.toBeInTheDocument();
  });
});
