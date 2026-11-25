---
name: arkos-playbook
description: Executa os playbooks de ponta a ponta da ARKOS (etapas com módulo, skill, entradas, saída, portão e dependências) sobre o superpowers:subagent-driven-development, atualizando o passo N/M do terminal e o relatório local. Use quando o arkos-roteador escolher um playbook, quando o usuário pedir um fluxo inteiro ("lançar SaaS", "validar nicho", "minerar clientes", "proposta OaaS"), ou para retomar um playbook parado.
status: rascunho
versao: 0.1.0
modulos: [B, todos]
depende_de: [arkos-roteador, arkos-intake, arkos-perfil, arkos-gate, superpowers:subagent-driven-development]
---

# arkos-playbook

É o "O" de Orchestration. O motor (superpowers) já existe; esta skill dá o **conteúdo** declarativo e a disciplina de portão entre etapas.

## Formato de um playbook

Fica em `cli/data/playbooks.json` (campo novo `etapas[]`) ou, para playbooks longos, em `engine/playbooks/<id>.yaml`:

```yaml
id: mineracao-clientes
nome: Mineração de clientes
modulos: [growth]
etapas:
  - id: entradas
    skill: arkos-intake
    saida: arkos.engine/execucoes/{id}/entradas.json
  - id: coleta
    skill: arkos-scraper-nicho
    entradas: [entradas.nicho, entradas.local, entradas.orcamento_usd]
    saida: arkos.engine/execucoes/{id}/bruto/
    portao: { tipo: confirmacao_custo }
    depende_de: [entradas]
  - id: merge
    skill: arkos-lead-merge
    saida: leads_{nicho}_{local}_{data}.csv
    portao: { tipo: jev_checklist, checklist: lead-merge }
    depende_de: [coleta]
  - id: relatorio
    skill: arkos-gate
    depende_de: [merge]
```

Tipos de `portao`: `confirmacao_custo`, `aprovacao_humana`, `jev_checklist`, `arkos_gate`, `guarda_envio`, `guarda_escrita`.

## Passos de execução

1. Receber `{playbook, entradas}` do roteador e do intake. Usar a pasta da execução que o terminal já criou (`arkos.engine/execucoes/<AAAAMMDD-HHMMSS-playbook-xxxx>/`, com o `aviso.json`) e criar nela o `estado.json`. Só criar um id novo se for rodar fora do terminal.
   **Regra PASTA-CASA:** a pasta da execução (`arkos.engine/execucoes/<id>/`) guarda só estado (entradas, rota, estado, aprovações, saida.json, bruto intermediário). **Todo artefato e toda entrega** vão para a `pasta` do playbook no `playbooks.json` (padrão `workspace/<cliente>/<projeto>/`, com cliente e projeto do `entradas.json`). O `saida.json` grava `cliente`, `projeto`, `pasta`, cada artefato com caminho relativo à casa, `decisoes` (`[{decisao, porque}]`, as tomadas nos portões e nas escolhas da execução), `pendencias` (o que ficou em aberto) e `proxima_acao` (uma frase). O `/relatorio` do terminal monta o relatório a partir dele.
2. Ordenar as etapas pelo `depende_de`. Etapas sem dependência entre si podem rodar em paralelo, **mas só com subagentes autorizados** (regra do usuário: avisar antes de disparar).
3. Para cada etapa:
   1. carregar a skill da etapa;
   2. passar as entradas (do intake, do perfil ou da saída de etapas anteriores);
   3. gravar a saída no caminho declarado;
   4. rodar o portão. **Portão reprovado = parar**, mostrar o motivo e propor correção. Nunca pular;
   5. atualizar o `estado.json` para o rodapé do terminal, no formato que ele lê (commit e74406f):
      ```json
      { "playbook": "mineracao-clientes", "total": 10,
        "etapas": [ { "id": "entradas", "nome": "Perguntas de entrada", "status": "feito" },
                    { "id": "custo", "nome": "Informar custo e perguntar", "status": "portao" },
                    { "id": "coleta", "nome": "Coleta", "status": "pendente" } ] }
      ```
      Status que o terminal reconhece: `feito` (também conta qualquer um que comece com conclu/ok/done); `em_andamento`, `aguardando` ou `portao` marcam a etapa atual. Os demais contam como pendente. O `total` é opcional; sem ele, o terminal conta as etapas. Etapa opcional pulada é gravada como `feito`, com `"pulada": true`, para o N/M não travar.
4. No fim:
   - chamar o `arkos-gate` para o relatório único e gravar no perfil o que for durável;
   - gravar o **`saida.json`** (contrato em `engine/fluxos/playbooks.json` → `contrato_saida`): `{playbook, execucao, status, artefatos[], campos{}, proximos[]}`. O campo `proximos` vem do próximo elo das `esteiras` em que o playbook aparece;
   - acrescentar uma linha em `arkos.engine/aprendizado.jsonl` com os campos do `retro[]` do playbook.
4b. **Exceções:** tratar como em `excecoes_padrao`, ou como em `excecoes` do playbook quando ele tiver as próprias. Status extras que vão para o `estado.json`: `bloqueada` (ferramenta fora do ar), `aguardando` (entrada ou custo) e `cancelado:<motivo>`. Toda etapa com `acao` de escrita ou envio traz um `rollback`; em cancelamento, perguntar se o rollback deve ser aplicado.
5. Retomar: `arkos-playbook retomar <id>` lê o `estado.json` e continua da primeira etapa não concluída.

## Primeiros playbooks

| id | Etapas (módulos) |
|---|---|
| lancar-saas | 9 → 10 (arkos-oferta) → 2 → 8 → 4 → 6 → 11 |
| validar-nicho-48h | 9 → 10 → reviews de premissa (stress-test) |
| mineracao-clientes | intake → arkos-scraper-nicho → arkos-lead-merge → (opcional) arkos-conversa |
| proposta-oaas | intake → arkos-oaas-proposta → arkos-oaas-calculadora → aprovação do dono |
| entrega-oaas | entrega do módulo → arkos-oaas-ledger → arkos-gate |
| lancar-infoproduto | 9 → 10 → 8 → 7 → 6 |
| diligencia | 14 inteiro |
| operacao-suporte | 12 |

## Regras duras

- Etapa que envia ou escreve tem o portão `guarda_envio` ou `guarda_escrita`. Sem isso o playbook não carrega (validação ao abrir).
- O playbook nunca guarda segredo nem dado pessoal em `estado.json`.
- Sem `arkos-intake` como primeira etapa, o playbook é inválido (regra do passo a passo padrão).

## Pendências

- Combinar com o Violoncelo se `etapas[]` vai no JSON ou num YAML separado.
- Validador de playbook (script) com teste, seguindo guarda-regressao.
