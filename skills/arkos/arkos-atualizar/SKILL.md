---
name: arkos-atualizar
description: Homologa e publica uma versão nova da própria ARKOS (o terminal e as skills, não o site ou o app do cliente, cujo deploy e rollback são do deploy-infra) para os prestadores (o que arkos update baixa), com rollback para a anterior. Exige versão maior que a atual, notas e novidades, sha256 dos arquivos, testes 100% verdes numa máquina de teste limpa, aceitação verde, aprovação do dono pela arkos-revisao e confirmação explícita. Use em "publicar versão nova da ARKOS", "lançar atualização", "homologar a release", "arkos update", "voltar a versão anterior", "rollback da ARKOS", e nas etapas homologar, aprovar e publicar do playbook atualizar-arkos.
status: instalada (2026-11-22)
versao: 1.0.0
modulos: [O, I]
depende_de: [arkos-revisao, arkos-gate]
---

# arkos-atualizar

Uma versão ruim chega a todos os prestadores de uma vez. Por isso publicar é uma escrita com trava e tem rollback de um comando.

## Passos

1. **Montar `release.json`:** `versao` (X.Y.Z), `notas`, `novidades[]` e `arquivos` (nome → sha256).
2. **Homologar numa máquina de teste limpa**, nunca na de desenvolvimento. Instale do zero, rode os testes do terminal e os de aceitação das skills, e salve `resultado-testes.json`.
   `python scripts/atualizar.py homologar --release release.json --testes resultado-testes.json --atual 0.5.0`
3. **Aprovação do dono:** `arkos-revisao decidir --decisao aprovar` gera o `revisao.json`.
4. **Prévia:** `publicar --release release.json --canal canal.json --aprovacao revisao.json --testes resultado-testes.json` mostra de/para e o rollback, e não publica.
5. **Publicar:** o mesmo comando com `--confirmo`. O ponteiro `atual` do canal muda e a anterior vai para `anteriores`.
6. **Acompanhar** as primeiras horas pela `arkos-suporte`. Se quebrar: `rollback --canal canal.json --motivo "..." --confirmo`.

## Regras duras

1. **Testes 100% verdes.** Nada de "1 falhou mas é bobo": o script recusa.
2. **Máquina de teste limpa:** `dev` ou `minha` reprovam.
3. **Versão estritamente maior** que a atual.
4. **Só com a aprovação do dono** (decisão `aprovar`, papel `dono`) e com `--confirmo` depois da prévia.
5. **Nada é apagado:** o histórico guarda quem aprovou e o hash da release, e as 10 últimas versões ficam para rollback.
6. **Novidades obrigatórias:** o prestador precisa saber o que mudou.

## Pronto quando

- a homologação está verde;
- `canal.json` aponta para a versão nova, com a anterior em `anteriores`;
- o histórico registra a aprovação.

## Exceções

- **rollback:** volta para a anterior com o motivo. Sem anterior, devolve código 3.
- **resultado_ruim:** a homologação deu vermelho. Devolva para quem fez a mudança com a lista de `problemas`.
- **entrada_incompleta:** rollback sem motivo. Devolve código 3 e pergunta.

## Testes

`python -m unittest discover -s scripts/tests`: 3 testes cobrindo a publicação completa, teste falho, sem dono, aprovado por prestador, sem confirmar, máquina de dev, versão igual, rollback em sequência e rollback sem anterior.
