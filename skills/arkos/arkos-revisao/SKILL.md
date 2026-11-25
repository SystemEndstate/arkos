---
name: arkos-revisao
description: Revisão de entrega na ARKOS. O dono (ou o cliente, ou um revisor) aprova, aprova com ressalva ou devolve com motivo e com a etapa para onde volta; grava arkos.engine/execucoes/<id>/revisao.json com o histórico de rodadas. Só revisa com gate verde, quem executou não se aprova e devolver reabre só da etapa pedida em diante. Use em "revisar a entrega", "aprovar", "devolver para ajuste", "aprovar com ressalva", "o cliente aprovou o texto", "dono aprova a versão", e nas etapas revisar, decidir, teste e aprovacao de revisao-dono, onboarding-prestador, atualizar-arkos e caso-de-sucesso.
status: instalada (2026-11-22)
versao: 1.0.0
modulos: [O]
depende_de: [arkos-gate, arkos-painel]
---

# arkos-revisao

O portão humano depois do gate automático. O gate diz se está tecnicamente pronto; a revisão diz se está bom para o cliente.

## Passos

1. **Pegar a fila:** `arkos-painel fila-revisao` lista as execuções com gate verde e sem revisão.
2. **Revisar:** abra o relatório (`/relatorio`), os artefatos de `saida.json` e as evidências. Leia contra o critério de pronto do playbook.
3. **Decidir:**
   - aprovar: `python scripts/revisao.py decidir --casa C --execucao ID --quem dono --papel dono --decisao aprovar`
   - aprovar com ressalva: `--decisao ressalva --ressalvas "trocar foto; CTA maior"`. A entrega segue e as ressalvas viram pendência.
   - devolver: `--decisao devolver --motivo "sem prova social" --voltar-para design`
4. **Registrar o aprendizado:** o motivo de toda devolução vai para o `aprendizado.jsonl` (a `arkos-playbook` lê dali).

## Regras duras

1. **Só com gate verde.** Gate amarelo ou vermelho volta para o prestador antes; o script recusa (código 2).
2. **Quem executou não revisa a própria entrega**, nem com o papel de revisor.
3. **O papel prestador não aprova.** Revisam dono, revisor ou cliente.
4. **Devolver exige motivo e a etapa de volta**, que precisa existir no playbook. Só reabre dali em diante; o que veio antes fica como está.
5. **Nada é apagado:** cada decisão vira uma rodada nova em `revisao.json`.

## Pronto quando

- `revisao.json` existe com a decisão, quem, quando e o motivo ou as ressalvas;
- na devolução, `estado.json` mostra as etapas reabertas como `pendente`.

## Exceções

- **retrabalho:** devolver reabre da etapa pedida (ex.: `design` e `gate`) e o rodapé do terminal volta para ela.
- **entrada_incompleta:** devolver sem motivo, com etapa inexistente, ressalva sem lista ou execução que não existe. Devolve código 3 com a pergunta.

## Testes

`python -m unittest discover -s scripts/tests`: 4 testes cobrindo aprovar com histórico, ressalva, autoaprovação, papel prestador, gate amarelo, retrabalho parcial e execução inexistente.
