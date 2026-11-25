---
name: arkos-licenca
description: Licença do prestador na ARKOS. O dono emite, com papel (prestador, revisor ou dono), clientes liberados e validade; o prestador faz arkos login; a base confere a cada chamada; o dono revoga e a base responde 401 na chamada seguinte. Assinatura HMAC-SHA256 com segredo que só o dono tem. Use em "emitir licença", "liberar o prestador", "arkos login", "licença vencida", "deu 401 na base", "revogar licença", e nas etapas licenca, login e revogar de onboarding-prestador e desligar-prestador.
status: instalada (2026-11-22)
versao: 1.1.0
modulos: [O, I]
depende_de: [arkos-perfil]
---

# arkos-licenca

A licença diz quem é a pessoa, o que ela pode fazer e em quais clientes. Formato: `ARK1.<payload>.<assinatura>`. O payload tem `lid`, `prestador`, `papel`, `plano`, `clientes`, `emitida`, `expira` e `base`.

**Plano** (`--plano vip|membro`, padrão `membro`): `vip` tem acesso total; `membro` não recebe e-commerce, TikTok Shop, UGC, VSL nem advertorial, e só ouve a função das skills (engine/REGRAS-ACESSO-E-SIGILO.md). Licença sem o campo vale `membro`. O plano está dentro da assinatura: trocar `membro` por `vip` no texto da licença é recusado.

## Passos

1. **Emitir** (só o dono, depois de revisar papel e clientes):
   `ARKOS_LICENCA_SEGREDO=... python scripts/licenca.py emitir --prestador ana --papel prestador --plano membro --clientes clinica-a,loja-b --dias 90 --dono-confirma`
2. **Entregar a licença ao prestador** por um canal privado. Ele roda `arkos login <licença>`; o terminal guarda em `~/.arkos/licenca.txt`.
3. **Testar a base:** `verificar --licenca <...> --cliente clinica-a` deve dar status 200. Com um cliente que não está na licença, 401.
4. **Revogar** (desligamento ou suspeita): `revogar --lid <lid> --revogadas <arquivo da base> --motivo "..." --dono-confirma`. A próxima verificação dá 401.

## Regras duras

1. **O segredo de assinatura nunca vai para arquivo do repositório, pacote, log ou chat.** Ele só existe em `ARKOS_LICENCA_SEGREDO`, na máquina do dono ou no servidor da base, com pelo menos 32 caracteres. Sem ele, o script para.
2. **Só o dono emite e revoga** (`--dono-confirma`). O prestador não emite a própria licença.
3. **Assinatura conferida em tempo constante.** Licença editada (trocar o papel para dono, somar clientes) é recusada.
4. **Prestador e revisor precisam de pelo menos 1 cliente.** A validade vai de 1 a 365 dias.
5. **Revogar exige motivo**, que vai para a auditoria.

## Pronto quando

- a licença emitida verifica com 200 no cliente certo e 401 fora dele;
- depois de revogar, a mesma licença dá 401.

## Exceções

- **fora_do_ar:** a base não responde. O terminal trabalha só com o local e avisa; nada que precise da base roda.
- **Licença vencida ou revogada:** 401 com o motivo. A `arkos-suporte` orienta pedir uma licença nova ao dono.
- **entrada_incompleta:** papel inválido, sem cliente ou validade fora da faixa. Recusado com a explicação.

## Testes

`python -m unittest discover -s scripts/tests`: 5 testes cobrindo o ciclo completo, adulteração para virar dono ou vip, plano padrão membro, emissão sem o dono, vencida, malformada, sem segredo e entradas inválidas. Usam um segredo sintético só do teste.
