---
name: arkos-passagem
description: Dossiê de passagem de um cliente de um prestador para outro na ARKOS. Junta perfil, metas, execuções abertas com o portão que está esperando, decisões com o porquê, pendências, acessos a transferir, o que NÃO fazer com o cliente e as entregas anteriores, sem nenhum segredo. Grava workspace/<cliente>/_cliente/passagem-<data>.md e registra a leitura confirmada por quem assume. Use em "passar o cliente", "trocar de prestador", "dossiê de passagem", "o novo prestador precisa saber", "handover", e nas etapas dossie, reuniao e passagem de passagem-prestador e desligar-prestador.
status: instalada (2026-11-22)
versao: 1.0.0
modulos: [O, L]
depende_de: [arkos-acessos, arkos-painel, arkos-perfil]
---

# arkos-passagem

Passagem ruim perde contexto, repete erro com o cliente e deixa portão parado. O dossiê é a memória que muda de mãos.

## Passos

1. **Gerar:** `python scripts/passagem.py dossie --casa C --cliente X --de ana --para bruno --nao-fazer "não ligar antes das 10h; não prometer prazo de agenda"`
2. **Quem sai completa** a seção 7 ("O que NÃO fazer") se veio vazia. O script avisa com `nao_fazer_vazio: true`.
3. **Reunião conjunta** de 30 min, ou leitura confirmada. Quem assume roda `confirmar --arquivo passagem-<data>.md --quem bruno`.
4. **Acessos:** rode o `arkos-acessos transferir` com a lista da seção 6.
5. **Portões esperando** (`portoes_esperando`): avise o cliente de quem é o novo contato. A mensagem passa pela `arkos-guarda-envio`.

## As 8 seções

1. Quem é o cliente (perfil)
2. Metas e SLA (`metas.yaml`)
3. Execuções abertas, com o portão esperando e a próxima ação
4. Decisões já tomadas e por quê (`saida.json` → `decisoes`)
5. Pendências
6. Acessos a transferir
7. O que NÃO fazer
8. Entregas anteriores (artefatos)

## Regras duras

1. **Nenhum segredo no dossiê:** linha com cara de senha ou token vira `[segredo omitido]`.
2. **Um cliente por dossiê:** execução de outro cliente nunca entra.
3. **Passagem para a mesma pessoa é recusada.**
4. O dossiê fica em `workspace/<cliente>/_cliente/`, junto com o resto do cliente.

## Pronto quando

- as 8 seções estão preenchidas (a 7 pelo prestador que sai);
- a leitura está confirmada por quem assume;
- os acessos estão transferidos (o plano da `arkos-acessos` está todo feito).

## Exceções

- **entrada_incompleta:** o cliente não existe nesta casa. Devolve código 3.
- **retomar:** se o prestador saiu sem passagem, o dono roda o dossiê com `--de <quem saiu>`; o conteúdo vem das execuções.

## Testes

`python -m unittest discover -s scripts/tests`: 3 testes cobrindo as 8 seções, decisões e pendências, isolamento entre clientes, token mascarado, a mesma pessoa, confirmação e cliente inexistente.
