---
name: arkos-xlsx
description: Gera, edita e confere planilhas Excel (.xlsx) na pasta do cliente com openpyxl — custos, orçamento, leads, cronograma, com cabeçalho fixo, filtro, formatos de moeda/percentual/data, total por fórmula — e confere fórmulas quebradas, referências fora dos dados e valores de erro. Use em "planilha", "Excel", "xlsx", "orçamento em planilha", "atualizar a célula", "conferir as fórmulas", "spreadsheet".
status: rascunho
versao: 0.1.0
modulos: [D, O, F]
depende_de: []
substitui: anthropic-skills:xlsx (clone de sala limpa; texto e código escritos do zero)
---

# arkos-xlsx

Planilha por spec e script (`scripts/xlsx_arkos.py`). O cálculo fica **na planilha** (fórmulas), não num número digitado: quem abrir vê de onde veio.

## Pasta-casa

`workspace/<cliente>/<projeto>/planilhas/<slug>-<AAAA-MM-DD>.xlsx`, nunca sobrescreve (`-v2`). Edição sai `-editado`.

## Comandos

```bash
py -3 scripts/xlsx_arkos.py gerar planilha.json --casa C --cliente X --projeto Y
py -3 scripts/xlsx_arkos.py editar entrada.xlsx --celulas mudancas.json --casa C --cliente X --projeto Y
py -3 scripts/xlsx_arkos.py conferir arquivo.xlsx     # código 1 se achar problema
py -3 scripts/xlsx_arkos.py ler arquivo.xlsx
```

Coluna com `formato`: `moeda` (R$), `int`, `pct`, `data`, `texto`. `total.somar` lista as colunas que ganham `SUM`. Exemplo em `_comum/exemplo-planilha.json`.

## Passos

1. Montar as abas. Toda conta vira fórmula (`=B2*C2`); total por `SUM`.
2. `gerar`. O script já roda o `conferir`; com problema, a saída vem `reprovado` com a lista.
3. Planilha do cliente: `ler`, depois `editar --celulas` (a célula mantém fonte, borda e formato).
4. Número que ninguém mediu vai numa nota da aba (`notas`), não fingindo ser dado.

## Identidade

Cabeçalho em Ink com texto branco mono, aba marcada em Ink, linhas finas, total em negrito com filete. Sem Volt (planilha é papel claro).

## Regras duras

- Pasta-casa, data no nome e sem sobrescrever.
- Cabeçalho congelado (A2) e filtro ligado.
- Autor `ARKOS Engine` e título preenchidos.
- `conferir` sem problema antes de entregar: zero `#REF!`/`#DIV/0!`/`#VALUE!`, parênteses fechados, nenhuma aba inexistente, nenhuma referência fora dos dados, nenhuma circular direta.
- O total nunca é digitado: é fórmula.

## Pronto quando

`conferir` sai com código 0 e o arquivo passa nas regras (T3 de `_testes/aceitacao_clones.py`). O valor das fórmulas aparece quando a planilha é aberta: o openpyxl grava a fórmula, não o resultado.

## Exceções

- `entrada_incompleta`: sem `titulo`/`abas`, aba sem `nome`/`colunas`, total pedindo coluna que não existe ou célula em aba inexistente: código 2, a lista do que falta e nenhum arquivo.
- `resultado_ruim`: `conferir` reprovou. Corrigir a fórmula apontada e gerar de novo.

## Pendências

- Gráfico nativo e formatação condicional.
- Recalcular e gravar os valores sem Excel (LibreOffice headless, quando houver).
