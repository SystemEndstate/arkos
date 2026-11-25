"""criticos.py - riscos críticos do registro de premissas (especificação interna).

Crítica = impacto alto E confiança < 0,5 E status diferente de 'validada'.
Ordem: menor confiança primeiro; empate por id.

Uso:
  python criticos.py premissas.yaml [--categorias cliente,preco] [--sem-teste]
Saída: JSON {"total": n, "criticos": [...], "sem_teste_com_data": [ids]}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from premissas import carregar, critica  # noqa: E402


def criticos(itens: list[dict], categorias: set[str] | None = None) -> list[dict]:
    lista = [p for p in itens if critica(p) and (not categorias or p.get("categoria") in categorias)]
    return sorted(lista, key=lambda p: (float(p["confianca"]), str(p["id"])))


def sem_teste_com_data(lista: list[dict]) -> list[str]:
    """Críticos sem 'teste' ou sem 'prazo_teste' (entra na regra do veredito da banca)."""
    return [p["id"] for p in lista if not p.get("teste") or not p.get("prazo_teste")]


def refutadas_altas_sem_troca(itens: list[dict]) -> list[str]:
    """Impacto alto refutada sem 'substituida_por' (plano de troca)."""
    return [p["id"] for p in itens
            if p.get("impacto") == "alto" and p.get("status") == "refutada" and not p.get("substituida_por")]


def _main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cats = None
    if "--categorias" in argv:
        cats = set(argv[argv.index("--categorias") + 1].split(","))
    itens = carregar(argv[0])
    lista = criticos(itens, cats)
    saida = {"total": len(lista), "criticos": lista,
             "sem_teste_com_data": sem_teste_com_data(lista),
             "refutadas_altas_sem_troca": refutadas_altas_sem_troca(itens)}
    print(json.dumps(saida, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
