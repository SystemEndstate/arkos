---
name: arkos-vps
description: Operar um servidor remoto do cliente pela ARKOS — status, logs e deploy — por SSH ou pela API do Easypanel. Leitura (status/logs) é livre; deploy só com confirmação explícita e passando pela trava de escrita. Use em "o servidor está de pé?", "ver os logs", "reiniciar o serviço", "fazer deploy na VPS", "subir a nova versão no Easypanel".
status: rascunho
versao: 0.1.0
modulos: [dev, operacao]
depende_de: [arkos-guarda-escrita, arkos-monitor]
---

# arkos-vps

Clone de sala limpa da operação de VPS: usa SSH (método público) ou a API do Easypanel com a credencial do cliente, sem nenhum app/skill pessoal. Leitura é livre; **deploy e reinício só com confirmação** e pela `arkos-guarda-escrita`, com rollback registrado.

## Quando usar e quando não usar

- **Usar:** checar status, puxar logs, reiniciar serviço, fazer deploy no servidor do cliente.
- **Não usar:** sem host/credencial do cliente; para monitorar de fora (isso é `arkos-monitor`).

## Entradas

- SSH: `host`, `user`, chave (caminho; nunca a chave no texto). Ou Easypanel: `base_url` + `api_key` do cliente (env/config).
- `servico`/`projeto` alvo; para deploy, a imagem/commit e o plano de rollback.

## Passos

1. **Status/logs (livre):** `vps.py status --host ...` e `vps.py logs ...` montam o comando SSH (janela oculta) ou a chamada GET do Easypanel.
2. **Deploy (travado):** `vps.py deploy ... --confirmar --aprovacao-id <id>` monta a ação. Recusa sem `--confirmar`, sem `aprovacao_id` da `arkos-guarda-escrita` ou sem rollback. O `servico` é validado (`^[A-Za-z0-9_.-]+$`) e citado (`shlex.quote`): entrada crua nunca vira comando. Easypanel: endpoint tRPC `services.app.deployService` (o `/api/deploy/...` não existe).
3. **Antes do deploy:** registrar o estado atual (commit/deploy anterior) para o rollback.
4. **Executar** só depois do OK via `arkos-guarda-escrita` (o `aprovacao_id` vem dela).
5. **Conferir** com `arkos-monitor` que o serviço voltou (status 200 + texto esperado).

## Saída

JSON: leitura → `{cmd/url, saida?}`; deploy → `{acao, confirmado:false, o_que_faria, rollback}` sem `--confirmar`, ou `{acao, confirmado:true, trava:"arkos-guarda-escrita"}` com.

## Critério de pronto

- [ ] Status/logs só leram (não mudaram nada).
- [ ] Deploy só rodou com `--confirmar` e pela trava.
- [ ] O rollback ficou registrado antes do deploy.
- [ ] Todo subprocesso SSH rodou com janela oculta.

## Exceções

- **Sem credencial:** recusar; pedir a conexão (não adivinhar host).
- **Deploy sem `--confirmar`:** recusar e mostrar o que faria (nunca rodar).
- **Serviço não volta após deploy:** acionar o rollback registrado e avisar.

## Alimenta

- `arkos-monitor` (confere de fora) e o `arkos-painel` (registro da operação).

## Regras duras

- Credencial é sempre do cliente; o pacote não traz host nem chave.
- Deploy/reinício nunca roda sem confirmação explícita e sem a trava de escrita.
- Janela sempre oculta no Windows (CREATE_NO_WINDOW).
