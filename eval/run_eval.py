"""Harness de avaliação. Uso: python run_eval.py gabarito|ataques

A implementar. Contrato de saída: reports/<modo>.json com
{"gerado_em", "n_casos", "metricas": {...}, "casos": [{id, ok, motivo}]} e reports/resumo.md.
"""
import sys

if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "gabarito"
    raise SystemExit(f"run_eval.py ({modo}) ainda não implementado: ver SPEC §14")
