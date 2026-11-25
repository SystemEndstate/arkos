"""banca_nota.py - nota e veredito da banca (as 4 personas usam o mesmo script).

Nota = média ponderada da rubrica (0–10 por critério), arredondada a 1 casa.
Critério sem nota (null) sai da conta, os pesos restantes são renormalizados e a nota
fica marcada 'parcial'.

Regra do veredito (igual nas 4 bancas):
  parar                 nota < 4, ou premissa de impacto alto refutada sem plano de troca
  seguir com condições  4 <= nota < 7, ou risco crítico sem teste com data
  seguir                nota >= 7 e todo risco crítico com teste com data

Uso:
  python banca_nota.py --persona investidor --rubrica '{"tamanho": 7, ...}' [--premissas premissas.yaml]
  python banca_nota.py --entrada entrada.json
    entrada.json: {"persona": "...", "rubrica": {...},
                   "refutadas_altas_sem_troca": [..]?, "criticos_sem_teste": [..]?}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PESOS = {
    "investidor": {"tamanho": 0.20, "retorno": 0.30, "risco": 0.20, "defensabilidade": 0.15, "por_que_agora": 0.15},
    "cetico": {"evidencia": 0.30, "cobertura": 0.20, "tese_contraria": 0.20, "realismo": 0.15, "taxa_base": 0.15},
    "cliente": {"dor": 0.25, "clareza": 0.20, "preco": 0.20, "ansiedade_habito": 0.20, "objecoes": 0.15},
    "operador": {"capacidade": 0.25, "custo_servir": 0.25, "gargalo": 0.20, "dependencias": 0.15,
                 "pessoas_conformidade": 0.15},
}
VEREDITOS = ("seguir", "seguir com condições", "parar")


def nota(persona: str, rubrica: dict) -> dict:
    if persona not in PESOS:
        raise ValueError(f"persona desconhecida: {persona}")
    pesos = PESOS[persona]
    extras = set(rubrica) - set(pesos)
    if extras:
        raise ValueError(f"critérios fora da rubrica de {persona}: {sorted(extras)}")
    usados = {}
    for k, peso in pesos.items():
        v = rubrica.get(k)
        if v is None:
            continue
        if not isinstance(v, (int, float)) or not 0 <= v <= 10:
            raise ValueError(f"{k}: nota deve ficar entre 0 e 10")
        usados[k] = (float(v), peso)
    if not usados:
        raise ValueError("rubrica vazia")
    soma_pesos = sum(p for _, p in usados.values())
    valor = sum(v * p for v, p in usados.values()) / soma_pesos
    faltando = [k for k in pesos if k not in usados]
    return {"nota": round(valor + 1e-9, 1), "parcial": bool(faltando), "faltando": faltando}


def veredito(n: float, refutadas_altas_sem_troca: list, criticos_sem_teste: list) -> dict:
    motivos = []
    if n < 4:
        motivos.append(f"nota {n} < 4")
    if refutadas_altas_sem_troca:
        motivos.append("premissa de impacto alto refutada sem plano de troca: " + ", ".join(refutadas_altas_sem_troca))
    if motivos:
        return {"veredito": "parar", "motivos": motivos}
    if n < 7:
        motivos.append(f"nota {n} entre 4 e 6,9")
    if criticos_sem_teste:
        motivos.append("risco crítico sem teste com data: " + ", ".join(criticos_sem_teste))
    if motivos:
        return {"veredito": "seguir com condições", "motivos": motivos}
    return {"veredito": "seguir", "motivos": [f"nota {n} >= 7 e todo risco crítico com teste com data"]}


def avaliar(persona: str, rubrica: dict, refutadas: list | None = None, sem_teste: list | None = None) -> dict:
    r = nota(persona, rubrica)
    r.update(veredito(r["nota"], refutadas or [], sem_teste or []))
    r["persona"] = persona
    return r


def _main(argv: list[str]) -> int:
    def opt(nome):
        return argv[argv.index(nome) + 1] if nome in argv else None

    if opt("--entrada"):
        e = json.loads(Path(opt("--entrada")).read_text(encoding="utf-8"))
        persona, rubrica = e["persona"], e["rubrica"]
        refut, sem = e.get("refutadas_altas_sem_troca", []), e.get("criticos_sem_teste", [])
    elif opt("--persona") and opt("--rubrica"):
        persona, rubrica = opt("--persona"), json.loads(opt("--rubrica"))
        refut, sem = [], []
    else:
        print(__doc__)
        return 2
    if opt("--premissas"):
        from criticos import criticos, refutadas_altas_sem_troca, sem_teste_com_data
        from premissas import carregar
        itens = carregar(opt("--premissas"))
        refut = refutadas_altas_sem_troca(itens)
        sem = sem_teste_com_data(criticos(itens))
    print(json.dumps(avaliar(persona, rubrica, refut, sem), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
