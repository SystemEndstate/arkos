---
name: arkos-acessos
description: Inventário e passagem de acessos por cliente na ARKOS (Meta BM, contas de anúncio, Google Ads, GA4, GTM, TikTok, domínio, hospedagem, CRM, WhatsApp, n8n, Easypanel, GitHub). Registra quem tem acesso e em qual nível, sem nunca guardar senha ou token. Gera o plano de transferência (dar ao novo antes de revogar do antigo) e o de revogação com giro de segredos, e só marca um item como feito com o id da aprovação. Use em "checklist de acessos", "quais acessos o cliente precisa dar", "transferir acessos para outro prestador", "revogar acessos", "girar chaves", e nas etapas acessos, liberar, conectar e chaves de onboarding-cliente, onboarding-prestador, passagem-prestador e desligar-prestador.
status: instalada (2026-11-22)
versao: 1.0.0
modulos: [O, D]
depende_de: [arkos-guarda-escrita, arkos-perfil]
---

# arkos-acessos

Um acesso é dinheiro e dado do cliente. Esta skill mantém o mapa de quem tem o quê e conduz as mudanças com trava. Ela **não** loga em plataforma nenhuma.

## Onde fica

- `<casa>/workspace/<cliente>/_cliente/acessos.json`, com `acessos.md` legível ao lado.
- `<casa>/workspace/<cliente>/_cliente/planos-acesso/<data>-<motivo>.json`: planos de transferência e revogação.

## Passos

1. **Checklist** do que o serviço contratado pede: `python scripts/acessos.py checklist --casa C --cliente X --servicos meta_bm,meta_ads,ga4,gtm`. Cada item nasce `pendente`.
2. **Conectar em modo leitura primeiro.** Peça ao cliente o convite de parceiro (BM, MCC, Business Center) ou o OAuth dele. Nunca login e senha pessoais.
3. **Registrar** o que foi concedido: `registrar --servico meta_ads --quem ana --nivel leitura|edicao|admin [--conta act_123]`.
4. **Transferir** (passagem): `transferir --de ana --para bruno`. Gera o plano com os itens `dar` primeiro e `revogar` depois, cada um com rollback.
5. **Revogar** (desligamento): `revogar --prestador ana`. Gera um plano por cliente, mais o item `girar_segredos`.
6. **Executar cada item** na plataforma. Se for por ferramenta (MCP), passe pela `arkos-guarda-escrita`; se for à mão, a pessoa faz. Depois marque com `concluir --plano <arq> --item N --aprovacao <id>`.

## Regras duras

1. **Nunca senha, token, chave, cookie, código 2FA ou cartão.** O script recusa (código 2) qualquer campo com cara de segredo. O segredo fica no cofre do cliente.
2. **Dar antes de revogar.** O script recusa revogar um acesso do antigo enquanto o mesmo serviço não foi dado ao novo. O cliente nunca fica sem operador.
3. **Item só fica feito com `aprovacao_id`** da guarda-escrita. Tudo vai para o `historico`.
4. **Menor nível que resolve:** leitura para auditar e relatar, edição para operar. Admin só com pedido do dono.
5. **WhatsApp:** só API oficial com opt-in. Nunca número pessoal do prestador.

## Pronto quando

- todo serviço do contrato está `ativo` ou com o motivo de estar `pendente`;
- em passagem ou desligamento, todos os itens do plano estão `feito` com aprovação e o antigo aparece como `revogado`.

## Exceções

- **entrada_incompleta:** serviço desconhecido, ou o prestador não tem acesso ativo no cliente. O script devolve código 3 com a pergunta.
- **rollback:** cada item do plano traz o seu (ex.: "remover bruno de meta_ads"). O giro de segredo não tem volta: o novo segredo vai direto ao cofre.

## Testes

`python -m unittest discover -s scripts/tests`: 4 testes cobrindo recusa de senha, token e cartão, ordem dar → revogar, aprovação obrigatória, revogação em todos os clientes e entradas inválidas.
