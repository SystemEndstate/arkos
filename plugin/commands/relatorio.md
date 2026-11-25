---
description: Gera o relatório da execução ARKOS (site local em workspace/<cliente>/<projeto>/relatorio/) e abre
allowed-tools: Bash(node:*), Read, Write
argument-hint: "[--cliente c --projeto p | --execucao id]"
---

Fatos da execução (crus, coletados de arkos.engine/execucoes/<id>/ e do workspace):

!`node "${CLAUDE_PLUGIN_ROOT}/../relatorio.mjs" coletar $ARGUMENTS`

Faça o relatório agora, nesta ordem e sem perguntar nada que já esteja nos fatos:

1. Se `cliente` ou `projeto` vierem null, descubra pelo pedido ou pelas entradas; se não der, pergunte só isso.
2. Leia o `schema` (SCHEMA.md) indicado acima e, se precisar, os artefatos listados.
3. Escreva o JSON do relatório num arquivo temporário (ex.: `<destino>/../_relatorio.json`) com: título do que foi entregue, `kind`, `lead`, `meta` (cliente, projeto, data, execução), e seções para entradas, plano/rota, decisões e o porquê, passos com status (`steps`), artefatos, números (`kpis`, só com fonte), fontes (`sources`), pendências (owner `voce`, status `waiting`) e próxima ação. Sem inventar número nem fato; estimativa leva "(estimativa)".
4. Gere: `node "${CLAUDE_PLUGIN_ROOT}/../relatorio.mjs" gerar <arquivo.json> --cliente <c> --projeto <p> --execucao <id> --abrir` e apague o JSON temporário.
5. Responda em 2 linhas: o caminho do relatório e o do índice do cliente (`relatorios.html`).
