---
name: arkos-pptx
description: Gera e edita apresentações PowerPoint (.pptx, 16:9) na pasta do cliente com python-pptx, na identidade ARKOS e com o Rotor desenhado pelas pás oficiais — capa, seção, lista, números, tabela e fechamento — e faz uma prévia PNG sem precisar do PowerPoint. Use em "apresentação", "slides", "deck", "PowerPoint", "pptx", "montar os slides da reunião", "trocar o valor no deck".
status: rascunho
versao: 0.1.0
modulos: [D, O, V]
depende_de: []
substitui: anthropic-skills:pptx (clone de sala limpa; texto e código escritos do zero)
---

# arkos-pptx

Deck por spec (`scripts/pptx_arkos.py`). O Claude escreve o roteiro dos slides; o script faz o layout.

## Pasta-casa

`workspace/<cliente>/<projeto>/apresentacoes/<slug>-<AAAA-MM-DD>.pptx`, nunca sobrescreve (`-v2`). A prévia fica ao lado: `<arquivo>-previa.png`.

## Comandos

```bash
py -3 scripts/pptx_arkos.py gerar deck.json [--trocar chaves.json] --casa C --cliente X --projeto Y
py -3 scripts/pptx_arkos.py previa arquivo.pptx    # folha PNG de todos os slides (PIL, fontes OFL em fonts/)
py -3 scripts/pptx_arkos.py editar entrada.pptx --trocar chaves.json --casa C --cliente X --projeto Y
py -3 scripts/pptx_arkos.py ler arquivo.pptx
```

Tipos de slide: `capa`, `secao`, `titulo+texto`, `titulo+lista`, `titulo+numeros` (até 4), `titulo+tabela`, `fim`; qualquer um aceita `nota` (notas do apresentador). Exemplo em `_comum/exemplo-deck.json`.

## Passos

1. Roteiro: uma ideia por slide, no máximo 6 itens numa lista e 4 números por slide.
2. `gerar`, depois `previa` e **olhar a prévia** antes de entregar: o texto cabe? o Rotor está inteiro?
3. Mudança num deck que já existe: `ler`, depois `editar --trocar`.
4. Passar pelo `arkos-gate` (copy).

## Identidade

- **Tema escuro (padrão):** fundo Ink, texto claro, Volt como acento (número da seção, números grandes e a pá de cima do Rotor).
- **Tema claro:** fundo papel, marca toda em Ink, sem Volt.
- O **Rotor** é desenhado com as 4 pás chanfradas oficiais (a mesma geometria do relatório e do site), como forma livre. Nunca é aproximado com retângulos nem usado como imagem borrada.
- Cabeçalho `ARKOS ENGINE · <CLIENTE>` e contador `NN / TT` à direita.

## Regras duras

- 16:9, na pasta-casa, com data no nome e sem sobrescrever.
- Capa com as 4 pás do Rotor; Volt só no tema escuro.
- Metadados: título e autor `ARKOS Engine`.
- Deck com `{{chave}}` sobrando não é entregue.
- Não inventar números: o slide de números só leva o que estiver no spec.

## Pronto quando

`gerar` devolve `status: ok`, a prévia foi conferida e o arquivo passa nas regras (T3 de `_testes/aceitacao_clones.py`).

## Exceções

- `entrada_incompleta`: sem `titulo`/`slides`, ou `editar` sem arquivo ou sem `--trocar`, sai com código 2 e a lista do que falta, sem escrever.
- `resultado_ruim`: a prévia mostra texto estourando a caixa. Encurtar o texto (não diminuir a fonte) e gerar de novo.

## Pendências

- Slide com imagem do cliente (foto e produto) e gráfico nativo.
- A prévia mostra posição, cor e texto; a renderização final da fonte depende de quem abrir.
