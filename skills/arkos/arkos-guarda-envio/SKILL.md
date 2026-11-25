---
name: arkos-guarda-envio
description: Trava obrigatória antes de qualquer disparo de mensagem (WhatsApp, Instagram DM, e-mail, LinkedIn, SMS) na ARKOS. Confere opt-in e opt-out, origem e base legal do lead, janela de 24 h, template aprovado, CAN-SPAM, GDPR, LGPD, limites diários e horário, e exige prévia + aprovação explícita. Use sempre que uma skill ou MCP for enviar, agendar ou subir uma mensagem para alguém, inclusive sellbird, Instantly, Smartlead, lemlist, Wame e instaflow.
status: rascunho
versao: 0.1.0
modulos: [5, 8, 13, J, K, P]
depende_de: [arkos-mercado, jev]
---

# arkos-guarda-envio

**Regra fixa:** a ARKOS nunca envia mensagem a ninguém sem passar por esta trava **e** sem o "sim" explícito de uma pessoa. Protege número, domínio e conta de banimento (o erro 141006 já apareceu no meuanuncio) e protege a empresa de multa.

## Duas camadas

1. **Hook `PreToolUse`** (determinístico, sem LLM) em `~/.arkos/hooks/guarda_envio.py`. Ele casa as ferramentas de envio (lista em `~/.arkos/travas.json`: `mcp__instantly__*send*`, `mcp__smartlead__*`, `mcp__lemlist__*launch*`, `mcp__instaflow__crt-pst`, `mcp__claude_ai_Wame__*send*`, `sellbird send`…). Sem um `aprovacao_id` válido e recente no `.arkos/aprovacoes/`, ele **bloqueia** e manda chamar esta skill.
2. **Esta skill** monta a prévia, roda os checks e grava a aprovação.

## Checks por lote (cada lead e cada mensagem)

| Check | Regra | Fonte |
|---|---|---|
| origem | O lead tem `fonte`, `coletado_em` e `base_legal` | LGPD art. 37 |
| supressão | Não está na lista de opt-out (`arkos.engine/supressao.csv` + nuvem) | LGPD art. 18 / CAN-SPAM |
| canal permitido | O canal está em `canais_permitidos` do lead | pesquisa 11 |
| WhatsApp | Exige `whatsapp_template_optin` com data e texto aceito; fora da janela de 24 h só template aprovado; mensagem tem saída ("PARAR/SAIR") | política do WhatsApp |
| Instagram | Só responde quem iniciou nas últimas 24 h; a IA não usa `HUMAN_AGENT` | Instagram Platform |
| LinkedIn | **Bloqueio total de envio automático**: só gera rascunho | User Agreement §8.2 |
| e-mail EUA | Endereço postal, link de opt-out funcionando, remetente identificado, assunto que não engana | CAN-SPAM |
| e-mail EU | Base legal por país registrada; idioma local | GDPR + ePrivacy |
| SMS e ligação automática EUA | **Bloqueio total** | TCPA |
| volume | Abaixo do limite diário da caixa ou do número (config do mercado) | entregabilidade |
| horário | Dentro da janela comercial do fuso do lead | arkos-mercado |
| conteúdo | Jev `decide_many`: "promete resultado garantido?", "parece spam?", "inventa dado?" | — |

O Jev classifica o conteúdo; a decisão de bloquear é determinística: qualquer check obrigatório reprovado = lead fora do lote.

## Passos

1. Receber `{canal, mercado, mensagens[], leads[]}`.
2. Rodar os checks. Separar em **liberados**, **bloqueados (com motivo)** e **para revisão**.
3. Mostrar a prévia: 3 mensagens de amostra, contagem por grupo, custo (template de WhatsApp é cobrado), horário do envio.
4. Perguntar: "Liberar N envios por <canal> em <horário>? Bloqueados: M (motivos)." Só um "sim" explícito vale.
5. Gravar `arkos.engine/execucoes/<id>/aprovacoes/<portao>.json` = `{quem, quando, canal, n, hash_das_mensagens, expira_em}` e o log na nuvem. A validade vem de `config.travas.aprovacao_envio_validade` no perfil (padrão a confirmar: 2 h). Limites de volume diário também vêm de `config.travas` (a confirmar).
6. Devolver o `aprovacao_id`. O hook libera só envios cujo hash bate.

## O que nunca faz

- Não envia nada sozinha. Quem envia é a skill ou o MCP do canal, depois da aprovação.
- Não libera WhatsApp frio, nem por template, sem opt-in.
- Não aceita aprovação "para sempre": cada lote tem a sua.

## Pendências

- Lista exata dos nomes de ferramentas de envio de cada MCP depois de instalados.
- Testes do hook (bloqueia sem aprovação, libera com hash certo, expira).
