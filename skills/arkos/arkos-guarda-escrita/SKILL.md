---
name: arkos-guarda-escrita
description: Trava obrigatória antes de qualquer mutação em conta de anúncio, pagamento, CRM ou loja (criar, editar, pausar, mudar budget, cobrar, reembolsar) na ARKOS. Exige prévia com diff, teto de variação de budget por execução, confirmação humana e log de quem mudou o quê. Use sempre que Meta Ads, TikTok, Google Ads, Stripe, Asaas, Shopify, HubSpot, Pipedrive ou n8n forem escrever algo.
status: rascunho
versao: 0.1.0
modulos: [D, 6, 10, 13, K, M, L]
depende_de: [arkos-perfil]
---

# arkos-guarda-escrita

Os MCPs oficiais da Meta e do TikTok escrevem direto: budget, pausa, criação. Um token de ads ou de pagamento na máquina do prestador é acesso a dinheiro. Esta trava fica entre a decisão e a mutação.

## Duas camadas

1. **Hook `PreToolUse`** em `~/.arkos/hooks/guarda_escrita.py`: casa ferramentas de escrita listadas em `~/.arkos/travas.json` (ex.: `mcp__meta-ads__*create*|*update*|*pause*`, `mcp__tiktok__*`, `mcp__stripe__*create*|*refund*`, `mcp__easypanel__execute_mutation|execute_destructive`, `mcp__n8n__*activate*`). Sem `aprovacao_id` válido para aquele alvo, bloqueia.
2. **Esta skill** lê o estado atual, monta o diff e grava a aprovação.

## Passos

1. **Ler o estado atual** do alvo pelo próprio MCP (só leitura).
2. **Montar o diff** por item: `campo: antes → depois` (ex.: `budget diário: R$ 200 → R$ 260 (+30%)`).
3. **Aplicar os limites configuráveis** do perfil (`config.travas` no `arkos-perfil`). **Todos os valores são padrão provisório, A CONFIRMAR com o dono:**
   - `budget_variacao_max_conjunto` (padrão a confirmar: 20%) e `budget_variacao_max_conta` (a confirmar: 30%) por execução. Acima disso, segunda confirmação, sem bloqueio;
   - `pagamento_segunda_confirmacao_acima` (a confirmar: R$ 500 / US$ 100);
   - ação destrutiva (apagar campanha, cancelar assinatura) sempre pede confirmação com o nome do alvo digitado. Esta regra é fixa.
4. **Mostrar a prévia** e perguntar. Só "sim" explícito vale.
5. **Gravar** `arkos.engine/execucoes/<id>/aprovacoes/<portao>.json` = `{quem, quando, alvo, diff, expira_em}` (validade em `config.travas.aprovacao_escrita_validade`, padrão a confirmar: 30 min) e enviar o log ao `arkos-base` (quem mudou o quê, em qual conta).
6. Depois da mutação, **reler** o alvo e confirmar que o estado bate com o diff. Se não bater, avisar.

## Regras duras

- Meta Ads na fase 1 só com `ads_read`; esta trava precisa existir e ter teste antes de ligar `ads_management`.
- Nunca chave mestra: OAuth por usuário ou chave restrita (Stripe "Agent", subconta Asaas).
- Nunca CPF ou dado de cartão em log.
- Escala de anúncio decidida pelo `arkos-escala` (P2) continua passando por aqui.

## Pendências

- Confirmar com o dono os valores padrão de `config.travas` (todos marcados "a confirmar").
- Nomes reais das ferramentas de escrita de cada MCP depois de instalados.
- Teste do hook com MCP falso.
