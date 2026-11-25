---
name: arkos-intake
description: Perguntas de entrada padrão da ARKOS antes de recomendar ou executar qualquer módulo (mercado, cliente ideal, canal, orçamento, prazo, destino). Use no começo de todo pedido de trabalho dentro do `arkos`, quando o arkos-roteador escolher um módulo/playbook, ou quando o usuário disser "começar", "novo projeto", "minerar clientes", "campanha nova", "proposta".
status: rascunho
versao: 0.1.0
modulos: [todos]
depende_de: [arkos-perfil, arkos-mercado, arkos-roteador]
---

# arkos-intake

Regra do usuário (MODULOS.md, 2026-11-21): **todo módulo começa com perguntas de entrada** e só depois recomenda e executa. Esta skill é o único lugar onde essas perguntas moram, para que todo prestador pergunte igual.

## Quando usar

- O `arkos-roteador` devolveu `{modulo, playbook}` e o playbook ainda não tem as entradas preenchidas.
- O pedido do usuário é vago ("quero clientes", "faz um anúncio").

Não use quando o pedido já trouxer todas as entradas: nesse caso, confirme numa linha e siga.

## Passos

1. **Ler o perfil** (`arkos-perfil ler`). O que já está lá **não é perguntado**: vira padrão sugerido.
2. **Buscar o bloco de perguntas** do playbook em `cli/data/playbooks.json` → `entradas[]` (formato abaixo). Sem bloco, use o bloco genérico.
3. **Tirar do pedido** o que o usuário já disse (nicho, cidade, canal). Não perguntar de novo.
4. **Perguntar tudo num bloco só**, na ordem, com o padrão entre parênteses. No máximo 8 perguntas. Usar `AskUserQuestion` quando houver opções fechadas (mercado, canal, motor).
5. **Mercado primeiro.** A resposta chama o `arkos-mercado`, que traz canais permitidos, leis e tom. As perguntas seguintes já se ajustam (ex.: no BR o canal padrão é e-mail + DM; WhatsApp só com opt-in).
5b. **Esteira:** se o playbook for um elo de esteira e houver `saida.json` do elo anterior do mesmo cliente,
    (o terminal já procura esse arquivo e manda o caminho no `additionalContext`, a partir do commit `eeea3dc`; usar esse caminho, sem procurar de novo), pré-preencher as entradas mapeadas em `esteiras[].elos[].recebe` e mostrá-las como "assumido (de <playbook>)". `mercado` e `empresa` passam sempre.
5c. **Cliente e projeto** (regra PASTA-CASA): o `playbooks.json` já traz as duas perguntas logo depois do mercado. Padrão: o último cliente usado e `<tema>-<AAAA-MM>`. Nomes em minúsculas, sem acento, com hífen. Criar `workspace/<cliente>/<projeto>/` se não existir (sem sobrescrever nada).
6. **Gravar** as respostas em `arkos.engine/execucoes/<id>/entradas.json` (o `<id>` é o da execução que o terminal criou e mandou no `additionalContext`, junto com as perguntas de `entradas[]`) e as que forem duráveis (ICP, mercado-alvo) no perfil, com `arkos-perfil atualizar`.
7. Devolver ao playbook: `{entradas, faltando: []}`. Se faltar algo obrigatório, não seguir.

## Bloco genérico (quando o playbook não define)

| # | Pergunta | Padrão | Obrigatória |
|---|---|---|---|
| 1 | Mercado: Brasil, EUA ou Europa? | o do perfil | sim |
| 2 | Para qual empresa ou projeto? | perfil ativo | sim |
| 3 | Cliente ideal: nicho, porte, cidade ou país, ticket | ICP do perfil | sim |
| 4 | Canal | o padrão do mercado | sim nos módulos 5, 8, 13, K |
| 5 | Orçamento de mídia/ferramenta, se o playbook gastar (informativo: a skill estima o custo e o prestador decide) | — | não |
| 6 | Prazo | — | não |
| 7 | O que conta como pronto? | critério do playbook | não |
| 8 | Destino da saída (CSV, CRM, site, relatório) | relatório | não |

## Formato proposto para `playbooks.json` (a combinar com o Violoncelo)

```json
{ "id": "mineracao-clientes",
  "entradas": [
    { "id": "mercado", "pergunta": "Mercado: Brasil, EUA ou Europa?", "opcoes": ["BR","EUA","EU"], "perfil": "mercado", "obrigatoria": true },
    { "id": "nicho", "pergunta": "Nicho", "perfil": "icp.nicho", "obrigatoria": true },
    { "id": "local", "pergunta": "Cidade, estado ou país", "obrigatoria": true },
    { "id": "quantidade", "pergunta": "Quantos leads?", "padrao": 200, "obrigatoria": true }
  ] }
```

Campo `perfil` = caminho no perfil de onde vem o padrão. O terminal pode mostrar "passo 0/M · entradas" enquanto a skill roda.

## Regras duras

- Nunca executar nada pago antes de as entradas obrigatórias estarem preenchidas e de o prestador ver o custo estimado e dizer "sim" (decisão do usuário: sem teto, quem decide o gasto é o prestador).
- Nunca perguntar um dado sensível que não seja necessário (CPF, senha, chave). Chave e token são feitos pelo login do próprio MCP.
- Perguntas em pt-BR. Se o mercado for EUA/EU, os **artefatos** saem em inglês, mas a conversa com o prestador continua em pt-BR.

## Pendências

- Combinar o campo `entradas[]` com o Violoncelo antes de criar a skill.
- Escrever os blocos de cada um dos 17 playbooks atuais.
