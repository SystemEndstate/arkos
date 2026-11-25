---
name: arkos-site
description: Cria landing page e site de alto nível para o cliente dentro da pasta-casa — abre o projeto com o kit e o gate da taste-skill (design-taste-frontend), conduz copy, plano por telas, build, crítica com impeccable e acabamento de movimento e mobile, e só dá pronto com o gate verde. Use em "criar landing page", "site para o cliente", "página de vendas", "site bonito", "landing de alto nível", "refazer o site", "build a landing page".
status: rascunho
versao: 0.1.0
modulos: [2, S]
depende_de: [design-taste-frontend, impeccable, arkos-site-gratis]
substitui: site-de-10k (origem não confirmada; esta é uma implementação própria, escrita do zero)
---

# arkos-site

A ARKOS não reinventa o design de site: usa as duas skills **distribuíveis** que fazem isso bem, a taste-skill (`design-taste-frontend`, direção, build e gate) e a `impeccable` (crítica e auditoria). Esta skill é a **cola**: abre o projeto na pasta certa, guarda o brief, arma o gate e não deixa dizer "pronto" sem o gate.

## Pasta-casa

`workspace/<cliente>/<projeto>/site/`: `index.html`, `assets/` (kit da taste-skill), `brief.md` e `.taste-skill/` (estado do gate). Um site por projeto: o `novo` recusa uma pasta que já tem site.

## Comandos

```bash
py -3 scripts/site_arkos.py novo brief.json --casa C --cliente X --projeto Y   # kit, starter, brief.md e gate armado
py -3 scripts/site_arkos.py status <pasta-do-site>                             # roda o gate (oculto) e diz PASS/FAIL
py -3 scripts/site_arkos.py pronto <pasta-do-site>                             # critério de pronto; código 0 = verde
```

Brief: `negocio`, `tipo` (`software`, `product`, `service` ou `place`), `o_que_vende`, `publico`, `acao_principal` (o único CTA), `fatos` (só o que é verdade) e, opcionais, `contato` e `material`. Exemplo em `_comum/exemplo-brief-site.json`.

## Passos

1. `novo` com o brief. Fatos que faltam são perguntados ao `arkos-intake`; nunca inventados.
2. **design-taste-frontend**, inteira, na pasta do site: copy primeiro, plano por telas, deal, build. O gate já está armado.
3. **impeccable**: `critique` e `audit`; corrigir todo P0/P1.
4. **Pacote Emil** (`animate`, `mobile-native`): entrada do hero, hover e toque. Nada de botão de pausa em elemento decorativo; animação para fora da tela; `prefers-reduced-motion` respeitado.
5. Conferir em 360, 390, 430, 768, 1024, 1440 e 1800 px no portal do Maestro: nenhum texto vaza.
6. `pronto` até dar verde. Depois, o `arkos-site-gratis` publica.

## Regras duras

- Nada inventado: número, cliente, depoimento, prêmio ou endereço só se estiver nos `fatos`. Contato desconhecido fica em `.example`.
- Um CTA principal por tela, com o texto da `acao_principal`.
- Pronto só com o gate da taste-skill **PASS**. Exceção: FAIL que vem de um pedido explícito do cliente fica registrado em `.taste-skill/waivers.json`, com a data e o pedido.
- Responsivo de 360 a 1800 px, sem rolagem horizontal.
- Todo processo (gate, Chrome, servidor) roda oculto, sem janela.

## Pronto quando

`pronto` sai com código 0: gate PASS, `<title>` e description preenchidos, nenhum placeholder (`{{}}`, lorem, TODO) e o CTA principal presente na página.

## Exceções

- `entrada_incompleta`: brief sem campo obrigatório, `tipo` inválido ou pasta que já tem site. Código 2, a lista e nada copiado.
- `fora_do_ar`: sem a taste-skill ou sem o Node 22+. Código 3 e o que instalar. A taste-skill é procurada em `ARKOS_TASTE`, na mesma pasta de skills desta, em `CLAUDE_CONFIG_DIR/skills` e em `~/.claude/skills`, nessa ordem.
- `resultado_ruim`: gate FAIL. Corrigir um item por vez e rodar de novo; com 3 reprovações seguidas na mesma etapa, escalar para o dono. Nunca apagar teste nem waiver para passar.

## Pendências

- Vídeo de scroll e cenas pesadas: quando houver uma skill distribuível para isso.
- Medir o perf (`perf.mjs`) dentro do `pronto`.
