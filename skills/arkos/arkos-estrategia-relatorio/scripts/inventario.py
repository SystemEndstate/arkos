"""inventario.py - o que existe no estado da suíte, a idade de cada arquivo e a linha da banca.

Desatualizado = mais de 30 dias, ou anterior à última retro (retro/AAAA-MM-DD.md).
Banca: lê 'persona', 'nota' e 'veredito' do frontmatter de banca/*.md, sem recalcular.

Uso:
  python inventario.py workspace/<cliente>/<projeto>/estrategia [--hoje AAAA-MM-DD] [--out relatorio/inventario.json]
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

LIMITE_DIAS = 30
ARQUIVOS = {  # arquivo -> skill que produz (especificação interna)
    "tese.md": "arkos-estrategia", "premissas.yaml": "arkos-estrategia-premissas",
    "ideias.md": "arkos-estrategia-ideia", "modelo.md": "arkos-estrategia-modelo",
    "preco.md": "arkos-estrategia-preco", "gtm.md": "arkos-estrategia-gtm",
    "financas.xlsx": "arkos-estrategia-financas", "financas.md": "arkos-estrategia-financas",
    "financas-resultado.json": "arkos-estrategia-financas", "produto.md": "arkos-estrategia-produto",
    "diagnostico.md": "arkos-estrategia-diagnostico",
}
OBRIGATORIOS = ("tese.md", "premissas.yaml")


def _data_mod(p: Path) -> dt.date:
    return dt.date.fromtimestamp(p.stat().st_mtime)


def frontmatter(texto: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", texto, re.S)
    if not m:
        return {}
    out = {}
    for linha in m.group(1).splitlines():
        k = re.match(r"([A-Za-z_]\w*):\s*(.*?)\s*(#.*)?$", linha)
        if k:
            v = k.group(2).strip().strip('"')
            out[k.group(1)] = float(v) if re.fullmatch(r"-?\d+(\.\d+)?", v) else v
    return out


def inventariar(pasta: str | Path, hoje: dt.date) -> dict:
    base = Path(pasta)
    if not base.is_dir():
        raise ValueError(f"pasta não existe: {base}")
    retros = sorted(p.stem for p in (base / "retro").glob("*.md") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)) \
        if (base / "retro").is_dir() else []
    ultima_retro = dt.date.fromisoformat(retros[-1]) if retros else None
    itens, faltando = [], []
    for nome, skill in ARQUIVOS.items():
        p = base / nome
        if not p.exists():
            faltando.append({"arquivo": nome, "skill": skill})
            continue
        d = _data_mod(p)
        idade = (hoje - d).days
        motivo = None
        if idade > LIMITE_DIAS:
            motivo = f"{idade} dias"
        elif ultima_retro and d < ultima_retro and nome != "premissas.yaml":
            motivo = f"anterior à retro de {ultima_retro.isoformat()}"
        itens.append({"arquivo": nome, "data": d.isoformat(), "idade_dias": idade,
                      "desatualizado": motivo is not None, "motivo": motivo})
    banca = []
    for p in sorted((base / "banca").glob("*.md")) if (base / "banca").is_dir() else []:
        fm = frontmatter(p.read_text(encoding="utf-8"))
        banca.append({"arquivo": f"banca/{p.name}", "persona": fm.get("persona", p.stem),
                      "nota": fm.get("nota"), "veredito": fm.get("veredito"),
                      "completo": all(fm.get(k) not in (None, "") for k in ("persona", "nota", "veredito"))})
    return {"pasta": str(base), "hoje": hoje.isoformat(), "ultima_retro": ultima_retro and ultima_retro.isoformat(),
            "arquivos": itens, "faltando": faltando, "banca": banca,
            "pode_gerar": all((base / n).exists() for n in OBRIGATORIOS),
            "alguma_banca_parar": any(b["veredito"] == "parar" for b in banca)}


def _main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    hoje = dt.date.fromisoformat(argv[argv.index("--hoje") + 1]) if "--hoje" in argv else dt.date.today()
    r = inventariar(argv[0], hoje)
    txt = json.dumps(r, ensure_ascii=False, indent=2)
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(txt, encoding="utf-8")
    print(txt)
    return 0 if r["pode_gerar"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
