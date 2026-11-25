---
name: arkos-pesquisa
description: Pesquisa aprofundada e verificável sobre um tema (mercado, concorrente, regra, fornecedor) com disciplina de fonte — pergunta clara, busca ampla, triangulação (≥2 fontes independentes por afirmação crítica), registro de fontes e nível de confiança. Use em "pesquisa profunda", "investigar o mercado", "levantar sobre X", "o que se sabe sobre", "pesquisar antes de decidir".
status: rascunho
versao: 0.1.0
modulos: [base]
depende_de: [arkos-decisor]
---

# arkos-pesquisa

Clone de sala limpa da pesquisa profunda: o Claude faz a busca (web/ferramentas); esta skill impõe a **disciplina de fonte** e um registro de citações, para a resposta ser verificável e não um chute. Não gera o texto da pesquisa (isso é do Claude) — organiza perguntas, fontes, lacunas e confiança. Método público.

## Quando usar e quando não usar

- **Usar:** tema que vira decisão (mercado, concorrente, regra, fornecedor) e precisa de prova.
- **Não usar:** fato simples e único; pergunta que o perfil já responde.

## Entradas

- A pergunta e as sub-perguntas.
- As fontes achadas (url, afirmação, data), via `pesquisa.py fonte add`.

## Passos

1. **Decompor** a pergunta em sub-perguntas verificáveis.
2. **Buscar amplo** (o Claude usa as ferramentas de web) e registrar cada fonte no ledger (`pesquisa.py`).
3. **Deduplicar por domínio** e marcar afirmação crítica com **< 2 fontes independentes** como `frágil`.
4. **Triangular:** afirmações que se contradizem viram `conflito` e sobem para o Claude decidir (ou o `arkos-decisor` quando for fechado).
5. **Graduar confiança** por afirmação (alta/média/baixa) conforme número e independência das fontes.
6. **Relatório:** perguntas, respostas com citação, lacunas e nível de confiança.

## Saída

JSON do ledger: `{perguntas, fontes:[{url,dominio,afirmacao,data}], afirmacoes:[{texto,confianca,fontes}], fragies:[...], conflitos:[...], lacunas:[...]}`. O texto final é do Claude, citando o ledger.

## Critério de pronto

- [ ] Toda afirmação crítica tem ≥ 2 fontes independentes ou está marcada `frágil`/`lacuna`.
- [ ] Conflitos entre fontes foram resolvidos ou declarados.
- [ ] Cada afirmação tem nível de confiança.

## Exceções

- **Fonte única:** manter, marcada `frágil`; não apresentar como fato.
- **Nada encontrado:** declarar a lacuna, não inventar.
- **Fontes em conflito:** declarar o conflito e a fonte mais forte, com o porquê.

## Alimenta

- `arkos-estrategia-*` (premissas com evidência) e qualquer decisão que precise de base.

## Regras duras

- Nunca apresentar afirmação de fonte única como fato.
- Não inventar número nem fonte; lacuna é declarada.
- Sem dado pessoal nem segredo no ledger.
