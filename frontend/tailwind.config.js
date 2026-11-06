/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Identidade KYU (telas do design): marrom escuro na lateral, laranja da marca, fundo creme.
      // Contraste conferido para texto normal (AA, 4,5:1): branco sobre laranja e escuro, e os pares de selo.
      colors: {
        kyu: {
          escuro: "#2B1A14",
          laranja: "#B5471D",
          "laranja-forte": "#963A17",
          marca: "#C8602D",
          creme: "#F6F2EE",
          cartao: "#FFFFFF",
          borda: "#E6DED6",
          linha: "#EFE9E3",
          cabecalho: "#F4EFEA",
          texto: "#1E2227",
          suave: "#5F5751",
          verde: "#1D6A42",
          "verde-fundo": "#E2F1E7",
          vermelho: "#B0261A",
          "vermelho-fundo": "#FBE6E1",
          ambar: "#875200",
          "ambar-fundo": "#FDEEDA",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
};
