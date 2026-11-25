---
name: arkos-painel
description: Painel de operação da ARKOS a partir das execuções da casa. Mostra a carteira por cliente, prazos e SLA com alerta em 80% e no estouro, a fila de entregas esperando o dono, indicadores (no prazo, devolução, gate verde de primeira, custo real × estimado) e a auditoria de escritas e envios sem aprovação ou com hash diferente. Use em "como está a carteira", "o que está atrasado", "o que espera o dono", "indicadores do mês", "auditar o prestador", "painel de execuções", e nas etapas carteira, agenda, calcular, alertar, fila, coletar, conferir e relatorio dos playbooks multi-cliente, prazos-sla, revisao-dono, auditoria-prestador e painel-execucoes.
status: instalada (2026-11-22)
versao: 1.0.0
modulos: [O, L]
depende_de: [arkos-playbook, arkos-revisao]
---

# arkos-painel

Só lê. Junta o que está em `<casa>/arkos.engine/execucoes/<id>/` (`aviso.json`, `entradas.json`, `estado.json`, `saida.json`, `revisao.json`, `aprovacoes/*.json`, `escritas.jsonl`) e devolve visões prontas para decidir.

## Comandos

Script: `scripts/painel.py` (stdlib). A casa vem de `--casa`, `ARKOS_CASA` ou `~/.arkos/config.json`.

| Pedido | Comando |
|---|---|
| Carteira (todos ou um cliente) | `python painel.py carteira [--do-cliente X]` |
| Prazos e alertas | `python painel.py prazos --sla-horas 40 [--sla-json sla.json]` |
| Fila do dono | `python painel.py fila-revisao` |
| Indicadores | `python painel.py indicadores` |
| Auditoria | `python painel.py auditoria [--prestador P]` |

Com `--saida <pasta>` grava `painel.json` e `painel.md`. Use `workspace/_operacao/painel-<aaaa-mm>/`, ou `workspace/<cliente>/_cliente/` para um cliente só.

## Regras duras

1. **Isolamento:** a visão de um cliente nunca mostra execução de outro (`--do-cliente`). Num relatório para o cliente, use sempre o filtro.
2. **O tempo parado no portão do cliente não conta como atraso do prestador**: o campo `portao_cliente_h` das etapas é descontado.
3. **Alertas:** 80% do SLA avisa o prestador; 100% avisa o dono. O painel só aponta. Se o aviso for uma mensagem, passa pela `arkos-guarda-envio`.
4. **Auditoria verde** só com zero anomalias. Uma escrita sem aprovação, com hash diferente do aprovado ou com aprovação vencida é anomalia e vai para o dono.
5. **Entrega não fica dentro de `arkos.engine/`**: o script recusa (código 2).

## Pronto quando

- a carteira bate com as pastas de execução, sem cliente misturado;
- cada execução aberta tem prazo calculado e nível (ok, aviso ou estourado);
- a auditoria listou cada escrita conferida;
- o arquivo do painel está em `workspace/`.

## Exceções

- **entrada_incompleta:** a casa não tem execuções. O script devolve código 3 e diz onde procurou. Pergunte se a casa está certa.
- **JSON corrompido** numa execução: ela entra com o status calculado pelo que sobrou e não derruba o painel.

## Testes

`python -m unittest discover -s scripts/tests`: 7 testes cobrindo carteira isolada, portão do cliente, fila, indicadores, auditoria, recusa de saída no engine, casa vazia e JSON quebrado.
