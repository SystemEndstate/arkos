---
name: arkos-sop
description: Cria e valida SOPs (procedimento operacional padrão) e o checklist no formato da ARKOS. Seções obrigatórias Objetivo, Dono, Gatilho, Passos numerados, Pronto quando e Exceções; recusa senha no texto e passo vago ("etc.", "conforme necessário"). Use em "documentar o processo", "criar SOP", "virar procedimento", "checklist do papel", "transformar aprendizado em SOP", e nas etapas documentar, sops e base de processo-operacional, onboarding-prestador e retro-cliente.
status: instalada (2026-11-22)
versao: 1.0.0
modulos: [O, L]
depende_de: []
---

# arkos-sop

Um SOP bom deixa qualquer prestador fazer a tarefa igual, sem perguntar. Um SOP vago só parece documentação.

## Passos

1. **Entender** o processo com quem faz hoje: gatilho, passos reais, como sabe que acabou e o que costuma dar errado.
2. **Criar:**
   `python scripts/sop.py novo --casa C --projeto "Onboarding de cliente" --titulo "Subir campanha Meta" --dono ana --gatilho "cliente aprovou os criativos" --passos "a; b; c" --pronto "x; y" --excecoes "se X: Y" --ferramentas "Meta Ads"`
3. **Validar** (também vale para SOP antigo): `validar --arquivo sop.md`. Devolve a lista do que falta.
4. **Checklist:** `checklist --arquivo sop.md` gera `checklist-<slug>.md` ao lado.
5. **Base:** o SOP aprovado entra na `arkos-base` para os prestadores consultarem. Isso é só leitura para eles.

## Onde fica

- de operação: `<casa>/workspace/_operacao/<projeto>/sop-<slug>.md`;
- de um cliente: `<casa>/workspace/<cliente>/<projeto>/sop-<slug>.md`.

## Regras duras

1. **Seis seções obrigatórias:** Objetivo, Dono, Gatilho, Passos, Pronto quando, Exceções.
2. **Pelo menos 2 passos numerados**, cada um com uma ação e até 220 caracteres.
3. **Sem passo vago:** "etc.", "conforme necessário", "quando der" e "se possível" reprovam.
4. **Sem senha nem token:** escreva "pegar no cofre do cliente". O script recusa (código 2).
5. **SOP de etapa com escrita ou envio** aponta a guarda (`arkos-guarda-escrita` ou `arkos-guarda-envio`) no passo.

## Pronto quando

- `validar` volta `ok: true`;
- o checklist foi gerado;
- tem dono nomeado.

## Exceções

- **entrada_incompleta:** faltou dono, gatilho, passos ou critério de pronto. Devolve código 3 e diz o que falta.
- **retrabalho:** o processo mudou. Crie a versão nova com o mesmo título; a anterior fica no git do workspace.

## Testes

`python -m unittest discover -s scripts/tests`: 3 testes cobrindo SOP completo com checklist, senha no passo, passo vago, campos faltando e SOP antigo sem seções.
